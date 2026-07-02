import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import ServerWakeNotice from './components/ServerWakeNotice'
import { FullPageLoader } from './components/common/Loading'
import Login from './pages/Login'
import Register from './pages/Register'
import CreateClass from './pages/CreateClass'
import JoinClass from './pages/JoinClass'
import InviteJoin from './pages/InviteJoin'
import EditClass from './pages/EditClass'
import TestDetails from './pages/TestDetails'
import TestAttempt from './pages/TestAttempt'
import TestResult from './pages/TestResult'
import ClassResults from './pages/ClassResults'
import MembersPage from './pages/MembersPage'
import CreateUnit from './pages/CreateUnit'
import EditUnit from './pages/EditUnit'
import CreateMaterial from './pages/CreateMaterial'
import CreateTest from './pages/CreateTest'
import AddQuestions from './pages/AddQuestions'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
const ResetPassword = lazy(() => import('./pages/ResetPassword'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const ClassDetails = lazy(() => import('./pages/ClassDetails'))
const UnitDetails = lazy(() => import('./pages/UnitDetails'))
const CreateAssessment = lazy(() => import('./pages/CreateAssessment'))
const AssessmentDetails = lazy(() => import('./pages/AssessmentDetails'))
const AssessmentAttempt = lazy(() => import('./pages/AssessmentAttempt'))
const AssessmentDashboard = lazy(() => import('./pages/AssessmentDashboard'))
const AssessmentResult = lazy(() => import('./pages/AssessmentResult'))
const MaterialReader = lazy(() => import('./pages/MaterialReader'))
const EditMaterial = lazy(() => import('./pages/EditMaterial'))
const EditAssessment = lazy(() => import('./pages/EditAssessment'))
const EmailNotificationPage = lazy(() => import('./pages/EmailNotificationPage'))
const Codespaces = lazy(() => import('./pages/Codespaces'))
const ClassCodespace = lazy(() => import('./pages/ClassCodespace'))
const CodingTaskEditor = lazy(() => import('./pages/CodingTaskEditor'))
const CodingTaskAttempt = lazy(() => import('./pages/CodingTaskAttempt'))
const CodingTaskSubmissions = lazy(() => import('./pages/CodingTaskSubmissions'))
const CodingAssessmentEditor = lazy(() => import('./pages/CodingAssessmentEditor'))
const CodingAssessmentAttempt = lazy(() => import('./pages/CodingAssessmentAttempt'))
const CodingAssessmentSubmissions = lazy(() => import('./pages/CodingAssessmentSubmissions'))

export default function App() {
  return <>
    <ServerWakeNotice />
    <Suspense fallback={<FullPageLoader />}><Routes>
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route path="/reset-password" element={<ResetPassword />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="codespaces" element={<Codespaces />} />
        <Route path="codespaces/:codespaceId" element={<ClassCodespace />} />
        <Route path="codespaces/:codespaceId/tasks/new" element={<CodingTaskEditor />} />
        <Route path="codespaces/:codespaceId/tasks/:taskId/edit" element={<CodingTaskEditor />} />
        <Route path="codespaces/:codespaceId/tasks/:taskId/attempt" element={<CodingTaskAttempt />} />
        <Route path="codespaces/:codespaceId/tasks/:taskId/submissions" element={<CodingTaskSubmissions />} />
        <Route path="codespaces/:codespaceId/assessments/new" element={<CodingAssessmentEditor />} />
        <Route path="codespaces/:codespaceId/assessments/:assessmentId/attempt" element={<CodingAssessmentAttempt />} />
        <Route path="codespaces/:codespaceId/assessments/:assessmentId/submissions" element={<CodingAssessmentSubmissions />} />
        <Route path="profile" element={<Profile />} />
        <Route path="settings" element={<Settings />} />
        <Route path="join/:joinCode" element={<InviteJoin />} />
        <Route path="classes/new" element={<CreateClass />} />
        <Route path="classes/join" element={<JoinClass />} />
        <Route path="classes/:classId" element={<ClassDetails />} />
        <Route path="classes/:classId/edit" element={<EditClass />} />
        <Route path="classes/:classId/units/new" element={<CreateUnit />} />
        <Route path="classes/:classId/units/:unitId/edit" element={<EditUnit />} />
        <Route path="classes/:classId/members" element={<MembersPage />} />
        <Route path="classes/:classId/results" element={<ClassResults />} />
        <Route path="classes/:classId/codespace" element={<ClassCodespace />} />
        <Route path="classes/:classId/codespace/tasks/new" element={<CodingTaskEditor />} />
        <Route path="classes/:classId/codespace/tasks/:taskId/edit" element={<CodingTaskEditor />} />
        <Route path="classes/:classId/codespace/tasks/:taskId/attempt" element={<CodingTaskAttempt />} />
        <Route path="classes/:classId/codespace/tasks/:taskId/submissions" element={<CodingTaskSubmissions />} />
        <Route path="classes/:classId/codespace/assessments/new" element={<CodingAssessmentEditor />} />
        <Route path="classes/:classId/notifications/email" element={<EmailNotificationPage />} />
        <Route path="units/:unitId" element={<UnitDetails />} />
        <Route path="units/:unitId/materials/new" element={<CreateMaterial />} />
        <Route path="classes/:classId/units/:unitId/materials/:materialId/edit" element={<EditMaterial />} />
        <Route path="units/:unitId/tests/new" element={<CreateTest />} />
        <Route path="units/:unitId/assessments/new" element={<CreateAssessment />} />
        <Route path="classes/:classId/units/:unitId/assessments/:assessmentId/edit" element={<EditAssessment />} />
        <Route path="classes/:classId/units/:unitId/assessments/:assessmentId/manage" element={<AssessmentDashboard />} />
        <Route path="assessments/:assessmentId" element={<AssessmentDetails />} />
        <Route path="assessments/:assessmentId/attempt" element={<AssessmentAttempt />} />
        <Route path="assessments/:assessmentId/dashboard" element={<AssessmentDashboard />} />
        <Route path="assessments/:assessmentId/result" element={<AssessmentResult />} />
        <Route path="materials/:materialId" element={<MaterialReader />} />
        <Route path="tests/:testId" element={<TestDetails />} />
        <Route path="tests/:testId/attempt" element={<TestAttempt />} />
        <Route path="tests/:testId/questions/new" element={<AddQuestions />} />
        <Route path="results/:attemptId" element={<TestResult />} />
      </Route>
    </Route>
    <Route path="*" element={<div className="grid min-h-screen place-items-center"><a href="/" className="text-brand-600">Return to ClassNest</a></div>} />
    </Routes></Suspense>
  </>
}
