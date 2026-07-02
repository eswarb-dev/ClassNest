import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, ClipboardList, Code2, Edit3, Eye, FileUp, Plus, Send, Trash2 } from 'lucide-react'
import api, { errorMessage } from '../api/axios'
import useClassActivity from '../hooks/useClassActivity'

export default function ClassCodespace() {
  const { classId, codespaceId } = useParams()
  const [room, setRoom] = useState(null)
  const [codespace, setCodespace] = useState(null)
  const [tasks, setTasks] = useState([])
  const [assessments, setAssessments] = useState([])
  const [error, setError] = useState('')
  const [importResult, setImportResult] = useState(null)
  const [importing, setImporting] = useState('')
  const taskImportRef = useRef(null)
  const answerKeyImportRef = useRef(null)

  useEffect(() => {
    let active = true
    async function loadCodespace() {
      const codespaceResponse = codespaceId
        ? await api.get(`/codespaces/${codespaceId}`)
        : await api.get(`/classes/${classId}/codespace`)
      const [taskResponse, assessmentResponse] = await Promise.all([
        api.get(`/codespaces/${codespaceResponse.data.id}/tasks`),
        api.get(`/codespaces/${codespaceResponse.data.id}/coding-assessments`),
      ])
      if (!active) return
      setRoom({
        id: codespaceResponse.data.classroom_id,
        name: codespaceResponse.data.classroom_name,
        role: codespaceResponse.data.role,
      })
      setCodespace(codespaceResponse.data)
      setTasks(taskResponse.data)
      setAssessments(assessmentResponse.data)
    }
    loadCodespace().catch(err => { if (active) setError(errorMessage(err)) })
    return () => { active = false }
  }, [classId, codespaceId])

  const teacher = room?.role === 'teacher'
  useClassActivity(room?.id, codespace ? {
    activity_type: 'codespace_view',
    activity_label: codespace.name,
    entity_type: 'codespace',
    entity_id: codespace.id,
  } : null)
  const publishTask = async task => {
    try {
      const { data } = await api.post(`/coding-tasks/${task.id}/publish`)
      setTasks(current => current.map(item => item.id === data.id ? data : item))
    } catch (err) { setError(errorMessage(err)) }
  }
  const deleteTask = async task => {
    if (!window.confirm(`Delete "${task.title}" and its submissions?`)) return
    try {
      await api.delete(`/coding-tasks/${task.id}`)
      setTasks(current => current.filter(item => item.id !== task.id))
    } catch (err) { setError(errorMessage(err)) }
  }
  const publishAssessment = async assessment => {
    try {
      const { data } = await api.post(`/coding-assessments/${assessment.id}/publish`)
      setAssessments(current => current.map(item => item.id === data.id ? data : item))
    } catch (err) { setError(errorMessage(err)) }
  }
  const deleteAssessment = async assessment => {
    if (!window.confirm(`Delete "${assessment.title}" and its submissions?`)) return
    try {
      await api.delete(`/coding-assessments/${assessment.id}`)
      setAssessments(current => current.filter(item => item.id !== assessment.id))
    } catch (err) { setError(errorMessage(err)) }
  }
  const importExcel = async (file, endpoint, label) => {
    if (!file || !codespace) return
    setImporting(label)
    setError('')
    setImportResult(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await api.post(`/codespaces/${codespace.id}/${endpoint}`, formData)
      const taskResponse = await api.get(`/codespaces/${codespace.id}/tasks`)
      setTasks(taskResponse.data)
      setImportResult({ label, ...data })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setImporting('')
      if (taskImportRef.current) taskImportRef.current.value = ''
      if (answerKeyImportRef.current) answerKeyImportRef.current.value = ''
    }
  }

  if (error) return <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>
  if (!room || !codespace) return <div className="card p-6 text-sm text-slate-500">Loading codespace...</div>

  const detailBase = `/codespaces/${codespace.id}`

  return <div>
    <Link className="back-link" to={codespaceId ? '/codespaces' : `/classes/${classId}`}><ArrowLeft size={16} />{codespaceId ? 'Back to codespaces' : 'Back to class'}</Link>
    <section className="mt-5 card p-6 sm:p-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
        <div>
          <div className="eyebrow flex items-center gap-2"><Code2 size={16} />Codespace</div>
          <h1 className="mt-2 page-title">{codespace.name}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">{codespace.description || 'Coding workspace for this class.'}</p>
        </div>
        {teacher && <div className="flex flex-wrap gap-2">
          <button type="button" className="btn-secondary" disabled={!!importing} onClick={() => taskImportRef.current?.click()}><FileUp size={16} />{importing === 'Coding tasks' ? 'Importing...' : 'Import individual tasks'}</button>
          <button type="button" className="btn-secondary" disabled={!!importing} onClick={() => answerKeyImportRef.current?.click()}><FileUp size={16} />{importing === 'Answer key' ? 'Importing...' : 'Import individual answer keys'}</button>
          <Link className="btn-secondary" to={`${detailBase}/tasks/new`}><Plus size={16} />Create task</Link>
          <Link className="btn-primary" to={`${detailBase}/assessments/new`}><ClipboardList size={16} />Create coding assessment</Link>
          <input ref={taskImportRef} type="file" accept=".xlsx" className="sr-only" onChange={event => importExcel(event.target.files?.[0], 'import-tasks', 'Coding tasks')} />
          <input ref={answerKeyImportRef} type="file" accept=".xlsx" className="sr-only" onChange={event => importExcel(event.target.files?.[0], 'import-answer-key', 'Answer key')} />
        </div>}
      </div>
    </section>

    {importResult && <section className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
      <p className="font-bold">{importResult.label} import complete</p>
      <p className="mt-1">Imported: {importResult.imported_count} · Updated: {importResult.updated_count} · Skipped: {importResult.skipped_count}</p>
      {!!importResult.errors?.length && <ul className="mt-2 list-disc space-y-1 pl-5">{importResult.errors.map((item, index) => <li key={index}>{item}</li>)}</ul>}
    </section>}

    <section className="mt-6 space-y-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-slate-950">Coding assessments</h2>
        <span className="text-xs font-semibold text-slate-400">{assessments.length} assessment{assessments.length === 1 ? '' : 's'}</span>
      </div>
      {assessments.map(assessment => <article key={assessment.id} className="card p-5">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-lg font-bold text-slate-950">{assessment.title}</h3>
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${assessment.task_type === 'web' ? 'bg-cyan-50 text-cyan-700' : 'bg-violet-50 text-violet-700'}`}>{assessment.task_type === 'web' ? 'Web' : 'Python'}</span>
              <AssessmentStatusBadge assessment={assessment} teacher={teacher} />
            </div>
            <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-500">{assessment.description || 'No description provided.'}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
              <span>{assessment.question_count} questions</span>
              <span>{assessment.total_marks} marks</span>
              {teacher && <span>{assessment.submission_count} submissions</span>}
              {assessment.due_at && <span>Due {serverDate(assessment.due_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>}
            </div>
          </div>
          {teacher ? <div className="flex flex-wrap gap-2">
            {!assessment.is_published && <button className="btn-secondary" onClick={() => publishAssessment(assessment)}><Send size={15} />Publish</button>}
            <Link className="btn-secondary" to={`${detailBase}/assessments/${assessment.id}/submissions`}><Eye size={15} />Submissions</Link>
            <button className="btn-secondary text-red-700 hover:border-red-200 hover:bg-red-50" onClick={() => deleteAssessment(assessment)}><Trash2 size={15} />Delete</button>
          </div> : <Link className="btn-primary" to={`${detailBase}/assessments/${assessment.id}/attempt`}>Open assessment</Link>}
        </div>
      </article>)}
      {!assessments.length && <div className="empty-state">{teacher ? 'Create a coding assessment from Excel to publish many questions together.' : 'No coding assessments have been published yet.'}</div>}
    </section>

    <section className="mt-8 grid gap-3">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-slate-950">Individual coding tasks</h2>
        <span className="text-xs font-semibold text-slate-400">{tasks.length} task{tasks.length === 1 ? '' : 's'}</span>
      </div>
      {tasks.map(task => <article key={task.id} className="card p-5">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg font-bold text-slate-950">{task.title}</h2>
              <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${task.task_type === 'web' ? 'bg-cyan-50 text-cyan-700' : 'bg-violet-50 text-violet-700'}`}>{task.task_type === 'web' ? 'Web' : 'Python'}</span>
              <StatusBadge task={task} teacher={teacher} />
            </div>
            <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-500">{task.description || 'No description provided.'}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs font-semibold text-slate-500">
              <span>{task.marks} marks</span>
              {teacher && <span className={task.answer_key_exists ? 'text-emerald-700' : 'text-amber-700'}>Answer key: {task.answer_key_exists ? 'Added' : 'Missing'}</span>}
              {task.due_at && <span>Due {serverDate(task.due_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>}
              {teacher && <span>{task.submission_count} submissions</span>}
            </div>
          </div>
          {teacher ? <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" to={`${detailBase}/tasks/${task.id}/edit`}><Edit3 size={15} />Edit</Link>
            {!task.is_published && <button className="btn-secondary" onClick={() => publishTask(task)}><Send size={15} />Publish</button>}
            <Link className="btn-secondary" to={`${detailBase}/tasks/${task.id}/submissions`}><Eye size={15} />Submissions</Link>
            <button className="btn-secondary text-red-700 hover:border-red-200 hover:bg-red-50" onClick={() => deleteTask(task)}><Trash2 size={15} />Delete</button>
          </div> : <Link className="btn-primary" to={`${detailBase}/tasks/${task.id}/attempt`}>Open task</Link>}
        </div>
      </article>)}
      {!tasks.length && <div className="empty-state">{teacher ? 'Create the first coding task for this class.' : 'No coding tasks have been published yet.'}</div>}
    </section>
  </div>
}

function StatusBadge({ task, teacher }) {
  if (teacher) return <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${task.is_published ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{task.is_published ? 'Published' : 'Draft'}</span>
  if (task.my_submission_status === 'evaluated') return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-bold uppercase text-emerald-700"><CheckCircle2 size={13} />Evaluated</span>
  if (task.my_submission_status) return <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold uppercase text-blue-700">Submitted</span>
  return <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold uppercase text-slate-600">Not submitted</span>
}

function AssessmentStatusBadge({ assessment, teacher }) {
  if (teacher) return <span className={`rounded-full px-2.5 py-1 text-[11px] font-bold uppercase ${assessment.is_published ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{assessment.is_published ? 'Published' : 'Draft'}</span>
  if (assessment.my_submission_status === 'evaluated') return <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-bold uppercase text-emerald-700"><CheckCircle2 size={13} />Evaluated</span>
  if (assessment.my_submission_status) return <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold uppercase text-blue-700">Submitted</span>
  return <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold uppercase text-slate-600">Not submitted</span>
}

function serverDate(value) {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}
