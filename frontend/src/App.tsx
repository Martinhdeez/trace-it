import { Navigate, Outlet, Route, Routes } from 'react-router'
import { AppShell } from './components/shell/AppShell'
import { Audit } from './routes/Audit'
import { Instances } from './routes/Instances'
import { Landing } from './routes/Landing'
import { NewProcess } from './routes/NewProcess'
import { Process } from './routes/Process'
import { Processes } from './routes/Processes'
import { Queue } from './routes/Queue'
import { Rule } from './routes/Rule'
import { Rules } from './routes/Rules'
import { Settings } from './routes/Settings'
import { Sources } from './routes/Sources'
import { paths } from './lib/paths'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route element={<Console />}>
        <Route path="/processes" element={<Processes />} />
        <Route path="/processes/new" element={<NewProcess />} />
        <Route path="/processes/:processId" element={<Process />} />
        <Route path="/processes/:processId/instances" element={<Instances />} />
        <Route path="/processes/:processId/queue" element={<Queue />} />
        <Route path="/processes/:processId/rules" element={<Rules />} />
        <Route path="/processes/:processId/rules/:ruleId" element={<Rule />} />
        <Route path="/processes/:processId/audit" element={<Audit />} />
        <Route path="/processes/:processId/sources" element={<Sources />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to={paths.processes} replace />} />
    </Routes>
  )
}

function Console() {
  return (
    <AppShell>
      <div className="relative flex min-h-0 flex-1 flex-col">
        <Outlet />
      </div>
    </AppShell>
  )
}
