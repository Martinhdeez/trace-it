import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, mode } from '../api/client'
import { keys } from '../api/queries'
import { Button, Input, Segmented } from '../components/shell/Controls'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { t } from '../i18n'
import { useSession } from '../state/session'
import { useTheme, type Theme } from '../state/theme'

export function Settings() {
  const { user, signIn, signOut } = useSession()
  const queryClient = useQueryClient()

  const users = useQuery({ queryKey: keys.users, queryFn: () => api.listUsers() })
  const llm = useQuery({ queryKey: keys.llm, queryFn: () => api.listLlmConfig() })

  const switchUser = useMutation({ mutationFn: (email: string) => signIn(email) })

  const change = useMutation({
    mutationFn: ({ role, model }: { role: string; model: string }) =>
      api.setLlmConfig(role, model),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.llm }),
  })

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
            action={
              user ? (
                <Button tone="ghost" onClick={signOut}>
                  Salir
                </Button>
              ) : null
            }
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

          <NestedCard label="modelo por papel">
            <div className="space-y-2 px-3.5 py-3">
              <p className="text-[12px] text-muted">
                Configuración activa por caso de uso y papel. Cada cambio crea una versión nueva:
                compilador, tester ciego, normalizador y asistente pueden usar modelos distintos.
              </p>
              {llm.isError ? <ErrorNotice error={llm.error} /> : null}
              {llm.data?.length === 0 ? <Empty>Sin papeles configurados.</Empty> : null}
              {(llm.data ?? []).map((config) => (
                <div key={config.papel} className="flex items-center gap-2">
                  <span className="w-32 shrink-0 font-mono text-[12px] text-muted">
                    {config.papel}
                  </span>
                  <Input
                    defaultValue={config.modelo}
                    className="font-mono"
                    onBlur={(event) => {
                      const model = event.target.value.trim()
                      if (model && model !== config.modelo) {
                        change.mutate({ role: config.papel, model })
                      }
                    }}
                  />
                </div>
              ))}
              {change.isError ? <ErrorNotice error={change.error} /> : null}
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

/** Where the console gets its data: the real backend, or the simulator when asked for. */
function ApiStatus() {
  return (
    <NestedCard label="api">
      <div className="space-y-2 px-3.5 py-3">
        <div className="flex items-baseline justify-between text-[13px]">
          <span className="text-muted">Modo</span>
          <span className="font-mono">
            {mode} · {import.meta.env.VITE_API_URL ?? '/api'}
          </span>
        </div>
        <p className="text-[12px] text-muted">
          Por defecto todo sale del backend real y sus errores se muestran tal cual. Con{' '}
          <span className="font-mono">VITE_API_MODE=mock</span> la consola usa el simulador y lo
          indica con la etiqueta MOCK DATA.
        </p>
      </div>
    </NestedCard>
  )
}
