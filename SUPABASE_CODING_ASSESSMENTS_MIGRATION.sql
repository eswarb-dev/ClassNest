CREATE TABLE IF NOT EXISTS public.coding_assessments (
    id SERIAL PRIMARY KEY,
    codespace_id INTEGER NOT NULL REFERENCES public.class_codespaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT DEFAULT 'python',
    total_marks INTEGER DEFAULT 0,
    due_at TIMESTAMP NULL,
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.coding_assessment_questions (
    id SERIAL PRIMARY KEY,
    assessment_id INTEGER NOT NULL REFERENCES public.coding_assessments(id) ON DELETE CASCADE,
    question_id TEXT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    starter_code TEXT,
    starter_html TEXT,
    starter_css TEXT,
    starter_js TEXT,
    expected_output TEXT,
    visible_test_cases TEXT,
    hidden_test_cases TEXT,
    marks INTEGER DEFAULT 10,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.coding_assessment_submissions (
    id SERIAL PRIMARY KEY,
    assessment_id INTEGER NOT NULL REFERENCES public.coding_assessments(id) ON DELETE CASCADE,
    student_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'submitted',
    total_marks_awarded INTEGER DEFAULT 0,
    feedback TEXT,
    submitted_at TIMESTAMP DEFAULT NOW(),
    evaluated_at TIMESTAMP NULL,
    completion_email_sent BOOLEAN DEFAULT FALSE,
    UNIQUE(assessment_id, student_id)
);

CREATE TABLE IF NOT EXISTS public.coding_assessment_answers (
    id SERIAL PRIMARY KEY,
    submission_id INTEGER NOT NULL REFERENCES public.coding_assessment_submissions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES public.coding_assessment_questions(id) ON DELETE CASCADE,
    code TEXT,
    html_code TEXT,
    css_code TEXT,
    js_code TEXT,
    output TEXT,
    marks_awarded INTEGER DEFAULT 0,
    feedback TEXT,
    evaluation_status TEXT DEFAULT 'needs_review',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(submission_id, question_id)
);

CREATE TABLE IF NOT EXISTS public.coding_assessment_answer_keys (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES public.coding_assessment_questions(id) ON DELETE CASCADE,
    expected_answer TEXT,
    expected_output TEXT,
    visible_test_cases TEXT,
    hidden_test_cases TEXT,
    evaluation_rule TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coding_assessments_codespace_id
ON public.coding_assessments(codespace_id);

CREATE INDEX IF NOT EXISTS idx_coding_assessment_questions_assessment_id
ON public.coding_assessment_questions(assessment_id);

CREATE INDEX IF NOT EXISTS idx_coding_assessment_submissions_assessment_id
ON public.coding_assessment_submissions(assessment_id);

CREATE INDEX IF NOT EXISTS idx_coding_assessment_answers_submission_id
ON public.coding_assessment_answers(submission_id);
