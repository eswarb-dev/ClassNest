import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Send } from 'lucide-react'
import api, { errorMessage } from '../api/axios'

const PythonCodeWorkspace = lazy(() => import('../components/code/PythonCodeWorkspace'))
const WebCodeWorkspace = lazy(() => import('../components/code/WebCodeWorkspace'))

export default function CodingAssessmentAttempt() {
  const { codespaceId, assessmentId } = useParams()
  const [assessment, setAssessment] = useState(null)
  const [answers, setAnswers] = useState({})
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get(`/coding-assessments/${assessmentId}`).then(response => {
      setAssessment(response.data)
      setAnswers(Object.fromEntries(response.data.questions.map(question => [question.id, {
        code: question.starter_code || '',
        html_code: question.starter_html || '',
        css_code: question.starter_css || '',
        js_code: question.starter_js || '',
      }])))
    }).catch(err => setError(errorMessage(err)))
  }, [assessmentId])

  const answeredCount = useMemo(() => Object.values(answers).filter(answer => [answer.code, answer.html_code, answer.css_code, answer.js_code].some(value => (value || '').trim())).length, [answers])

  const runCode = async (question, code) => {
    const { data } = await api.post('/code/run', { code, language: 'python' })
    return data
  }
  const submit = async () => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await api.post(`/coding-assessments/${assessmentId}/submit`, {
        answers: assessment.questions.map(question => ({ question_id: question.id, ...(answers[question.id] || {}) })),
      })
      setNotice('Assessment submitted successfully.')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  if (error && !assessment) return <p className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>
  if (!assessment) return <div className="card p-6 text-sm text-slate-500">Loading coding assessment...</div>

  return <div className="mx-auto max-w-5xl">
    <Link className="back-link" to={`/codespaces/${codespaceId || assessment.codespace_id}`}><ArrowLeft size={16} />Back to codespace</Link>
    <section className="card mt-5 p-6 sm:p-8">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <h1 className="page-title">{assessment.title}</h1>
          <p className="mt-2 text-sm leading-6 text-slate-500">{assessment.description || 'Complete all coding questions and submit once.'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-bold text-slate-700">{answeredCount} / {assessment.questions.length} questions answered</div>
      </div>
      {error && <p className="mt-5 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {notice && <p className="mt-5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">{notice}</p>}
    </section>
    <section className="mt-6 space-y-5">
      {assessment.questions.map((question, index) => <article key={question.id} className="card overflow-hidden">
        <div className="border-b border-slate-200 p-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold uppercase text-slate-600">Question {index + 1}</span>
            <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold uppercase text-blue-700">{question.marks} marks</span>
          </div>
          <h2 className="mt-3 text-lg font-bold text-slate-950">{question.title}</h2>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{question.description}</p>
        </div>
        <div className="bg-slate-50 p-5">
          <Suspense fallback={<div className="h-80 animate-pulse rounded-xl bg-slate-200" />}>
            {assessment.task_type === 'web'
              ? <WebCodeWorkspace
                initialHtml={answers[question.id]?.html_code}
                initialCss={answers[question.id]?.css_code}
                initialJs={answers[question.id]?.js_code}
                starterHtml={question.starter_html || ''}
                starterCss={question.starter_css || ''}
                starterJs={question.starter_js || ''}
                onCodeChange={value => setAnswers(current => ({ ...current, [question.id]: { ...(current[question.id] || {}), ...value } }))}
                expectedOutput={question.expected_output}
                showExpectedOutput={Boolean(question.expected_output)}
              />
              : <PythonCodeWorkspace
                initialCode={answers[question.id]?.code}
                starterCode={question.starter_code || ''}
                onCodeChange={value => setAnswers(current => ({ ...current, [question.id]: { ...(current[question.id] || {}), code: value } }))}
                onRun={code => runCode(question, code)}
                expectedOutput={question.expected_output}
                showExpectedOutput={Boolean(question.expected_output)}
              />}
          </Suspense>
        </div>
      </article>)}
    </section>
    <div className="sticky bottom-4 mt-6 flex justify-end">
      <button className="btn-primary shadow-lg" disabled={busy} onClick={submit}><Send size={16} />{busy ? 'Submitting...' : 'Submit assessment'}</button>
    </div>
  </div>
}
