import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { Segmented, Select } from '../components/shell/Controls'
import { UseCaseModels } from '../components/process/UseCaseModels'
import { ErrorNotice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { t } from '../i18n'
import { useSession } from '../state/session'
import { useTheme, type Theme } from '../state/theme'

export function Settings() {
  const { user, signIn } = useSession()

  const users = useQuery({ queryKey: keys.users, queryFn: () => api.listUsers() })
  const useCases = useQuery({ queryKey: keys.useCases, queryFn: () => api.listUseCases() })
  const [picked, setPicked] = useState<number | null>(null)
  const useCaseId = picked ?? useCases.data?.[0]?.id

  const switchUser = useMutation({ mutationFn: (email: string) => signIn(email) })


  return (
    <>
      <Topbar crumbs={[{ label: 'Ajustes' }]} />
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <PageIntro
          kicker="Espacio"
          title="Ajustes"
          description="Quién eres para el backend y el estado de la API. OCR y modelos de un proceso concreto están en Ajustes de ese proceso."
        />

        <div className="max-w-2xl space-y-3">
          <Appearance />

          <NestedCard
            label="usuario"
          >
            <div className="space-y-2 px-3.5 py-3">
              <p className="text-[12px] text-muted">
                Tu id viaja en la cabecera <span className="font-mono">X-User-Id</span>. Activar
                y retirar reglas solo lo puede hacer un responsable.
              </p>
              {users.isError ? <ErrorNotice error={users.error} /> : null}
              {switchUser.isError ? <ErrorNotice error={switchUser.error} /> : null}
              <ul className="space-y-1">
                {(users.data ?? []).map((candidate) => (
                  <li key={candidate.id}>
                    <button
                      type="button"
                      onClick={() => switchUser.mutate(candidate.email)}
                      className={
                        candidate.id === user?.id
                          ? 'flex w-full items-center justify-between rounded-[10px] bg-well px-3 py-2 text-left ring-1 ring-line'
                          : 'flex w-full items-center justify-between rounded-[10px] px-3 py-2 text-left hover:bg-canvas'
                      }
                    >
                      <span className="text-[13px]">
                        {candidate.name}
                        <span className="ml-2 font-mono text-[11px] text-faint">
                          {candidate.email}
                        </span>
                      </span>
                      <StatusBadge
                        value={candidate.role === 'manager' ? 'activa' : 'borrador'}
                      >
                        {t(`roles.${candidate.role}`)}
                      </StatusBadge>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </NestedCard>

          <NestedCard label="modelos del caso de uso (compartidos)">
            <div className="space-y-2 px-3.5 py-3">
              <p className="text-[12px] text-muted">
                Configuración activa por caso de uso y papel. Cada cambio crea una versión nueva:
                compilador, tester ciego, normalizador y asistente pueden usar modelos distintos.
              </p>
              {useCases.isError ? <ErrorNotice error={useCases.error} /> : null}
              {(useCases.data?.length ?? 0) > 1 ? (
                <Select
                  value={useCaseId}
                  onChange={(event) => setPicked(Number(event.target.value))}
                >
                  {useCases.data?.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </Select>
              ) : null}
              {useCaseId != null ? <UseCaseModels useCaseId={useCaseId} /> : null}
            </div>
          </NestedCard>

          <ApiStatus />
        </div>
      </div>
    </>
  )
}

function Appearance() {
  const { theme, setTheme } = useTheme()

  return (
    <NestedCard label="apariencia">
      <div className="space-y-3 px-3.5 py-3">
        <p className="text-[12px] text-muted">
          Claro por defecto. Oscuro se guarda en este navegador.
        </p>
        <Segmented<Theme>
          value={theme}
          onChange={setTheme}
          options={[
            { value: 'light', label: 'Claro' },
            { value: 'dark', label: 'Oscuro' },
          ]}
        />
      </div>
    </NestedCard>
  )
}

/** Where the console gets its data: only the backend. */
function ApiStatus() {
  return (
    <NestedCard label="api">
      <div className="space-y-2 px-3.5 py-3">
        <div className="flex items-baseline justify-between text-[13px]">
          <span className="text-muted">Base</span>
          <span className="font-mono">{import.meta.env.VITE_API_URL ?? '/api'}</span>
        </div>
        <p className="text-[12px] text-muted">
          Todo sale del backend real y sus errores se muestran tal cual.
        </p>
      </div>
    </NestedCard>
  )
}
