import type { components } from './schema'
import { get, post, put } from './http'

export type GatheringSettings = components['schemas']['GatheringSettings']
export type MailOverview = components['schemas']['MailOverview']
export type MailMessage = MailOverview['messages'][number]
export type MailAttachment = MailMessage['attachments'][number]
export type MailAccount = NonNullable<MailOverview['account']>
export type MailActivity = components['schemas']['ActivityOut']
export type MailActivityFeed = components['schemas']['MailActivityFeed']
export type MailHistory = components['schemas']['MailHistory']
export const mailKeys = {
  overview: (id: number, before?: number, message?: number) => ['mail-overview', id, before, message] as const,
  activity: (id: number, userId?: number) => ['mail-activity', id, userId] as const,
  history: (id: number, messageId: number) => ['mail-history', id, messageId] as const,
}
export const mailApi = {
  gathering: (id: number) => get<GatheringSettings>(`/processes/${id}/gathering`),
  saveGathering: (id: number, value: GatheringSettings) => put<GatheringSettings>(`/processes/${id}/gathering`, value),
  overview: (id: number, before?: number, message?: number) => get<MailOverview>(`/processes/${id}/mail-ingestion${message ? `?message_id=${message}` : before ? `?before_id=${before}` : ''}`),
  activity: (id: number, after?: number) => get<MailActivityFeed>(`/processes/${id}/mail-ingestion/activity${after != null ? `?after_id=${after}` : ''}`),
  read: (id: number, through: number) => post<MailActivityFeed>(`/processes/${id}/mail-ingestion/activity/read`, { through_id: through }),
  history: (id: number, messageId: number) => get<MailHistory>(`/processes/${id}/mail-ingestion/messages/${messageId}/history`),
  retry: (id: number, attachmentId: number, attempts: number) => post<MailMessage>(`/processes/${id}/mail-ingestion/attachments/${attachmentId}/retry`, { expected_attempts: attempts }),
}
