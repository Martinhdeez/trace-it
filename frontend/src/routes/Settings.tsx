import { useSyncExternalStore } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, apiTrace, mode } from '../api/client'
import { keys } from '../api/queries'
import { Button, Input } from '../components/shell/Controls'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { StatusBadge } from '../components/shell/StatusBadge'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { useSession } from '../state/session'

export function Settings() {
  const { user, use, signOut } = useSession()
  const queryClient = useQueryClient()

  const users = useQuery({ queryKey: keys.users, queryFn: () => api.listUsers() })
  const llm = useQuery({ queryKey: keys.llm, queryFn: () => api.listLlmConfig() })

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
          description="Quién eres para el backend, qué modelo lleva cada papel y qué parte de la API está viva."
        />

        <div className="max-w-2xl space-y-3">
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
              <ul className="space-y-1">
                {(users.data ?? []).map((candidate) => (
                  <li key={candidate.id}>
                    <button
                      type="button"
                      onClick={() => use(candidate)}
                      className={
                        candidate.id === user?.id
                          ? 'flex w-full items-center justify-between rounded-[10px] bg-well px-3 py-2 text-left ring-1 ring-black/[0.05]'
                          : 'flex w-full items-center justify-between rounded-[10px] px-3 py-2 text-left hover:bg-canvas'
                      }
                    >
                      <span className="text-[13px]">
                        {candidate.nombre}
                        <span className="ml-2 font-mono text-[11px] text-faint">
                          {candidate.email}
                        </span>
                      </span>
                      <StatusBadge
                        value={candidate.rol === 'responsable' ? 'activa' : 'borrador'}
                      >
                        {candidate.rol}
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

/** Which calls the real backend answered and which ones the mock covered. */
function ApiStatus() {
  useSyncExternalStore(apiTrace.subscribe, apiTrace.snapshot)
  const entries = apiTrace.entries()
  const live = entries.filter(([, source]) => source === 'live').length

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
          En <span className="font-mono">auto</span> cada llamada intenta el backend real y cae al
          simulador si el endpoint responde 501, 502 o no existe. {live} de {entries.length}{' '}
          llamadas de esta sesión salieron del backend.
        </p>
        {entries.length === 0 ? (
          <Empty>Todavía no se ha llamado a nada.</Empty>
        ) : (
          <ul className="grid gap-x-6 gap-y-0.5 sm:grid-cols-2">
            {entries.map(([method, source]) => (
              <li key={method} className="flex items-baseline justify-between gap-2">
                <span className="truncate font-mono text-[11.5px] text-muted">{method}</span>
                <span
                  className={
                    source === 'live'
                      ? 'font-mono text-[10px] text-pagar'
                      : 'font-mono text-[10px] text-faint'
                  }
                >
                  {source}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </NestedCard>
  )
}
