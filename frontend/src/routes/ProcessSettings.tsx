import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import type { DecisionReview, ExecutionOut, ExtractionSettings } from '../api/contracts'
import { keys } from '../api/queries'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { UseCaseModels } from '../components/process/UseCaseModels'
import { Select, Textarea } from '../components/shell/Controls'
import { ErrorNotice, Notice } from '../components/shell/Notice'
import { NestedCard } from '../components/shell/Well'
import { t } from '../i18n'
import { paths } from '../lib/paths'

const OCR_OPTIONS = [
  { value: 'local', hint: 'Modelos locales. Sin coste por página.' },
  { value: 'api', hint: 'Un proveedor con visión. Mejor en escaneos difíciles; sale por página.' },
  { value: 'hybrid', hint: 'Local primero, y el proveedor solo donde la lectura local no basta.' },
] as const

const DEFAULT_GUIDANCE =
  'Revisa si la decisión del motor es coherente con el documento y las fuentes. Si no lo es, explica por qué.'

export function ProcessSettings() {
  const processId = Number(useParams().processId)
  const queryClient = useQueryClient()
  const [saved, setSaved] = useState(false)

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  // The draft if there is one, else the published version: what the next save edits.
  const execution = useQuery({
    queryKey: keys.execution(processId),
    queryFn: () => api.getExecution(processId),
  })
  const settings = execution.data?.settings
  const review = execution.data?.decision_review as DecisionReview | null | undefined
  const [guidance, setGuidance] = useState<string | null>(null)

  // Every change goes into the draft; publishing makes it apply.
  const save = useMutation({
    mutationFn: (body: { execution?: ExecutionOut['settings']; decision_review?: DecisionReview | null }) =>
      api.saveDraft(processId, {
        expected_revision: execution.data?.revision ?? null,
        refresh_agents: false,
        ...body,
      }),
    onSuccess: () => {
      setSaved(true)
      void queryClient.invalidateQueries({ queryKey: keys.execution(processId) })
      void queryClient.invalidateQueries({ queryKey: keys.draft(processId) })
    },
  })

  const setMode = (mode: ExtractionSettings['mode']) => {
    if (!settings) return
    save.mutate({ execution: { ...settings, extraction: { ...settings.extraction, mode } } })
  }
  const setReviewer = (enabled: boolean) => {
    save.mutate({
      decision_review: enabled
        ? { guidance: guidance?.trim() || review?.guidance || DEFAULT_GUIDANCE, timeout_seconds: review?.timeout_seconds ?? 30 }
        : null,
    })
  }
  const mode = settings?.extraction.mode ?? 'local'

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.name ?? '…', to: paths.process(processId) },
        { label: 'Ajustes' },
      ]}
    >
      <div className="min-h-0 flex-1 overflow-y-auto px-8 pb-10 pt-4">
        <header className="mb-8">
          <p className="text-[13px] text-muted">Ajustes del proceso</p>
          <h1 className="mt-1 text-[32px] font-medium leading-[1.1] tracking-[-0.045em]">
            Cómo corre cada paso
          </h1>
          <p className="mt-2 max-w-xl text-[14.5px] leading-6 text-muted">
            OCR, modelos por papel y si un revisor opcional mira el resultado del motor.
            El usuario del espacio sigue en Ajustes, abajo a la izquierda.
          </p>
        </header>

        <div className="max-w-2xl space-y-3">
          <NestedCard label="ocr">
            <div className="space-y-2 px-3.5 py-3">
              <p className="text-[12px] text-muted">
                Qué lee las páginas antes de extraer símbolos. Se guarda en el borrador del proceso.
              </p>
              {execution.isError ? <ErrorNotice error={execution.error} /> : null}
              <Select
                value={mode}
                disabled={!settings || save.isPending}
                onChange={(event) => setMode(event.target.value as ExtractionSettings['mode'])}
              >
                {OCR_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {t(`extractionMode.${option.value}`)}
                  </option>
                ))}
              </Select>
              <p className="text-[12px] text-faint">
                {OCR_OPTIONS.find((option) => option.value === mode)?.hint}
              </p>
            </div>
          </NestedCard>

          <NestedCard label="modelos del caso de uso (compartidos)">
            <div className="space-y-2 px-3.5 py-3">
              <p className="text-[12px] text-muted">
                Compilador, extractores y asistente. Son del caso de uso, no de este proceso: un
                cambio aquí lo ven todos los procesos que lo comparten.
              </p>
              {process.data?.use_case_id != null ? (
                <UseCaseModels useCaseId={process.data.use_case_id} />
              ) : null}
            </div>
          </NestedCard>

          <NestedCard label="revisor opcional">
            <div className="px-3.5 py-3">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={review != null}
                  disabled={!execution.data || save.isPending}
                  onChange={(event) => setReviewer(event.target.checked)}
                />
                <span>
                  <span className="block text-[13px] text-ink">
                    Pedir una segunda lectura después del motor
                  </span>
                  <span className="mt-1 block text-[12px] leading-5 text-muted">
                    Si el modelo discrepa, el caso va a Revisión. No cambia un hallazgo de
                    regla. Desactivado por defecto, como en ADR 0021.
                  </span>
                </span>
              </label>
              <Textarea
                rows={2}
                value={guidance ?? review?.guidance ?? DEFAULT_GUIDANCE}
                onChange={(event) => setGuidance(event.target.value)}
                onBlur={() => {
                  if (review && guidance != null && guidance.trim() !== review.guidance) setReviewer(true)
                }}
                className="mt-1"
              />
            </div>
          </NestedCard>
          {save.isError ? <ErrorNotice error={save.error} /> : null}
          {saved ? (
            <Notice
              title="Queda en el borrador. Publica para que se aplique"
              action={
                <Link to={paths.process(processId)} className="text-[12px] text-muted hover:text-ink">
                  Ir al Panel
                </Link>
              }
            />
          ) : null}
        </div>
      </div>
    </ProcessScreen>
  )
}
