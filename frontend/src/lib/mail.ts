import type { MailAccount, MailActivity, MailAttachment, MailMessage } from '../api/mail'

export type MailTone = 'neutral' | 'success' | 'review' | 'error'
export function mailError(code: string | null | undefined): string {
  return ({
    invalid_pdf: 'No se ha podido abrir este PDF. El correo no se ha modificado. Puedes reintentar su lectura.',
    size_limit: 'El adjunto o el correo supera el tamaño permitido. Envía un PDF más pequeño.',
    invalid_mime: 'No se ha podido interpretar el adjunto. Envíalo como un archivo PDF adjunto, sin comprimir.',
    message_missing: 'El mensaje ya no está disponible en el buzón. Vuelve a enviar el archivo.',
    infrastructure_error: 'La lectura se interrumpió por un problema técnico.',
    operator_retry_failed: 'El último reintento se interrumpió. Consulta los detalles antes de repetirlo.',
    attachment_failure: 'Uno o varios adjuntos necesitan atención. Consulta su estado individual.',
    attempts_exhausted: 'Se ha alcanzado el límite de intentos. Requiere intervención de un operador.',
    manual_pending_conflict: 'Coincide con un documento cargado manualmente que sigue pendiente. Revísalo sin ejecutarlo de nuevo.',
    duplicate_content: 'Este mismo archivo ya estaba registrado. Se conserva el vínculo al documento original.',
    invalid_credentials: 'La conexión al buzón requiere revisar las credenciales con un operador.',
    imap_unavailable: 'No se ha podido consultar el buzón. Se volverá a intentar según la espera indicada.',
    uidvalidity_changed: 'La identidad del buzón ha cambiado. La recepción está detenida para proteger el histórico.',
    operator_halt: 'La recepción se ha detenido por intervención de un operador.',
  } as Record<string, string>)[code ?? ''] ?? 'Hay una incidencia que requiere revisar los detalles técnicos.'
}
export function connectionStatus(account: MailAccount | null | undefined, now = Date.now()) {
  if (!account) return { label: 'Sin conexión instalada', tone: 'neutral' as MailTone }
  if (account.state === 'uninitialized') return { label: 'Pendiente de inicializar', tone: 'neutral' as MailTone }
  if (account.state === 'halted' || account.worker_phase === 'stopped') return { label: 'Recepción detenida', tone: 'error' as MailTone }
  if (!account.heartbeat_at || now - Date.parse(account.heartbeat_at) > 60_000) {
    return { label: 'Sin señal reciente del trabajador', tone: 'review' as MailTone }
  }
  if (account.error) return { label: 'Conexión con incidencias', tone: 'review' as MailTone }
  return { label: account.worker_phase === 'processing' ? 'Procesando adjuntos' : 'Recepción activa', tone: 'success' as MailTone }
}
export function attachmentStatus(part: MailAttachment, message: MailMessage) {
  if (part.error === 'manual_pending_conflict') return { label: 'Revisión de documento manual', tone: 'review' as MailTone }
  if (part.state === 'failed') return { label: 'No se pudo procesar', tone: 'error' as MailTone }
  if (part.requires_review) return { label: 'Requiere revisión', tone: 'review' as MailTone }
  if (part.state === 'duplicate') return { label: 'Ya registrado', tone: 'neutral' as MailTone }
  if (part.state === 'completed') return { label: 'Procesado', tone: 'success' as MailTone }
  if (message.state === 'retry_wait') return { label: 'Reintento pendiente', tone: 'neutral' as MailTone }
  if (part.state === 'reading') return { label: 'Leyendo documento', tone: 'neutral' as MailTone }
  if (part.state === 'imported') return { label: message.state === 'evaluating' ? 'Evaluando reglas' : 'Lectura completada', tone: 'neutral' as MailTone }
  return { label: 'Recibido', tone: 'neutral' as MailTone }
}
export function notificationText(event: MailActivity): string {
  const review = Number(event.data.review_count ?? 0), failed = Number(event.data.failed_count ?? 0)
  if (event.kind === 'completed' && event.data.state === 'ignored') return 'Correo recibido · Sin PDF adjunto'
  if (event.kind === 'completed') return failed ? `Correo procesado parcialmente · ${failed} adjuntos con incidencias` : review ? `Correo procesado · ${review} PDF requieren revisión` : 'Correo procesado · Adjuntos evaluados'
  if (event.kind === 'failed') return event.data.state === 'retry_wait' ? 'Lectura interrumpida · Reintento programado' : 'No se pudo procesar el correo'
  if (event.kind === 'retry_requested') return 'Reintento solicitado · Se conserva el historial'
  return `Correo recibido · ${Number(event.data.pdf_count ?? 0)} PDF detectados`
}
export const isNotifiable = (event: MailActivity) => ['completed', 'failed', 'retry_requested'].includes(event.kind) || (event.kind === 'received' && Number(event.data.pdf_count) > 0)
export const mailDate = (value?: string | null) => value ? new Date(value).toLocaleString() : 'Sin registro todavía'
