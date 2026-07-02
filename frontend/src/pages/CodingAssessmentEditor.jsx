import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CheckSquare, FileUp, Save, Square } from 'lucide-react'
import api, { errorMessage } from '../api/axios'

const blankForm = { title: '', description: '', task_type: 'python', due_at: '', is_published: false }

export default function CodingAssessmentEditor() {
  const { classId, codespaceId } = useParams()
  const navigate = useNavigate()
  const [codespace, setCodespace] = useState(null)
  const [form, setForm] = useState(blankForm)
  const [questions, setQuestions] = useState([])
  const [answerKeys, setAnswerKeys] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const url = codespaceId ? `/codespaces/${codespaceId}` : `/classes/${classId}/codespace`
    api.get(url).then(response => setCodespace(response.data)).catch(err => setError(errorMessage(err)))
  }, [classId, codespaceId])

  const selectedQuestions = useMemo(() => questions.filter((_, index) => selected.has(index)), [questions, selected])
  const totalMarks = selectedQuestions.reduce((sum, item) => sum + Number(item.marks || 0), 0)
  const allSelected = questions.length > 0 && selected.size === questions.length

  const uploadPreview = async (file, endpoint, setter, label) => {
    if (!file || !codespace) return
    setError('')
    setNotice('')
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await api.post(`/codespaces/${codespace.id}/${endpoint}`, formData)
      setter(data)
      if (endpoint.includes('import-preview')) setSelected(new Set(data.map((_, index) => index)))
      setNotice(`${data.length} ${label} detected.`)
      if (endpoint.includes('import-preview') && data[0]?.assessment_title && !form.title) {
        setForm(current => ({ ...current, title: data[0].assessment_title }))
      }
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(questions.map((_, index) => index)))
  const toggleOne = index => setSelected(current => {
    const next = new Set(current)
    if (next.has(index)) next.delete(index)
    else next.add(index)
    return next
  })

  const submit = async event => {
    event.preventDefault()
    if (!selectedQuestions.length) {
      setError('Select at least one coding question.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const payload = {
        ...form,
        due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
        questions: selectedQuestions.map(question => ({
          question_id: question.question_id || null,
          title: question.title || `${question.question_id || 'Question'} - Coding Task`,
          description: question.description || question.question_text,
          starter_code: form.task_type === 'python' ? question.starter_code || null : null,
          starter_html: form.task_type === 'web' ? question.starter_html || question.starter_code || '' : null,
          starter_css: form.task_type === 'web' ? question.starter_css || '' : null,
          starter_js: form.task_type === 'web' ? question.starter_js || '' : null,
          expected_output: question.expected_output || null,
          visible_test_cases: question.visible_test_cases || null,
          hidden_test_cases: question.hidden_test_cases || null,
          marks: Number(question.marks || 0),
        })),
        answer_keys: answerKeys,
      }
      await api.post(`/codespaces/${codespace.id}/coding-assessments`, payload)
      navigate(`/codespaces/${codespace.id}`)
    } catch (err) {
      setError(errorMessage(err))
      setBusy(false)
    }
  }

  return <div className="mx-auto max-w-5xl">
    <Link className="back-link" to={codespace ? `/codespaces/${codespace.id}` : '/codespaces'}><ArrowLeft size={16} />Back to codespace</Link>
    <section className="card mt-5 p-6 sm:p-8">
      <h1 className="page-title">Create coding assessment</h1>
      <form onSubmit={submit} className="mt-7 space-y-5">
        {error && <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {notice && <p className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p>}
        <section className="grid gap-3 sm:grid-cols-2">
          <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm font-semibold text-slate-700"><FileUp size={18} className="text-brand-700" />Upload Coding Assessment Excel<input className="sr-only" type="file" accept=".xlsx" onChange={event => uploadPreview(event.target.files?.[0], 'coding-assessments/import-preview', setQuestions, 'coding questions')} /></label>
          <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white p-4 text-sm font-semibold text-slate-700"><FileUp size={18} className="text-brand-700" />Upload Answer Key Excel optional<input className="sr-only" type="file" accept=".xlsx" onChange={event => uploadPreview(event.target.files?.[0], 'preview-answer-key-import', setAnswerKeys, 'answer keys')} /></label>
        </section>
        {!!questions.length && <section className="overflow-hidden rounded-xl border border-slate-200">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-slate-50 p-4">
            <button type="button" className="btn-secondary" onClick={toggleAll}>{allSelected ? <CheckSquare size={16} /> : <Square size={16} />}{allSelected ? 'Clear all' : 'Select all'}</button>
            <span className="text-sm font-semibold text-slate-600">{selectedQuestions.length} selected · {totalMarks} marks</span>
          </div>
          <div className="divide-y divide-slate-100">
            {questions.map((question, index) => <label key={`${question.question_id || 'question'}-${index}`} className="grid cursor-pointer gap-3 p-4 sm:grid-cols-[auto_1fr_auto_auto] sm:items-center">
              <input type="checkbox" className="size-4 rounded border-slate-300 text-brand-600" checked={selected.has(index)} onChange={() => toggleOne(index)} />
              <span className="min-w-0"><span className="block text-sm font-bold text-slate-900">{question.question_id || `Question ${index + 1}`}</span><span className="line-clamp-2 text-xs leading-5 text-slate-500">{question.description || question.question_text}</span></span>
              <span className="text-xs font-bold uppercase text-slate-500">{form.task_type === 'web' ? 'Web' : 'Python'}</span>
              <span className="text-sm font-bold text-slate-700">{question.marks} marks</span>
            </label>)}
          </div>
        </section>}
        <label><span className="label">Assessment title</span><input className="field" required maxLength="300" value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} /></label>
        <label><span className="label">Description</span><textarea className="field resize-y" rows="4" value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} /></label>
        <div className="grid gap-4 sm:grid-cols-3">
          <label><span className="label">Task type</span><select className="field" value={form.task_type} onChange={event => setForm({ ...form, task_type: event.target.value })}><option value="python">Python</option><option value="web">HTML/CSS/JS Web</option></select></label>
          <label><span className="label">Total marks</span><input className="field" readOnly value={totalMarks} /></label>
          <label><span className="label">Due date</span><input className="field" type="datetime-local" value={form.due_at} onChange={event => setForm({ ...form, due_at: event.target.value })} /></label>
        </div>
        <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-4"><input type="checkbox" checked={form.is_published} onChange={event => setForm({ ...form, is_published: event.target.checked })} className="mt-0.5 size-4 rounded border-slate-300 text-brand-600" /><span><span className="block text-sm font-semibold text-slate-800">Publish to students</span><span className="mt-1 block text-xs text-slate-500">Draft assessments remain visible only to teachers.</span></span></label>
        <div className="flex justify-end gap-2"><Link className="btn-secondary" to={codespace ? `/codespaces/${codespace.id}` : '/codespaces'}>Cancel</Link><button className="btn-primary" disabled={busy || !codespace || !selectedQuestions.length}><Save size={16} />{busy ? 'Saving...' : 'Save assessment'}</button></div>
      </form>
    </section>
  </div>
}
