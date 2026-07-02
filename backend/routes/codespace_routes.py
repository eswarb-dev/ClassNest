from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import case, func
from sqlalchemy.orm import Session

import models, schemas
from auth import get_current_user
from coding_runner import run_python_code
from database import get_db
from services.codespace_excel_import import import_coding_answer_keys, import_coding_tasks, preview_coding_answer_keys, preview_coding_tasks, read_codespace_excel_upload
from services.coding_evaluation_service import evaluate_submission as evaluate_coding_submission
from services.email_service import send_email
from utils import require_member, require_teacher

router = APIRouter(tags=["Codespaces"])


def ensure_codespace(db: Session, classroom: models.Classroom):
    codespace = db.query(models.ClassCodespace).filter_by(classroom_id=classroom.id).first()
    if codespace:
        return codespace
    codespace = models.ClassCodespace(
        classroom_id=classroom.id,
        name=f"{classroom.name} Codespace",
        description=f"Coding workspace for {classroom.name}",
    )
    db.add(codespace)
    db.flush()
    return codespace


def task_classroom_id(task: models.CodingTask):
    return task.codespace.classroom_id


def assessment_classroom_id(assessment: models.CodingAssessment):
    return assessment.codespace.classroom_id


def task_out(task: models.CodingTask, member_role: str, student_id: int | None = None, include_code: bool = True, submission_count: int | None = None, answer_key_exists: bool | None = None, student_submission=None):
    data = schemas.CodingTaskOut.model_validate(task).model_dump()
    data["submission_count"] = submission_count if submission_count is not None else len(task.submissions or [])
    data["answer_key_exists"] = bool(answer_key_exists) if answer_key_exists is not None else task.answer_key is not None
    if not include_code:
        for field in ("starter_code", "starter_html", "starter_css", "starter_js", "hidden_test_cases", "my_code", "my_html_code", "my_css_code", "my_js_code"):
            data[field] = None
    if member_role == "student":
        data["answer_key_exists"] = False
    if member_role == "student" and student_id:
        submission = student_submission if student_submission is not None else next((item for item in task.submissions if item.student_id == student_id), None)
        if submission:
            data["my_submission_status"] = submission.status
            data["my_submission_id"] = submission.id
            data["my_marks_awarded"] = submission.final_marks if submission.final_marks is not None else submission.marks_awarded
            data["my_feedback"] = submission.feedback or submission.evaluation_feedback
            if include_code:
                data["my_code"] = submission.code
                data["my_html_code"] = submission.html_code
                data["my_css_code"] = submission.css_code
                data["my_js_code"] = submission.js_code
            data["my_evaluation_status"] = submission.evaluation_status
            data["my_evaluation_feedback"] = submission.evaluation_feedback
    return data


def send_coding_completion_email(recipient_email: str, student_name: str, student_email: str, task_title: str, codespace_name: str, class_name: str, submitted_at, evaluation_status: str):
    subject = f"Coding task completed: {task_title}"
    message = (
        f"{student_name} has submitted the coding task '{task_title}' in {class_name}.\n\n"
        f"Student name: {student_name}\n"
        f"Email: {student_email}\n"
        f"Task title: {task_title}\n"
        f"Codespace name: {codespace_name}\n"
        f"Submitted time: {submitted_at}\n"
        f"Evaluation status: {evaluation_status}"
    )
    send_email(recipient_email, subject, message)


def send_coding_assessment_completion_email(recipient_email: str, student_name: str, assessment_title: str):
    send_email(recipient_email, f"Coding assessment completed: {assessment_title}", f"{student_name} completed {assessment_title}")


def codespace_out(codespace: models.ClassCodespace, role: str):
    data = schemas.ClassCodespaceOut.model_validate(codespace).model_dump()
    data["classroom_name"] = codespace.classroom.name
    data["role"] = role
    return data


def apply_task_answer_key(db: Session, task: models.CodingTask, answer_key: schemas.CodingTaskAnswerKeyInput | None):
    if not answer_key:
        return
    key = task.answer_key
    if key is None:
        key = models.CodingTaskAnswerKey(task=task, question_id=answer_key.question_id)
        db.add(key)
    key.question_id = answer_key.question_id
    key.correct_answer = answer_key.correct_answer
    key.accepted_answers = answer_key.accepted_answers
    key.expected_output = answer_key.expected_output
    key.evaluation_mode = (answer_key.evaluation_mode or "MANUAL").upper()
    key.case_sensitive = answer_key.case_sensitive
    key.visible_test_cases = answer_key.visible_test_cases
    key.hidden_test_cases = answer_key.hidden_test_cases
    key.explanation = answer_key.explanation


def assessment_out(assessment: models.CodingAssessment, member_role: str, student_id: int | None = None, include_questions: bool = False, submission_count: int | None = None, student_submission=None):
    data = schemas.CodingAssessmentOut.model_validate(assessment).model_dump()
    data["question_count"] = len(assessment.questions or [])
    data["submission_count"] = submission_count if submission_count is not None else len(assessment.submissions or [])
    if member_role == "student":
        for question in data.get("questions", []):
            question["hidden_test_cases"] = None
    if not include_questions:
        data["questions"] = []
    if member_role == "student" and student_id:
        submission = student_submission
        if submission:
            data["my_submission_status"] = submission.status
            data["my_submission_id"] = submission.id
            data["my_marks_awarded"] = submission.total_marks_awarded
    return data


def apply_assessment_answer_key(db: Session, question: models.CodingAssessmentQuestion, answer_key: schemas.CodingTaskAnswerKeyInput | None):
    if not answer_key:
        return
    key = question.answer_key
    if key is None:
        key = models.CodingAssessmentAnswerKey(question=question)
        db.add(key)
    key.expected_answer = answer_key.correct_answer or answer_key.accepted_answers
    key.expected_output = answer_key.expected_output
    key.visible_test_cases = answer_key.visible_test_cases
    key.hidden_test_cases = answer_key.hidden_test_cases
    key.evaluation_rule = answer_key.explanation or answer_key.evaluation_mode


def normalize_task_payload(data: schemas.CodingTaskInput):
    payload = data.model_dump(exclude={"answer_key"})
    if payload["task_type"] == "web":
        payload["language"] = "html-css-js"
        payload["starter_code"] = None
        payload["preview_enabled"] = True if data.preview_enabled is False else data.preview_enabled
    else:
        payload["task_type"] = "python"
        payload["language"] = payload.get("language") or "python"
        payload["starter_html"] = None
        payload["starter_css"] = None
        payload["starter_js"] = None
        payload["preview_enabled"] = False
    return payload


@router.get("/codespaces", response_model=schemas.CodespacesIndexOut)
def list_codespaces(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (
        db.query(models.Classroom, models.ClassMember.role)
        .join(models.ClassMember)
        .filter(models.ClassMember.user_id == user.id, models.Classroom.archived == False)
        .order_by(models.Classroom.created_at.desc())
        .all()
    )
    teaching = []
    learning = []
    changed = False
    for classroom, role in rows:
        codespace = ensure_codespace(db, classroom)
        changed = True
        if role == "teacher":
            total_tasks, published_tasks = db.query(
                func.count(models.CodingTask.id),
                func.sum(case((models.CodingTask.is_published == True, 1), else_=0)),
            ).filter(models.CodingTask.codespace_id == codespace.id).one()
            pending_submissions = (
                db.query(func.count(models.CodingSubmission.id))
                .join(models.CodingTask, models.CodingTask.id == models.CodingSubmission.task_id)
                .filter(models.CodingTask.codespace_id == codespace.id, models.CodingSubmission.status == "submitted")
                .scalar()
            )
            teaching.append({
                "codespace_id": codespace.id,
                "classroom_id": classroom.id,
                "class_name": classroom.name,
                "codespace_name": codespace.name,
                "role": "teacher",
                "total_tasks": total_tasks or 0,
                "published_tasks": published_tasks or 0,
                "pending_submissions": pending_submissions or 0,
            })
        else:
            available_tasks = db.query(func.count(models.CodingTask.id)).filter(models.CodingTask.codespace_id == codespace.id, models.CodingTask.is_published == True).scalar()
            submitted_tasks, pending_feedback = db.query(
                func.count(models.CodingSubmission.id),
                func.sum(case((models.CodingSubmission.status != "evaluated", 1), else_=0)),
            ).join(models.CodingTask, models.CodingTask.id == models.CodingSubmission.task_id).filter(
                models.CodingTask.codespace_id == codespace.id,
                models.CodingTask.is_published == True,
                models.CodingSubmission.student_id == user.id,
            ).one()
            learning.append({
                "codespace_id": codespace.id,
                "classroom_id": classroom.id,
                "class_name": classroom.name,
                "codespace_name": codespace.name,
                "role": "student",
                "available_tasks": available_tasks or 0,
                "submitted_tasks": submitted_tasks or 0,
                "pending_feedback": pending_feedback or 0,
            })
    if changed:
        db.commit()
    return {"teaching": teaching, "learning": learning}


@router.get("/classes/{classroom_id}/codespace", response_model=schemas.ClassCodespaceOut)
def get_class_codespace(classroom_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    classroom = db.get(models.Classroom, classroom_id)
    if not classroom:
        raise HTTPException(404, "Classroom not found")
    require_member(db, classroom_id, user.id)
    codespace = ensure_codespace(db, classroom)
    db.commit()
    db.refresh(codespace)
    member = require_member(db, classroom_id, user.id)
    return codespace_out(codespace, member.role)


@router.get("/codespaces/{codespace_id}", response_model=schemas.ClassCodespaceOut)
def get_codespace(codespace_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    member = require_member(db, codespace.classroom_id, user.id)
    return codespace_out(codespace, member.role)


@router.get("/codespaces/{codespace_id}/tasks", response_model=list[schemas.CodingTaskOut])
def list_tasks(codespace_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    member = require_member(db, codespace.classroom_id, user.id)
    query = db.query(models.CodingTask).filter_by(codespace_id=codespace_id)
    if member.role == "student":
        query = query.filter(models.CodingTask.is_published == True)
    tasks = query.order_by(models.CodingTask.created_at.desc()).all()
    task_ids = [task.id for task in tasks]
    submission_counts = dict(
        db.query(models.CodingSubmission.task_id, func.count(models.CodingSubmission.id))
        .filter(models.CodingSubmission.task_id.in_(task_ids))
        .group_by(models.CodingSubmission.task_id)
        .all()
    ) if task_ids else {}
    answer_key_ids = set()
    if member.role == "teacher" and task_ids:
        answer_key_ids = {row[0] for row in db.query(models.CodingTaskAnswerKey.task_id).filter(models.CodingTaskAnswerKey.task_id.in_(task_ids)).all()}
    student_submissions = {}
    if member.role == "student" and task_ids:
        student_submissions = {
            submission.task_id: submission
            for submission in db.query(models.CodingSubmission).filter(models.CodingSubmission.task_id.in_(task_ids), models.CodingSubmission.student_id == user.id).all()
        }
    return [
        task_out(
            task,
            member.role,
            user.id,
            include_code=False,
            submission_count=submission_counts.get(task.id, 0),
            answer_key_exists=task.id in answer_key_ids,
            student_submission=student_submissions.get(task.id),
        )
        for task in tasks
    ]


@router.get("/coding-tasks/{task_id}", response_model=schemas.CodingTaskOut)
def get_task(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(models.CodingTask, task_id)
    if not task:
        raise HTTPException(404, "Coding task not found")
    member = require_member(db, task_classroom_id(task), user.id)
    if member.role == "student" and not task.is_published:
        raise HTTPException(404, "Coding task not found")
    submission_count = db.query(func.count(models.CodingSubmission.id)).filter(models.CodingSubmission.task_id == task.id).scalar()
    student_submission = None
    if member.role == "student":
        student_submission = db.query(models.CodingSubmission).filter_by(task_id=task.id, student_id=user.id).first()
    answer_key_exists = False
    if member.role == "teacher":
        answer_key_exists = db.query(models.CodingTaskAnswerKey.id).filter_by(task_id=task.id).first() is not None
    return task_out(task, member.role, user.id, include_code=True, submission_count=submission_count or 0, answer_key_exists=answer_key_exists, student_submission=student_submission)


@router.post("/codespaces/{codespace_id}/tasks", response_model=schemas.CodingTaskOut, status_code=201)
def create_task(codespace_id: int, data: schemas.CodingTaskInput, db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    require_teacher(db, codespace.classroom_id, user.id)
    if data.question_id:
        existing = db.query(models.CodingTask).filter_by(codespace_id=codespace_id, question_id=data.question_id).first()
        if existing:
            raise HTTPException(409, "This question already exists. Update existing task?")
    payload = normalize_task_payload(data)
    task = models.CodingTask(codespace_id=codespace_id, **payload)
    db.add(task)
    apply_task_answer_key(db, task, data.answer_key)
    db.commit()
    db.refresh(task)
    return task_out(task, "teacher")


@router.post("/codespaces/{codespace_id}/import-tasks", response_model=schemas.CodespaceImportSummary)
async def import_tasks(codespace_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    require_teacher(db, codespace.classroom_id, user.id)
    content = await read_codespace_excel_upload(file)
    return import_coding_tasks(db, codespace_id, content)


@router.post("/codespaces/{codespace_id}/import-answer-key", response_model=schemas.CodespaceImportSummary)
async def import_answer_key(codespace_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    require_teacher(db, codespace.classroom_id, user.id)
    content = await read_codespace_excel_upload(file)
    return import_coding_answer_keys(db, codespace_id, content)


@router.post("/codespaces/{codespace_id}/preview-task-import")
async def preview_task_import(codespace_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    require_teacher(db, codespace.classroom_id, user.id)
    content = await read_codespace_excel_upload(file)
    return preview_coding_tasks(content)


@router.post("/codespaces/{codespace_id}/coding-assessments/import-preview")
async def preview_coding_assessment_import(codespace_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    require_teacher(db, codespace.classroom_id, user.id)
    content = await read_codespace_excel_upload(file)
    return preview_coding_tasks(content)


@router.get("/codespaces/{codespace_id}/coding-assessments", response_model=list[schemas.CodingAssessmentOut])
def list_coding_assessments(codespace_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    member = require_member(db, codespace.classroom_id, user.id)
    query = db.query(models.CodingAssessment).filter_by(codespace_id=codespace_id)
    if member.role == "student":
        query = query.filter(models.CodingAssessment.is_published == True)
    assessments = query.order_by(models.CodingAssessment.created_at.desc()).all()
    ids = [item.id for item in assessments]
    submission_counts = dict(db.query(models.CodingAssessmentSubmission.assessment_id, func.count(models.CodingAssessmentSubmission.id)).filter(models.CodingAssessmentSubmission.assessment_id.in_(ids)).group_by(models.CodingAssessmentSubmission.assessment_id).all()) if ids else {}
    student_submissions = {}
    if member.role == "student" and ids:
        student_submissions = {item.assessment_id: item for item in db.query(models.CodingAssessmentSubmission).filter(models.CodingAssessmentSubmission.assessment_id.in_(ids), models.CodingAssessmentSubmission.student_id == user.id).all()}
    return [assessment_out(item, member.role, user.id, submission_count=submission_counts.get(item.id, 0), student_submission=student_submissions.get(item.id)) for item in assessments]


@router.post("/codespaces/{codespace_id}/coding-assessments", response_model=schemas.CodingAssessmentOut, status_code=201)
def create_coding_assessment(codespace_id: int, data: schemas.CodingAssessmentInput, db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    require_teacher(db, codespace.classroom_id, user.id)
    assessment = models.CodingAssessment(
        codespace_id=codespace_id,
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        total_marks=sum(question.marks for question in data.questions),
        due_at=data.due_at,
        is_published=data.is_published,
    )
    db.add(assessment)
    key_by_id = {key.question_id: key for key in data.answer_keys}
    for index, item in enumerate(data.questions):
        question = models.CodingAssessmentQuestion(
            assessment=assessment,
            question_id=item.question_id,
            title=item.title,
            description=item.description,
            starter_code=item.starter_code if data.task_type == "python" else None,
            starter_html=item.starter_html if data.task_type == "web" else None,
            starter_css=item.starter_css if data.task_type == "web" else None,
            starter_js=item.starter_js if data.task_type == "web" else None,
            expected_output=item.expected_output,
            visible_test_cases=item.visible_test_cases,
            hidden_test_cases=item.hidden_test_cases,
            marks=item.marks,
            sort_order=index,
        )
        db.add(question)
        apply_assessment_answer_key(db, question, key_by_id.get(item.question_id))
    db.commit()
    db.refresh(assessment)
    return assessment_out(assessment, "teacher", include_questions=True)


@router.post("/codespaces/{codespace_id}/preview-answer-key-import")
async def preview_answer_key_import(codespace_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    codespace = db.get(models.ClassCodespace, codespace_id)
    if not codespace:
        raise HTTPException(404, "Codespace not found")
    require_teacher(db, codespace.classroom_id, user.id)
    content = await read_codespace_excel_upload(file)
    return preview_coding_answer_keys(content)


@router.put("/coding-tasks/{task_id}", response_model=schemas.CodingTaskOut)
def update_task(task_id: int, data: schemas.CodingTaskInput, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(models.CodingTask, task_id)
    if not task:
        raise HTTPException(404, "Coding task not found")
    require_teacher(db, task_classroom_id(task), user.id)
    if data.question_id:
        existing = db.query(models.CodingTask).filter(
            models.CodingTask.codespace_id == task.codespace_id,
            models.CodingTask.question_id == data.question_id,
            models.CodingTask.id != task.id,
        ).first()
        if existing:
            raise HTTPException(409, "This question already exists. Update existing task?")
    for field, value in normalize_task_payload(data).items():
        setattr(task, field, value)
    apply_task_answer_key(db, task, data.answer_key)
    db.commit()
    db.refresh(task)
    return task_out(task, "teacher")


@router.delete("/coding-tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(models.CodingTask, task_id)
    if not task:
        raise HTTPException(404, "Coding task not found")
    require_teacher(db, task_classroom_id(task), user.id)
    db.delete(task)
    db.commit()
    return Response(status_code=204)


@router.post("/coding-tasks/{task_id}/publish", response_model=schemas.CodingTaskOut)
def publish_task(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(models.CodingTask, task_id)
    if not task:
        raise HTTPException(404, "Coding task not found")
    require_teacher(db, task_classroom_id(task), user.id)
    task.is_published = True
    db.commit()
    db.refresh(task)
    return task_out(task, "teacher")


@router.post("/coding-tasks/{task_id}/run", response_model=schemas.CodingRunOut)
def run_task_code(task_id: int, data: schemas.CodingTaskRunInput, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(models.CodingTask, task_id)
    if not task:
        raise HTTPException(404, "Coding task not found")
    member = require_member(db, task_classroom_id(task), user.id)
    if member.role == "student" and not task.is_published:
        raise HTTPException(404, "Coding task not found")
    if task.task_type != "python":
        raise HTTPException(400, "Web tasks run in the browser preview")
    return run_python_code(data.code, task.visible_test_cases)


@router.post("/coding-tasks/{task_id}/submit", response_model=schemas.CodingSubmissionOut)
def submit_task(task_id: int, data: schemas.CodingSubmissionInput, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(models.CodingTask, task_id)
    if not task:
        raise HTTPException(404, "Coding task not found")
    member = require_member(db, task_classroom_id(task), user.id)
    if member.role != "student":
        raise HTTPException(403, "Student access required")
    if not task.is_published:
        raise HTTPException(404, "Coding task not found")
    submission = db.query(models.CodingSubmission).filter_by(task_id=task_id, student_id=user.id).first()
    send_completion_email = False
    is_web_task = task.task_type == "web"
    if is_web_task and not any([(data.html_code or "").strip(), (data.css_code or "").strip(), (data.js_code or "").strip()]):
        raise HTTPException(422, "Submit at least one HTML, CSS, or JavaScript field")
    if not is_web_task and not (data.code or "").strip():
        raise HTTPException(422, "Code is required")
    if submission:
        send_completion_email = not submission.completion_email_sent
        submission.code = data.code or ""
        submission.html_code = data.html_code
        submission.css_code = data.css_code
        submission.js_code = data.js_code
        submission.preview_snapshot = data.preview_snapshot
        submission.output = data.output
        submission.status = "submitted"
        submission.submitted_at = datetime.utcnow()
        submission.marks_awarded = None
        submission.auto_marks = None
        submission.final_marks = None
        submission.is_correct = None
        submission.evaluation_status = "needs_review" if is_web_task else "pending"
        submission.evaluation_feedback = None
        submission.feedback = None
    else:
        submission = models.CodingSubmission(
            task_id=task_id,
            student_id=user.id,
            code=data.code or "",
            html_code=data.html_code,
            css_code=data.css_code,
            js_code=data.js_code,
            preview_snapshot=data.preview_snapshot,
            output=data.output,
            evaluation_status="needs_review" if is_web_task else "pending",
            submitted_at=datetime.utcnow(),
        )
        db.add(submission)
        send_completion_email = True
    if is_web_task:
        submission.auto_marks = None
        submission.final_marks = None
        submission.is_correct = None
    else:
        evaluate_coding_submission(submission, task)
    teacher = db.get(models.User, task.codespace.classroom.created_by_user_id)
    if send_completion_email and teacher and teacher.email:
        submission.completion_email_sent = True
        background_tasks.add_task(
            send_coding_completion_email,
            teacher.email,
            user.name,
            user.email,
            task.title,
            task.codespace.name,
            task.codespace.classroom.name,
            submission.submitted_at,
            submission.evaluation_status,
        )
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/coding-tasks/{task_id}/submissions", response_model=list[schemas.CodingSubmissionListOut])
def list_submissions(task_id: int, limit: int = 25, offset: int = 0, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = db.get(models.CodingTask, task_id)
    if not task:
        raise HTTPException(404, "Coding task not found")
    require_teacher(db, task_classroom_id(task), user.id)
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    rows = db.query(models.CodingSubmission, models.User).join(models.User, models.User.id == models.CodingSubmission.student_id).filter(models.CodingSubmission.task_id == task_id).order_by(models.CodingSubmission.submitted_at.desc()).offset(offset).limit(limit).all()
    return [{**schemas.CodingSubmissionOut.model_validate(submission).model_dump(), "student_name": student.name, "student_email": student.email} for submission, student in rows]


@router.get("/coding-submissions/{submission_id}", response_model=schemas.CodingSubmissionOut)
def submission_detail(submission_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.query(models.CodingSubmission, models.User).join(models.User, models.User.id == models.CodingSubmission.student_id).filter(models.CodingSubmission.id == submission_id).first()
    if not row:
        raise HTTPException(404, "Coding submission not found")
    submission, student = row
    require_teacher(db, task_classroom_id(submission.task), user.id)
    return {**schemas.CodingSubmissionOut.model_validate(submission).model_dump(), "student_name": student.name, "student_email": student.email}


@router.put("/coding-submissions/{submission_id}/evaluate", response_model=schemas.CodingSubmissionOut)
def evaluate_submission(submission_id: int, data: schemas.CodingSubmissionEvaluate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    submission = db.get(models.CodingSubmission, submission_id)
    if not submission:
        raise HTTPException(404, "Coding submission not found")
    require_teacher(db, task_classroom_id(submission.task), user.id)
    submission.marks_awarded = data.marks_awarded
    submission.final_marks = data.marks_awarded
    submission.feedback = data.feedback
    submission.evaluation_feedback = data.feedback or submission.evaluation_feedback
    submission.status = "evaluated"
    submission.evaluation_status = "teacher_evaluated"
    submission.evaluated_at = datetime.utcnow()
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/coding-assessments/{assessment_id}", response_model=schemas.CodingAssessmentOut)
def get_coding_assessment(assessment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assessment = db.get(models.CodingAssessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Coding assessment not found")
    member = require_member(db, assessment_classroom_id(assessment), user.id)
    if member.role == "student" and not assessment.is_published:
        raise HTTPException(404, "Coding assessment not found")
    submission = None
    if member.role == "student":
        submission = db.query(models.CodingAssessmentSubmission).filter_by(assessment_id=assessment.id, student_id=user.id).first()
    return assessment_out(assessment, member.role, user.id, include_questions=True, student_submission=submission)


@router.post("/coding-assessments/{assessment_id}/publish", response_model=schemas.CodingAssessmentOut)
def publish_coding_assessment(assessment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assessment = db.get(models.CodingAssessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Coding assessment not found")
    require_teacher(db, assessment_classroom_id(assessment), user.id)
    assessment.is_published = True
    assessment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assessment)
    return assessment_out(assessment, "teacher")


@router.delete("/coding-assessments/{assessment_id}", status_code=204)
def delete_coding_assessment(assessment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assessment = db.get(models.CodingAssessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Coding assessment not found")
    require_teacher(db, assessment_classroom_id(assessment), user.id)
    db.delete(assessment)
    db.commit()
    return Response(status_code=204)


@router.post("/coding-assessments/{assessment_id}/submit", response_model=schemas.CodingAssessmentSubmissionOut)
def submit_coding_assessment(assessment_id: int, data: schemas.CodingAssessmentSubmitInput, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assessment = db.get(models.CodingAssessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Coding assessment not found")
    member = require_member(db, assessment_classroom_id(assessment), user.id)
    if member.role != "student":
        raise HTTPException(403, "Student access required")
    if not assessment.is_published:
        raise HTTPException(404, "Coding assessment not found")
    valid_question_ids = {question.id for question in assessment.questions}
    invalid = [answer.question_id for answer in data.answers if answer.question_id not in valid_question_ids]
    if invalid:
        raise HTTPException(422, "One or more answers do not belong to this assessment")
    submission = db.query(models.CodingAssessmentSubmission).filter_by(assessment_id=assessment_id, student_id=user.id).first()
    send_completion_email = False
    if submission:
        send_completion_email = not submission.completion_email_sent
        submission.status = "submitted"
        submission.submitted_at = datetime.utcnow()
        submission.evaluated_at = None
        submission.total_marks_awarded = 0
        submission.feedback = None
    else:
        submission = models.CodingAssessmentSubmission(assessment_id=assessment_id, student_id=user.id, submitted_at=datetime.utcnow())
        db.add(submission)
        db.flush()
        send_completion_email = True
    existing = {answer.question_id: answer for answer in submission.answers}
    for item in data.answers:
        answer = existing.get(item.question_id)
        if answer is None:
            answer = models.CodingAssessmentAnswer(submission=submission, question_id=item.question_id)
            db.add(answer)
        answer.code = item.code
        answer.html_code = item.html_code
        answer.css_code = item.css_code
        answer.js_code = item.js_code
        answer.output = item.output
        answer.marks_awarded = 0
        answer.feedback = None
        answer.evaluation_status = "needs_review"
        answer.updated_at = datetime.utcnow()
    teacher = db.get(models.User, assessment.codespace.classroom.created_by_user_id)
    if send_completion_email and teacher and teacher.email:
        submission.completion_email_sent = True
        background_tasks.add_task(send_coding_assessment_completion_email, teacher.email, user.name, assessment.title)
    db.commit()
    db.refresh(submission)
    return {**schemas.CodingAssessmentSubmissionOut.model_validate(submission).model_dump(), "student_name": user.name, "student_email": user.email}


@router.get("/coding-assessments/{assessment_id}/submissions", response_model=list[schemas.CodingAssessmentSubmissionOut])
def list_coding_assessment_submissions(assessment_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assessment = db.get(models.CodingAssessment, assessment_id)
    if not assessment:
        raise HTTPException(404, "Coding assessment not found")
    require_teacher(db, assessment_classroom_id(assessment), user.id)
    rows = db.query(models.CodingAssessmentSubmission, models.User).join(models.User, models.User.id == models.CodingAssessmentSubmission.student_id).filter(models.CodingAssessmentSubmission.assessment_id == assessment_id).order_by(models.CodingAssessmentSubmission.submitted_at.desc()).all()
    return [{**schemas.CodingAssessmentSubmissionOut.model_validate(submission).model_dump(), "student_name": student.name, "student_email": student.email, "answers": []} for submission, student in rows]


@router.get("/coding-assessments/submissions/{submission_id}", response_model=schemas.CodingAssessmentSubmissionOut)
def coding_assessment_submission_detail(submission_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    row = db.query(models.CodingAssessmentSubmission, models.User).join(models.User, models.User.id == models.CodingAssessmentSubmission.student_id).filter(models.CodingAssessmentSubmission.id == submission_id).first()
    if not row:
        raise HTTPException(404, "Coding assessment submission not found")
    submission, student = row
    require_teacher(db, assessment_classroom_id(submission.assessment), user.id)
    return {**schemas.CodingAssessmentSubmissionOut.model_validate(submission).model_dump(), "student_name": student.name, "student_email": student.email}


@router.patch("/coding-assessment-answers/{answer_id}/evaluate", response_model=schemas.CodingAssessmentAnswerOut)
def evaluate_coding_assessment_answer(answer_id: int, data: schemas.CodingAssessmentAnswerEvaluate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    answer = db.get(models.CodingAssessmentAnswer, answer_id)
    if not answer:
        raise HTTPException(404, "Coding assessment answer not found")
    require_teacher(db, assessment_classroom_id(answer.submission.assessment), user.id)
    answer.marks_awarded = min(data.marks_awarded, answer.question.marks)
    answer.feedback = data.feedback
    answer.evaluation_status = "teacher_evaluated"
    answer.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(answer)
    return answer


@router.patch("/coding-assessment-submissions/{submission_id}/finalize", response_model=schemas.CodingAssessmentSubmissionOut)
def finalize_coding_assessment_submission(submission_id: int, data: schemas.CodingAssessmentFinalizeInput, db: Session = Depends(get_db), user=Depends(get_current_user)):
    submission = db.get(models.CodingAssessmentSubmission, submission_id)
    if not submission:
        raise HTTPException(404, "Coding assessment submission not found")
    require_teacher(db, assessment_classroom_id(submission.assessment), user.id)
    submission.total_marks_awarded = sum(answer.marks_awarded or 0 for answer in submission.answers)
    submission.feedback = data.feedback
    submission.status = "evaluated"
    submission.evaluated_at = datetime.utcnow()
    db.commit()
    db.refresh(submission)
    return submission
