import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Plus, Trash2, X } from 'lucide-react'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { Button } from '../components/shell/Controls'
import { ErrorNotice } from '../components/shell/Notice'
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
    <main className="min-h-0 flex-1 overflow-y-auto px-5 py-8 sm:p-10 lg:p-12">
      <h1 className="sr-only">{t('nav.processes')}</h1>
      {processes.isError ? <ErrorNotice error={processes.error} /> : null}
      {remove.isError ? <ErrorNotice error={remove.error} /> : null}

      <ul aria-label={t('nav.processes')} className="mx-auto grid max-w-[1040px] grid-cols-1 gap-6 md:grid-cols-2 lg:gap-8">
        {processes.data?.map((process) => (
          <li key={process.id} className="group relative min-w-0">
            <Link
              to={paths.process(process.id)}
              className="flex min-h-[200px] items-center justify-center rounded-[20px] border border-hairline bg-canvas/50 px-8 py-14 text-center text-[24px] font-medium leading-tight tracking-[-0.035em] transition-colors hover:bg-canvas motion-reduce:transition-none sm:min-h-[240px] sm:text-[28px]"
            >
              <span className="min-w-0 break-words">{process.name}</span>
            </Link>
            {isManager ? (
              confirming === process.id ? (
                <div className="absolute inset-x-3 bottom-3 flex flex-wrap items-center justify-end gap-1.5 rounded-[12px] bg-surface p-2 shadow-lift ring-1 ring-line">
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
                  className="absolute bottom-3 right-3 text-nopagar hover:text-nopagar [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:group-focus-within:opacity-100"
                >
                  <Trash2 size={14} strokeWidth={1.8} />
                </Button>
              )
            ) : null}
          </li>
        ))}
        <li>
          <Link
            to={paths.newProcess}
            aria-label={t('nav.newProcess')}
            className="flex h-full min-h-[200px] items-center justify-center rounded-[20px] border-2 border-dashed border-faint/45 bg-surface text-faint transition-colors hover:border-muted hover:text-ink motion-reduce:transition-none sm:min-h-[240px]"
          >
            <Plus size={40} strokeWidth={1.25} aria-hidden="true" />
          </Link>
        </li>
      </ul>
    </main>
  )
}
