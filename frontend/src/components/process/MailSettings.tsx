import { Link } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, RotateCcw } from 'lucide-react'
import { mailApi, mailKeys, type MailMessage } from '../../api/mail'
import { attachmentStatus, connectionStatus, mailDate, mailError, type MailTone } from '../../lib/mail'
import { cn } from '../../lib/cn'
import { paths } from '../../lib/paths'
import { useSession } from '../../state/session'
import { Select } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'

/** The one mailbox the deployment offers; assigning it does not open the connection. */
const MAILBOX = 'migration-test@j-aautomation.com' as const
const RECENT = 8

const dot: Record<MailTone, string> = {
  success: 'bg-pagar',
  review: 'bg-escalar',
  error: 'bg-nopagar',
  neutral: 'bg-faint',
}

/**
 * Mail, as a process setting: which mailbox feeds the process, whether it is listening,
 * and the last few mails with where their PDFs ended up.
 */
export function MailSettings({ processId }: { processId: number }) {
  const { isManager } = useSession()
  const client = useQueryClient()
  const settings = useQuery({
    queryKey: ['mail-gathering', processId],
    queryFn: () => mailApi.gathering(processId),
  })
  const overview = useQuery({
    queryKey: mailKeys.overview(processId),
    queryFn: () => mailApi.overview(processId),
    refetchInterval: 10_000,
  })
  const save = useMutation({
    mutationFn: (email: typeof MAILBOX | null) => mailApi.saveGathering(processId, { email }),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['mail-gathering', processId] }),
  })
  const account = overview.data?.account
  const status = connectionStatus(account)
  const messages = (overview.data?.messages ?? []).slice(0, RECENT)
  const error = settings.error ?? overview.error ?? save.error

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <label className="block min-w-[240px] flex-1">
          <span className="text-[12px] text-muted">Buzón que alimenta el proceso</span>
          <Select
            className="mt-1"
            value={settings.data?.email ?? ''}
            disabled={!isManager || !settings.data || save.isPending}
            onChange={(event) => save.mutate(event.target.value ? MAILBOX : null)}
          >
            <option value="">Sin buzón</option>
            <option value={MAILBOX}>{MAILBOX}</option>
          </Select>
        </label>
        <p className="flex items-center gap-2 pb-2 text-[12.5px] text-muted" title={account?.error ? mailError(account.error) : undefined}>
          <span className={cn('h-2 w-2 rounded-full', dot[status.tone])} />
          {status.label}
          {account?.last_poll_at ? ` · ${mailDate(account.last_poll_at)}` : ''}
        </p>
      </div>
      {error ? <ErrorNotice error={error} /> : null}

      <div>
        <p className="text-[12px] text-muted">Últimos correos</p>
        {overview.isPending ? (
          <p className="mt-2 text-[12.5px] text-faint">Consultando…</p>
        ) : messages.length ? (
          <ul className="mt-2 divide-y divide-hairline overflow-hidden rounded-[12px] ring-1 ring-line">
            {messages.map((message) => (
              <MailRow key={message.id} message={message} processId={processId} canRetry={isManager} />
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[12.5px] text-faint">
            Todavía no ha llegado ningún correo. Los PDF que lleguen al buzón se leen y deciden solos.
          </p>
        )}
      </div>
    </div>
  )
}

/** One mail: who sent it, and each PDF with its state and a way into the document. */
function MailRow({ message, processId, canRetry }: { message: MailMessage; processId: number; canRetry: boolean }) {
  const client = useQueryClient()
  const retry = useMutation({
    mutationFn: (partId: number) => mailApi.retry(processId, partId, message.attempts),
    onSuccess: () => void client.invalidateQueries({ queryKey: ['mail-overview', processId] }),
  })
  return (
    <li id={`mail-${message.id}`} className="px-3.5 py-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <p className="min-w-0 truncate text-[13px] text-ink">{String(message.envelope?.subject || 'Sin asunto')}</p>
        <span className="shrink-0 text-[11px] text-faint">{mailDate(message.created_at)}</span>
      </div>
      <p className="truncate text-[11.5px] text-muted">{String(message.envelope?.sender || '—')}</p>
      {message.attachments.length ? (
        <ul className="mt-1.5 space-y-1">
          {message.attachments.map((part) => {
            const status = attachmentStatus(part, message)
            return (
              <li key={part.id} className="flex items-center gap-2 text-[12px]">
                <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', dot[status.tone])} />
                <span className="min-w-0 truncate font-mono text-[11.5px]" title={part.error ? mailError(part.error) : undefined}>
                  {part.original_name}
                </span>
                <span className="shrink-0 text-muted">· {status.label}</span>
                {part.instance_id ? (
                  <Link
                    to={paths.instance(processId, part.instance_id)}
                    className="ml-auto inline-flex shrink-0 items-center gap-0.5 text-muted hover:text-ink"
                  >
                    Abrir <ArrowUpRight size={12} strokeWidth={1.75} />
                  </Link>
                ) : canRetry && part.can_retry ? (
                  <button
                    type="button"
                    disabled={retry.isPending}
                    onClick={() => retry.mutate(part.id)}
                    className="ml-auto inline-flex shrink-0 items-center gap-1 text-muted hover:text-ink disabled:opacity-50"
                  >
                    <RotateCcw size={11} strokeWidth={1.75} /> Reintentar
                  </button>
                ) : null}
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="mt-1 text-[11.5px] text-faint">Sin PDF adjunto</p>
      )}
      {retry.isError ? <ErrorNotice error={retry.error} /> : null}
    </li>
  )
}
