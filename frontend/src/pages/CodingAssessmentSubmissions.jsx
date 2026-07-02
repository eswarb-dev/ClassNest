import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Eye, Save } from 'lucide-react'
import api, { errorMessage } from '../api/axios'

export default function CodingAssessmentSubmissions() {
  const { codespaceId, assessmentId } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [submissions, setSubmissions] = useState([])
  const [details, setDetails] = useState({})
  const [drafts, setDrafts] = useState({})
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get(`/coding-assessments/${assessmentId}`),
      api.get(`/coding-assessments/${assessmentId}/submissions`),
    ]).then(([assessmentResponse, submissionsResponse]) => {
      setAssessment(assessmentResponse.data)
      setSubmissions(submissionsResponse.data)
    }).catch(err => setError(errorMessage(err)))
  }, [assessmentId])

  const openDetail = async submission => {
    if (details[submission.id]) return
    const { data } = await api.get(`/coding-assessments/submissions/${submission.id}`)
    setDetails(current => ({ ...current, [submission.id]: data }))
    setDrafts(current => ({ ...current, ...Object.fromEntries(data.answers.map(answer => [answer.id, { marks_awarded: answer.marks_awarded ?? '', feedback: answer.feedback || '' }])) }))
  }

  const saveAnswer = async answer => {
    const draft = drafts[answer.id]
    const { data } = await api.patch(`/coding-assessment-answers/${answer.id}/evaluate`, { marks_awarded: Number(draft.marks_awarded || 0), feedback: draft.feedback })
    setDetails(current => ({
      ...current,
      [data.submission_id]: {
        ...current[data.submission_id],
        answers: current[data.submission_id].answers.map(item => item.id === data.id ? data : item),
      },
    }))
  }

  const finalize = async submission => {
    const { data } = await api.patch(`/coding-assessment-submissions/${submission.id}/finalize`, { feedback: submission.feedback || null })
    setSubmissions(current => current.map(item => item.id === data.id ? { ...item, ...data } : item))
    setDetails(current => ({ ...current, [submission.id]: { ...(current[submission.id] || submission), ...data } }))
  }

  if (error) return <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>
  if (!assessment) return <div className="card p-6 text-sm text-slate-500">Loading submissions...</div>

  return <div className="mx-auto max-w-5xl">
    <Link className="back-link" to={`/codespaces/${codespaceId || assessment.codespace_id}`}><ArrowLeft size={16} />Back to codespace</Link>
    <section className="card mt-5 p-6 sm:p-8">
      <h1 className="page-title">{assessment.title}</h1>
      <p className="mt-2 text-sm text-slate-500">{submissions.length} submissions · {assessment.total_marks} marks</p>
    </section>
    <section className="mt-6 space-y-4">
      {submissions.map(submission => <article key={submission.id} className="card p-5">
        <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="font-bold text-slate-950">{submission.student_name || `Student #${submission.student_id}`}</h2>
            <p className="mt-1 text-xs text-slate-500">{submission.student_email} · Submitted {serverDate(submission.submitted_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold uppercase text-slate-600">{submission.status}</span>
            <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold uppercase text-blue-700">{submission.total_marks_awarded}/{assessment.total_marks}</span>
            <button className="btn-secondary" onClick={() => openDetail(submission)}><Eye size={15} />Open</button>
            <button className="btn-primary" onClick={() => finalize(details[submission.id] || submission)}><Save size={15} />Finalize</button>
          </div>
        </div>
        {details[submission.id] && <div className="mt-5 space-y-4">
          {details[submission.id].answers.map(answer => <section key={answer.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-wrap justify-between gap-3">
              <div>
                <p className="text-sm font-bold text-slate-950">{answer.question?.title || `Question ${answer.question_id}`}</p>
                <p className="mt-1 text-xs text-slate-500">{answer.question?.marks ?? 0} marks</p>
              </div>
              <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold uppercase text-slate-600">{answer.evaluation_status}</span>
            </div>
            {answer.question?.task_type === 'web' || answer.html_code || answer.css_code || answer.js_code
              ? <div className="mt-3 grid gap-3 lg:grid-cols-3">{['html_code', 'css_code', 'js_code'].map(field => <pre key={field} className="max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">{answer[field] || ''}</pre>)}</div>
              : <pre className="mt-3 max-h-80 overflow-auto rounded-lg bg-slate-950 p-3 text-xs leading-5 text-slate-100">{answer.code || ''}</pre>}
            <div className="mt-4 grid gap-3 sm:grid-cols-[140px_1fr_auto] sm:items-end">
              <label><span className="label">Marks</span><input className="field bg-white" type="number" min="0" max={answer.question?.marks ?? 1000} value={drafts[answer.id]?.marks_awarded ?? ''} onChange={event => setDrafts(current => ({ ...current, [answer.id]: { ...(current[answer.id] || {}), marks_awarded: event.target.value } }))} /></label>
              <label><span className="label">Feedback</span><input className="field bg-white" value={drafts[answer.id]?.feedback ?? ''} onChange={event => setDrafts(current => ({ ...current, [answer.id]: { ...(current[answer.id] || {}), feedback: event.target.value } }))} /></label>
              <button className="btn-secondary" onClick={() => saveAnswer(answer)}><Save size={15} />Save</button>
            </div>
          </section>)}
        </div>}
      </article>)}
      {!submissions.length && <div className="empty-state">No submissions yet.</div>}
    </section>
  </div>
}

function serverDate(value) {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}
