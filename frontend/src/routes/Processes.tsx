import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Plus, Trash2, X } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { Button } from '../components/shell/Controls'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { Topbar } from '../components/shell/Topbar'
import { NestedCard, PageIntro } from '../components/shell/Well'
import { t } from '../i18n'
import { paths } from '../lib/paths'
import { useSession } from '../state/session'

export function Processes() {
  const { isManager } = useSession()
  const queryClient = useQueryClient()
  const [confirming, setConfirming] = useState<number | null>(null)
  const processes = useQuery({ queryKey: keys.processes, queryFn: () => api.listProcesses() })
  const remove = useMutation({
    mutationFn: (processId: number) => api.deleteProcess(processId),
    onSuccess: async (_, processId) => {
      setConfirming(null)
      queryClient.removeQueries({ queryKey: keys.process(processId) })
      await queryClient.invalidateQueries({ queryKey: keys.processes })
    },
  })

  return (
    <>
      <Topbar
        crumbs={[{ label: 'Procesos' }]}
        actions={
          <Link to={paths.newProcess}>
            <Button tone="primary">
              <Plus size={12} strokeWidth={2} />
              Nuevo proceso
            </Button>
          </Link>
        }
      />
      <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-10 pt-4 sm:px-6">
        <PageIntro
          kicker="Espacio"
          title="Procesos"
          description="Un proceso son unas reglas, un histórico de decisiones y las fuentes contra las que se validan. El pago de facturas es el primero, no el producto."
        />

        {processes.isError ? <ErrorNotice error={processes.error} /> : null}
        {remove.isError ? <ErrorNotice error={remove.error} /> : null}

        <NestedCard label={`${processes.data?.length ?? 0} procesos`}>
          {processes.data?.length ? (
            <ul className="divide-y divide-hairline">
              {processes.data.map((process) => (
                <li key={process.id} className="flex items-center gap-3 px-3.5 py-3">
                  <Link to={paths.process(process.id)} className="min-w-0 flex-1 hover:text-ink">
                    <p className="text-[15px] font-medium">{process.name}</p>
                    <p className="mt-0.5 line-clamp-2 text-[12.5px] text-muted">
                      {process.description}
                    </p>
                  </Link>
                  {isManager ? (
                    confirming === process.id ? (
                      <div className="flex shrink-0 items-center gap-1.5">
                        <span className="text-[12px] text-muted">{t('processes.confirmDelete')}</span>
                        <Button
                          tone="ghost"
                          aria-label={t('common.cancel')}
                          disabled={remove.isPending}
                          onClick={() => {
                            setConfirming(null)
                            remove.reset()
                          }}
                        >
                          <X size={12} strokeWidth={2} />
                        </Button>
                        <Button
                          tone="danger"
                          disabled={remove.isPending}
                          onClick={() => remove.mutate(process.id)}
                        >
                          <Check size={12} strokeWidth={2} />
                          {remove.isPending ? t('processes.deleting') : t('common.confirm')}
                        </Button>
                      </div>
                    ) : (
                      <Button
                        tone="ghost"
                        aria-label={t('processes.delete')}
                        title={t('processes.delete')}
                        onClick={() => {
                          remove.reset()
                          setConfirming(process.id)
                        }}
                        className="shrink-0 text-nopagar hover:text-nopagar"
                      >
                        <Trash2 size={14} strokeWidth={1.8} />
                      </Button>
                    )
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <Empty>Ningún proceso todavía. Crea el primero o importa un JSON.</Empty>
          )}
        </NestedCard>
      </div>
    </>
  )
}
