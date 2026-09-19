import type { components } from './schema'
import { get, put } from './http'

export type GatheringSettings = components['schemas']['GatheringSettings']
export type MailOverview = components['schemas']['MailOverview']

export const mailApi = {
  gathering: (processId: number) => get<GatheringSettings>(`/processes/${processId}/gathering`),
  saveGathering: (processId: number, value: GatheringSettings) =>
    put<GatheringSettings>(`/processes/${processId}/gathering`, value),
  overview: (processId: number) => get<MailOverview>(`/processes/${processId}/mail-ingestion`),
}
