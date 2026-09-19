import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, X } from 'lucide-react'
import { mailApi, mailKeys, type MailActivity } from '../../api/mail'
import { isNotifiable, notificationText } from '../../lib/mail'
import { paths, processFromPath } from '../../lib/paths'
import { useSession } from '../../state/session'

export function MailNotifications() {
  const { user } = useSession()
  const processId = processFromPath(useLocation().pathname)
  return user && processId ? <ProcessMailNotifications key={`${user.id}:${processId}`} processId={processId} userId={user.id} /> : null
}
function ProcessMailNotifications({ processId, userId }: { processId: number; userId: number }) {
  const client = useQueryClient()
  const query = useQuery({ queryKey: mailKeys.activity(processId, userId), queryFn: () => mailApi.activity(processId), refetchInterval: 5_000 })
  const cursor = useRef<number | null>(null)
  const fetching = useRef(false)
  const [notices, setNotices] = useState<MailActivity[]>([])
  const [more, setMore] = useState(0)
  useEffect(() => {
    const data = query.data
    if (!data || fetching.current) return
    if (cursor.current === null) {
      // Existing history belongs in the persistent activity view, never in startup toasts.
      cursor.current = data.latest_id
      if (!data.initialized) {
        void mailApi.read(processId, data.latest_id).then(() => client.invalidateQueries({ queryKey: mailKeys.activity(processId, userId) })).catch(() => { cursor.current = null })
      }
      return
    }
    if (data.latest_id <= cursor.current) return
    fetching.current = true
    void (async () => {
      const newest = new Map<number, MailActivity>()
      // Catch up in bounded pages without losing transitions between polls.
      for (let page = 0; page < 10; page++) {
        const feed = await mailApi.activity(processId, cursor.current ?? 0)
        for (const event of feed.items) {
          if (isNotifiable(event)) newest.set(event.message_id, event)
          cursor.current = Math.max(cursor.current ?? 0, event.id)
        }
        if (!feed.has_more) break
      }
      if (newest.size) {
        const all = [...newest.values()].sort((a, b) => b.id - a.id)
        setNotices(all.slice(0, 3)); setMore(Math.max(0, all.length - 3))
        void client.invalidateQueries({ queryKey: ['mail-overview', processId] })
      }
    })().catch(() => { /* The next poll resumes from the last successfully consumed event. */ }).finally(() => { fetching.current = false })
  }, [query.data, query.dataUpdatedAt, processId, userId, client])
  useEffect(() => {
    if (!notices.length) return
    const timer = setTimeout(() => setNotices([]), 10_000)
    return () => clearTimeout(timer)
  }, [notices])
  return <>
    <div className="absolute bottom-4 right-5 z-20"><Link to={paths.reception(processId)} aria-label={`Actividad de correo${query.data?.unread ? `, ${query.data.unread} sin leer` : ''}`} className="inline-flex items-center gap-2 rounded-full bg-shell px-3 py-2 text-xs shadow-md ring-1 ring-line"><Bell size={14} />Correo{query.data?.unread ? <span className="rounded-full bg-ink px-1.5 text-on-ink">{query.data.unread}</span> : null}</Link></div>
    <div aria-live="polite" aria-atomic="false" className="pointer-events-none fixed bottom-16 right-4 z-50 w-[min(360px,calc(100vw-32px))] space-y-2">
      {notices.map(event => <div key={event.message_id} role="status" className="pointer-events-auto rounded-2xl border border-hairline bg-shell p-4 shadow-lg">
        <div className="flex items-start gap-3"><div className="min-w-0 flex-1"><p className="text-sm font-medium">{notificationText(event)}</p><p className="mt-1 truncate text-xs text-muted">{String(event.data.subject || 'Sin asunto')}</p></div><button aria-label="Cerrar aviso de correo" onClick={() => setNotices(n => n.filter(e => e.message_id !== event.message_id))}><X size={16} /></button></div>
        <Link className="mt-3 inline-block text-sm underline" to={`${paths.reception(processId)}#mail-${event.message_id}`} onClick={() => setNotices(n => n.filter(e => e.message_id !== event.message_id))}>Ver correo</Link>
      </div>)}
      {notices.length > 0 && more > 0 && <p className="rounded-lg bg-shell p-2 text-xs">{more} correos más en la actividad de recepción.</p>}
    </div>
  </>
}
