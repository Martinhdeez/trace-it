import type { components } from './schema'
import { get, post, put } from './http'

export type GatheringSettings = components['schemas']['GatheringSettings']
export type MailOverview = components['schemas']['MailOverview']
export type MailMessage = MailOverview['messages'][number]
export type MailAttachment = MailMessage['attachments'][number]
export type MailAccount = NonNullable<MailOverview['account']>
export type MailActivity = components['schemas']['ActivityOut']
export type MailActivityFeed = components['schemas']['MailActivityFeed']
export const mailKeys = {
  overview: (id: number) => ['mail-overview', id] as const,
  activity: (id: number, userId?: number) => ['mail-activity', id, userId] as const,
}
export const mailApi = {
  gathering: (id: number) => get<GatheringSettings>(`/processes/${id}/gathering`),
  saveGathering: (id: number, value: GatheringSettings) => put<GatheringSettings>(`/processes/${id}/gathering`, value),
  overview: (id: number) => get<MailOverview>(`/processes/${id}/mail-ingestion`),
  activity: (id: number, after?: number) => get<MailActivityFeed>(`/processes/${id}/mail-ingestion/activity${after != null ? `?after_id=${after}` : ''}`),
  read: (id: number, through: number) => post<MailActivityFeed>(`/processes/${id}/mail-ingestion/activity/read`, { through_id: through }),
  retry: (id: number, attachmentId: number, attempts: number) => post<MailMessage>(`/processes/${id}/mail-ingestion/attachments/${attachmentId}/retry`, { expected_attempts: attempts }),
}
