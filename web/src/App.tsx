import { Navigate, Route, Routes, useParams } from 'react-router'
import { AppShell } from './components/shell/AppShell'
import { Settings } from './routes/Settings'
import { ReviewQueue } from './routes/ReviewQueue'
import { NuevoProceso } from './routes/NuevoProceso'
import { ProcessHome } from './routes/ProcessHome'
import { RulesPage } from './routes/RulesPage'
import { RunConsole } from './routes/RunConsole'
import { RunsList } from './routes/RunsList'
import { PROCESS, paths } from './lib/paths'

const legacyProcess: Record<string, string> = {
  'conciliar-pagos': PROCESS.reconcilePayments,
  'nota-simple': PROCESS.landRegistry,
  'altas-proveedor': PROCESS.vendorOnboarding,
}

export default function App() {
  return (
    <AppShell>
      <div className="relative flex min-h-0 flex-1 flex-col">
        <Routes>
          <Route path="/" element={<Navigate to={paths.process(PROCESS.reconcilePayments)} replace />} />
          <Route path="/processes/new" element={<NuevoProceso />} />
          <Route path="/processes/:processId" element={<ProcessHome />} />
          <Route path="/processes/:processId/rules" element={<RulesPage />} />
          <Route path="/processes/:processId/runs/:runId" element={<RunConsole />} />
          <Route path="/review" element={<ReviewQueue />} />
          <Route path="/runs" element={<RunsList />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/procesos/nuevo" element={<Navigate to={paths.processNew} replace />} />
          <Route path="/procesos/:processId" element={<LegacyProcess />} />
          <Route path="/cola" element={<Navigate to={paths.review} replace />} />
          <Route path="/ajustes" element={<Navigate to={paths.settings} replace />} />
        </Routes>
      </div>
    </AppShell>
  )
}

function LegacyProcess() {
  const { processId = '' } = useParams()
  return <Navigate to={paths.process(legacyProcess[processId] ?? PROCESS.reconcilePayments)} replace />
}
