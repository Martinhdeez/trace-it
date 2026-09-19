import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Mail, ArrowUpRight } from 'lucide-react'
import { mailApi, mailKeys } from '../../api/mail'
import type { MailAccount } from '../../api/mail'
import { connectionStatus, mailDate, mailError, type MailTone } from '../../lib/mail'
import { paths } from '../../lib/paths'
import { cn } from '../../lib/cn'
import { ErrorNotice } from '../shell/Notice'

export function MailBadge({ label, tone = 'neutral' }: { label: string; tone?: MailTone }) {
  return <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
    tone === 'success' ? 'bg-pagar-soft text-pagar' : tone === 'review' ? 'bg-escalar-soft text-escalar' : tone === 'error' ? 'bg-nopagar-soft text-nopagar' : 'bg-well text-muted')}>
    <span aria-hidden="true">{tone === 'success' ? '✓' : tone === 'error' ? '!' : tone === 'review' ? '◇' : '·'}</span>{label}
  </span>
}
export function MailConnection({ account }: { account: MailAccount | null | undefined }) {
  const state = connectionStatus(account)
  return <div className="space-y-2 text-sm">
    <MailBadge {...state} />
    <p className="text-muted">Última consulta correcta: {mailDate(account?.last_poll_at)}</p>
    {account?.heartbeat_at && <p className="text-xs text-muted">Última señal del trabajador: {mailDate(account.heartbeat_at)}</p>}
    {account?.error && <p className="text-sm text-nopagar">{mailError(account.error)}</p>}
    {account?.retry_at && <p className="text-xs text-muted">Próximo intento de conexión: {mailDate(account.retry_at)}</p>}
  </div>
}
export function MailSummary({ processId }: { processId: number }) {
  const query = useQuery({ queryKey: mailKeys.overview(processId), queryFn: () => mailApi.overview(processId), refetchInterval: 15_000 })
  const messages = query.data?.messages ?? []
  const parts = messages.flatMap(m => m.attachments)
  const pending = parts.filter(p => !['completed', 'failed', 'duplicate'].includes(p.state)).length
  const review = parts.filter(p => p.requires_review || p.error === 'manual_pending_conflict').length
  const failed = parts.filter(p => p.state === 'failed').length
  return <section aria-label="Resumen de recepción" className="mb-6 rounded-2xl border border-hairline bg-shell p-5">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h2 className="flex items-center gap-2 text-sm font-medium"><Mail size={16} />Recepción de correo</h2>
        <p className="mt-1 break-all text-sm text-muted">{query.data?.account?.username ?? 'Asigna un buzón en Ajustes para recibir PDF.'}</p></div>
      <Link className="inline-flex items-center gap-1 text-sm underline" to={paths.reception(processId)}>Abrir recepción <ArrowUpRight size={14} /></Link>
    </div>
    {query.isError ? <ErrorNotice error={query.error} /> : query.isPending ? <p role="status" className="mt-3 text-sm text-muted">Consultando recepción…</p> : <div className="mt-4 flex flex-wrap justify-between gap-4">
      <MailConnection account={query.data?.account} />
      <p className="text-sm text-muted">En correos recientes: {pending} en curso · {review} para revisión · {failed} con incidencias</p>
    </div>}
  </section>
}
