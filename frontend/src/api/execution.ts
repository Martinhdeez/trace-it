import { get, post, put } from './http'

export const presetNames = ['lowest_cost', 'fastest', 'balanced', 'highest_quality'] as const
export type Preset = typeof presetNames[number]
export type AgentSettings = {
  model: string
  fallback_models: string[]
  timeout_seconds: number | null
  retries: number | null
  request_limit: number | null
  model_settings: Record<string, unknown>
  limits: Record<string, number>
  [key: string]: unknown
}
export type ExtractionSettings = {
  mode: 'local' | 'api' | 'hybrid'
  primary_model_dir: string
  verification_model_dir: string
  ocr: boolean
  secondary_ocr: boolean
  vision_model: string | null
  text_judge_model: string | null
  focused_verification: boolean
  source_verification: boolean
  dpi: number
  vision_timeout_seconds: number
  judge_timeout_seconds: number
  vision_max_tokens: number
  judge_max_tokens: number
}
export type ExecutionSettings = {
  preset: Preset | 'custom'
  local_only: boolean
  local_endpoint: string
  compatible_endpoint: string | null
  agents: Record<string, AgentSettings>
  extraction: ExtractionSettings
}
export type ReviewSettings = { guidance: string; timeout_seconds: number } | null
export type ExecutionResponse = {
  settings: ExecutionSettings
  decision_review: ReviewSettings
  revision: number | null
  version_id: number | null
  presets: Record<Preset, { settings?: ExecutionSettings; error?: string }>
}
export type HistoricalCoverage = {
  evaluated: number
  not_evaluable: number
  partial: number
  none: number
  total?: number
}
export type HistoricalCaseWithoutCoverage = {
  instance_id: number
  name: string
  missing_symbols: string[]
  evaluated_rules: number[]
  unavailable_rules: { rule_id: number; symbol: string }[]
}
export type ValidationReport = {
  valid: boolean
  hash: string
  coverage?: HistoricalCoverage
  not_evaluable?: HistoricalCaseWithoutCoverage[]
  conflicts?: { instance_id: number; reason?: string }[]
  errors?: { instance_id: number; reason?: string }[]
  error?: string
  [key: string]: unknown
}
export type Draft = {
  revision: number
  snapshot: Record<string, unknown>
  validation: ValidationReport | null
}
export const executionApi = {
  get: (id: number) => get<ExecutionResponse>(`/processes/${id}/execution`),
  save: (id: number, revision: number | null, execution: ExecutionSettings, review: ReviewSettings) =>
    put<Draft>(`/processes/${id}/draft`, {
      expected_revision: revision, execution, decision_review: review,
    }),
  validate: (id: number) => post<Draft>(`/processes/${id}/draft/validate`),
  publish: (id: number, draft: Draft, reason: string) => post(`/processes/${id}/draft/publish`, {
    revision: draft.revision, validation_hash: draft.validation?.hash, reason,
  }),
}
