import { useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronRight, Plus, Trash2, X } from 'lucide-react'
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
      <div className="mx-auto max-w-[1040px]">
        <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-[24px] font-medium tracking-[-0.035em]">{t('nav.processes')}</h1>
          <Link
            to={paths.newProcess}
            className="inline-flex min-h-9 items-center gap-1.5 rounded-full bg-ink px-3.5 py-2 text-[12px] font-medium text-on-ink hover:bg-ink/90 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-focus"
          >
            <Plus size={14} strokeWidth={1.8} aria-hidden="true" />
            {t('nav.newProcess')}
          </Link>
        </header>
        {processes.isError ? <ErrorNotice error={processes.error} /> : null}
        {remove.isError ? <ErrorNotice error={remove.error} /> : null}

        <ul aria-label={t('nav.processes')} className="divide-y divide-hairline border-y border-hairline">
          {processes.data?.map((process) => (
            <li key={process.id} className="min-w-0">
              <div className="flex items-center gap-2">
                <Link
                  to={paths.process(process.id)}
                  className="flex min-h-20 min-w-0 flex-1 items-center justify-between gap-4 rounded-lg px-3 py-4 transition-colors hover:bg-canvas focus-visible:outline-2 focus-visible:outline-focus motion-reduce:transition-none"
                >
                  <div className="min-w-0">
                    <h2 className="break-words text-[15px] font-medium leading-6 tracking-[-0.015em]">{process.name}</h2>
                    {process.description ? (
                      <p className="mt-0.5 line-clamp-2 max-w-[72ch] break-words text-[13px] leading-5 text-muted">{process.description}</p>
                    ) : null}
                  </div>
                  <ChevronRight size={16} strokeWidth={1.6} className="shrink-0 text-muted" aria-hidden="true" />
                </Link>
                {isManager ? (
                  <Button
                    tone="ghost"
                    aria-label={t('processes.delete')}
                    title={t('processes.delete')}
                    disabled={remove.isPending}
                    onClick={() => {
                      remove.reset()
                      setConfirming(process.id)
                    }}
                    className="mr-1 min-h-9 shrink-0 px-2.5 hover:text-nopagar focus-visible:outline-2 focus-visible:outline-focus"
                  >
                    <Trash2 size={14} strokeWidth={1.8} />
                  </Button>
                ) : null}
              </div>
              {isManager && confirming === process.id ? (
                <div className="mb-3 flex flex-wrap items-center justify-end gap-2 rounded-lg bg-canvas p-3">
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
              ) : null}
            </li>
          ))}
        </ul>
        {processes.isSuccess && processes.data.length === 0 ? (
          <p className="py-8 text-[13px] text-muted">{t('processes.empty')}</p>
        ) : null}
      </div>
    </main>
  )
}
