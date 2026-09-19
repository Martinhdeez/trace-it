import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, FileText, Mail, RotateCcw } from 'lucide-react'
import { mailApi, mailKeys, type MailAttachment, type MailMessage } from '../../api/mail'
import { activityLabels, attachmentStatus, mailDate, mailError, notificationText, isNotifiable } from '../../lib/mail'
import { paths } from '../../lib/paths'
import { useSession } from '../../state/session'
import { Button } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { MailBadge, MailConnection } from './MailStatus'

export function MailReception({ processId }: { processId: number }) {
  const [pages, setPages] = useState<(number | undefined)[]>([undefined])
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useSearchParams()
  const focus = Number(search.get('message')) || undefined
  const before = focus ? undefined : pages.at(-1)
  const query = useQuery({ queryKey: mailKeys.overview(processId, before, focus), queryFn: () => mailApi.overview(processId, before, focus), refetchInterval: 5_000 })
  const messages = query.data?.messages ?? []
  const matches = messages.filter(m => filter === 'all' || (filter === 'review' ? m.attachments.some(p => p.requires_review || p.error === 'manual_pending_conflict') : filter === 'failed' ? m.state === 'failed' || m.attachments.some(p => p.state === 'failed') : !['completed', 'partial', 'ignored', 'failed'].includes(m.state)))
  return <div className="space-y-6">
    <section className="rounded-2xl border border-hairline p-5">
      <div className="flex flex-wrap justify-between gap-4">
        <div><h2 className="flex items-center gap-2 font-medium"><Mail size={18} />Buzón del proceso</h2>
          <p className="mt-2 break-all text-sm">{query.data?.account?.username ?? 'Todavía no hay una conexión instalada'}</p>
          <p className="mt-1 text-xs text-muted">Los nuevos PDF se leen con la configuración de extracción del proceso y se evalúan con sus reglas publicadas.</p></div>
        <Link className="text-sm underline" to={paths.processSettings(processId)}>Configurar buzón</Link>
      </div>
      <div className="mt-4"><MailConnection account={query.data?.account} /></div>
    </section>
    <MailActivityPanel processId={processId} />
    {focus && <Button onClick={() => { setSearch({}); setPages([undefined]); setFilter('all') }}>Ver todos los correos</Button>}
    <section aria-label="Correos recibidos">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-medium">Correos recibidos</h2>
        <div className="flex flex-wrap gap-1" role="group" aria-label="Filtrar correos de esta página">
          {([['all', 'Todos'], ['processing', 'En curso'], ['review', 'Para revisión'], ['failed', 'Incidencias']] as const).map(([value, label]) => <Button key={value} tone={filter === value ? 'primary' : 'ghost'} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</Button>)}
        </div>
      </div>
      {query.isPending ? <p role="status">Consultando correos…</p> : query.isError ? <ErrorNotice error={query.error} /> : matches.length ? <div className="space-y-4">{matches.map(message => <MailCard key={message.id} message={message} processId={processId} />)}</div> : <div className="rounded-2xl border border-dashed border-hairline p-8 text-center">
        <Mail className="mx-auto mb-3 text-muted" size={24} />
        <p className="font-medium">{messages.length ? 'No hay correos con este filtro en esta página' : 'Todavía no se han detectado correos'}</p>
        <p className="mt-2 text-sm text-muted">{messages.length ? 'Prueba otro filtro o consulta una página anterior.' : 'Los mensajes nuevos aparecerán después de la próxima consulta al buzón. El histórico anterior a la activación no se importa.'}</p>
      </div>}
      <div className="mt-4 flex items-center justify-between gap-3 text-xs text-muted">
        <span>Página {pages.length} · {messages.length} correos · Actualización cada 5 segundos</span>
        <div className="flex gap-2"><Button disabled={pages.length === 1} onClick={() => setPages(p => p.slice(0, -1))}>Más recientes</Button>
          <Button disabled={!query.data?.next_before_id} onClick={() => setPages(p => [...p, query.data?.next_before_id ?? undefined])}>Más antiguos</Button></div>
      </div>
    </section>
  </div>
}

function MailCard({ message, processId }: { message: MailMessage; processId: number }) {
  const [history, setHistory] = useState(false)
  const done = message.attachments.filter(p => ['completed', 'duplicate'].includes(p.state)).length
  const failed = message.attachments.filter(p => p.state === 'failed').length
  const review = message.attachments.filter(p => p.requires_review || p.error === 'manual_pending_conflict').length
  const label = message.state === 'ignored' ? 'Sin PDF adjunto' : message.state === 'retry_wait' ? 'Reintento pendiente' : failed || message.state === 'failed' ? 'Con incidencias' : review ? 'Requiere revisión' : message.state === 'completed' ? 'Procesado' : 'En curso'
  return <article id={`mail-${message.id}`} className="scroll-mt-6 overflow-hidden rounded-2xl border border-hairline bg-shell">
    <header className="border-b border-hairline p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3"><h3 className="min-w-0 break-words font-medium">{String(message.envelope?.subject || 'Sin asunto')}</h3>
        <MailBadge label={label} tone={failed || message.state === 'failed' ? 'error' : review ? 'review' : message.state === 'completed' ? 'success' : 'neutral'} /></div>
      <p className="mt-1 break-all text-sm text-muted">{String(message.envelope?.sender || 'Remitente no disponible')}</p>
      <p className="mt-2 text-xs text-muted">Detectado: {mailDate(message.created_at)} · {done}/{message.attachments.length} adjuntos procesados{failed ? ` · ${failed} con incidencias` : ''} · {message.attempts} intentos</p>
      {message.retry_at && message.state === 'retry_wait' && <p className="mt-2 text-sm">Próximo intento: {mailDate(message.retry_at)}</p>}
      {message.error && <p className="mt-2 text-sm">{mailError(message.error)}</p>}
    </header>
    <ul className="divide-y divide-hairline">{message.attachments.map(part => <Attachment key={part.id} part={part} message={message} processId={processId} />)}</ul>
    <footer className="space-y-3 bg-well/30 p-4 text-xs">
      <Button tone="ghost" aria-expanded={history} onClick={() => setHistory(v => !v)}>{history ? 'Ocultar historial' : 'Ver historial de intentos'}</Button>
      {history && <MessageHistory processId={processId} messageId={message.id} />}
      <details className="text-muted"><summary className="cursor-pointer">Detalles técnicos del correo</summary>
        <p className="mt-2 break-all">Message-ID: {String(message.envelope?.message_id || 'No disponible')}</p>
        <p>UID {message.uid} · UIDVALIDITY {message.uidvalidity}</p>
        <p>Recibido en el servidor: {String(message.envelope?.internal_date || 'Sin registro')}</p>
        {message.error && <p>Código: {message.error}</p>}
      </details>
    </footer>
  </article>
}
function Attachment({ part, message, processId }: { part: MailAttachment; message: MailMessage; processId: number }) {
  const { isManager } = useSession()
  const client = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const retry = useMutation({ mutationFn: () => mailApi.retry(processId, part.id, message.attempts), onSuccess: () => {
    setConfirm(false)
    void client.invalidateQueries({ queryKey: ['mail-overview', processId] })
    void client.invalidateQueries({ queryKey: ['mail-history', processId, message.id] })
    void client.invalidateQueries({ queryKey: ['mail-activity', processId] })
  } })
  const status = attachmentStatus(part, message)
  const step = ['completed', 'duplicate'].includes(part.state) ? 3 : part.state === 'imported' ? 2 : part.state === 'reading' ? 1 : 0
  return <li className="space-y-3 p-4 sm:p-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><p className="flex min-w-0 items-start gap-2 text-sm font-medium"><FileText className="shrink-0" size={17} /><span className="break-all">{part.original_name}</span></p><MailBadge {...status} /></div>
    {part.state !== 'failed' && <ol aria-label={`Progreso de ${part.original_name}`} className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted">
      {['Recibido', 'Lectura del documento', 'Evaluación', 'Resultado'].map((label, index) => <li key={label} aria-current={index === step ? 'step' : undefined} className={index === step ? 'font-medium text-ink' : ''}>{index < step ? '✓ ' : ''}{label}{index < 3 ? ' →' : ''}</li>)}
    </ol>}
    {part.error && <p className="text-sm">{mailError(part.error)}</p>}
    {part.decision && <p className="text-sm"><strong>{part.decision.replaceAll('_', ' ')}</strong>{part.reason ? ` · ${part.reason}` : ''}</p>}
    {(part.reading_at || part.completed_at) && <p className="text-xs text-muted">{part.reading_at ? `Lectura iniciada: ${mailDate(part.reading_at)}` : ''}{part.completed_at ? ` · Terminó: ${mailDate(part.completed_at)}` : ''}</p>}
    <div className="flex flex-wrap items-center gap-4 text-sm">
      {part.instance_id && <Link className="inline-flex items-center gap-1 underline" to={paths.instance(processId, part.instance_id)}>Abrir documento <ArrowUpRight size={13} /></Link>}
      {part.instance_id && (part.requires_review || part.error === 'manual_pending_conflict') && <Link className="underline" to={paths.reviewCase(processId, part.instance_id)}>Revisar decisión</Link>}
      {part.instance_id && <Link className="underline" to={paths.instance(processId, part.instance_id)}>Ver trazabilidad</Link>}
      {part.execution_id && <Link className="underline" to={paths.instances(processId, part.execution_id)}>Ejecución #{part.execution_id}</Link>}
      {isManager && part.can_retry && <Button disabled={retry.isPending || confirm} onClick={() => setConfirm(true)}><RotateCcw size={13} />Reintentar lectura</Button>}
    </div>
    {confirm && <div className="space-y-3 rounded-xl border border-hairline p-3 text-sm" role="group" aria-label="Confirmar reintento">
      <p>Se volverá a leer únicamente este adjunto desde su correo original. Se conservará el historial y no se modificarán decisiones ya tomadas.</p>
      <div className="flex gap-2"><Button disabled={retry.isPending} onClick={() => retry.mutate()}>{retry.isPending ? 'Solicitando…' : 'Confirmar reintento'}</Button><Button tone="ghost" disabled={retry.isPending} onClick={() => setConfirm(false)}>Cancelar</Button></div>
    </div>}
    {retry.isError && <ErrorNotice error={retry.error} />}
    {part.error && <details className="text-xs text-muted"><summary>Detalle técnico del adjunto</summary><p className="mt-1">Código: {part.error} · Parte MIME: {part.part}</p></details>}
  </li>
}
function MessageHistory({ processId, messageId }: { processId: number; messageId: number }) {
  const query = useQuery({ queryKey: mailKeys.history(processId, messageId), queryFn: () => mailApi.history(processId, messageId), refetchInterval: 5_000 })
  if (query.isPending) return <p role="status">Cargando historial…</p>
  if (query.isError) return <ErrorNotice error={query.error} />
  const items = [
    ...query.data.activities.map(e => ({ key: `a${e.id}`, at: e.created_at, label: activityLabels[e.kind] ?? e.kind, error: e.data.error ?? e.data.previous_error, author: e.data.author })),
    ...query.data.operator_audit.filter(e => e.data.action !== 'retry_attachment').map(e => ({ key: `o${e.id}`, at: e.created_at, label: String(e.data.action).includes('completed') ? 'Reintento del operador completado' : String(e.data.action).includes('failed') ? 'Reintento del operador interrumpido' : 'Intervención del operador', error: e.data.previous_attachment_error ?? e.data.previous_error, author: e.data.author })),
  ].sort((a, b) => Date.parse(a.at) - Date.parse(b.at))
  return items.length ? <ol className="space-y-2 border-l border-hairline pl-4">{items.map(e => <li key={e.key}><span className="font-medium">{e.label}</span> · {mailDate(e.at)}{e.author ? ` · ${String(e.author)}` : ''}{e.error ? <p className="mt-1 text-muted">Incidencia registrada: {mailError(String(e.error))}</p> : null}</li>)}</ol> : <p className="text-muted">No hay transiciones registradas para este correo anterior a la actualización.</p>
}
function MailActivityPanel({ processId }: { processId: number }) {
  const { user } = useSession()
  const client = useQueryClient()
  const query = useQuery({ queryKey: mailKeys.activity(processId, user?.id), queryFn: () => mailApi.activity(processId), refetchInterval: 5_000 })
  const read = useMutation({ mutationFn: () => mailApi.read(processId, query.data?.latest_id ?? 0), onSuccess: () => void client.invalidateQueries({ queryKey: ['mail-activity', processId] }) })
  return <details className="rounded-2xl border border-hairline p-4">
    <summary className="cursor-pointer text-sm font-medium">Actividad de recepción{query.data?.unread ? ` · ${query.data.unread} sin leer` : ''}</summary>
    {query.isError && <ErrorNotice error={query.error} />}
    {query.isPending && <p className="mt-3 text-sm" role="status">Cargando actividad…</p>}
    {query.data && <div className="mt-4 space-y-3"><Button disabled={!query.data.unread || read.isPending} onClick={() => read.mutate()}>Marcar como leído</Button>
      <ul className="space-y-3">{query.data.items.filter(isNotifiable).map(e => <li key={e.id} className="text-sm"><Link to={`${paths.reception(processId)}?message=${e.message_id}#mail-${e.message_id}`} className="underline">{notificationText(e)}</Link><p className="mt-1 text-xs text-muted">{String(e.data.subject || 'Sin asunto')} · {mailDate(e.created_at)}{e.id > query.data.through_id ? ' · Sin leer' : ''}</p></li>)}</ul>
      {!query.data.items.length && <p className="text-sm text-muted">Las próximas novedades aparecerán aquí.</p>}
      {query.data.has_more && <p className="text-xs text-muted">Mostrando la actividad más reciente. Cada correo conserva su historial completo.</p>}
    </div>}
    {read.isError && <ErrorNotice error={read.error} />}
  </details>
}
