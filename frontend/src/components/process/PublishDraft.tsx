import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { ValidationReport, VersionDraft, VersionOut } from '../../api/contracts'
import { keys } from '../../api/queries'
import { Button, Field, Textarea } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { t } from '../../i18n'
import { HistoricalCoverage } from './HistoricalCoverage'
import { ValidationImpact } from './ValidationImpact'

export function validationOf(draft: VersionDraft): ValidationReport | null {
  return draft.validation as ValidationReport | null
}

/** Validate the draft, read its historical coverage, then publish it as the next version. */
export function PublishDraft({
  processId,
  draft: initial,
  blocked = false,
  onPublished,
}: {
  processId: number
  draft: VersionDraft
  /** The caller has unsaved edits, or edits that do not parse. */
  blocked?: boolean
  onPublished?: (version: VersionOut) => void
}) {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState(initial)
  const [reason, setReason] = useState('')
  const [confirmDiscard, setConfirmDiscard] = useState(false)
  const validation = validationOf(draft)
  // reviewer-agent FE-4 (docs/reviewer-agent.md): an accepted suggestion compiles in the
  // background, so the draft is not ready yet. If merging a newer version from Carlos, keep his
  // UI and preserve: Validar and Publicar stay disabled while any rule has status `compiling`.
  const compilingRules = useQuery({
    queryKey: keys.rules(processId, 'compiling'),
    queryFn: () => api.listRules(processId, 'compiling'),
    refetchInterval: (query) => (query.state.data?.length ? 2_000 : false),
  })
  const compiling = (compilingRules.data?.length ?? 0) > 0

  const validate = useMutation({
    mutationFn: () => api.validateDraft(processId),
    onSuccess: setDraft,
  })
  const publish = useMutation({
    mutationFn: () =>
      api.publishDraft(processId, {
        revision: draft.revision,
        validation_hash: validation?.hash ?? '',
        reason: reason.trim(),
      }),
    onSuccess: async (version) => {
      await queryClient.invalidateQueries()
      onPublished?.(version)
    },
  })
  const discard = useMutation({
    mutationFn: () => api.discardDraft(processId, draft.revision),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: keys.execution(processId) })
      await queryClient.invalidateQueries({ queryKey: keys.draft(processId) })
    },
  })
  const busy = validate.isPending || publish.isPending || discard.isPending

  return (
    <div className="space-y-3">
      <p className="text-sm">
        Publicar incluye todos los cambios de este borrador. La validación comprueba los hechos
        guardados; no repite el OCR ni mide la calidad de un modelo.
      </p>
      <Button disabled={busy || blocked || compiling} onClick={() => validate.mutate()}>
        {validate.isPending ? 'Validating and backtesting…' : 'Validate and backtest'}
      </Button>
      {compiling && <p role="status" className="text-[12px] text-muted">{t('reviewerAgent.compiling')}</p>}
      {compilingRules.isError && <ErrorNotice error={compilingRules.error} />}
      {validate.isError && <ErrorNotice error={validate.error} />}
      {validation && (
        <div role="status" className="space-y-3">
          <HistoricalCoverage validation={validation} />
          <ValidationImpact processId={processId} validation={validation} />
        </div>
      )}
      {validation && !validation.valid && (
        <p role="alert" className="text-sm text-nopagar">
          La validación ha fallado. {validation.error || 'Resuelve lo que bloquea antes de publicar.'}
          {!!validation.conflicts?.length && ` ${validation.conflicts.length} conflicto(s) con el histórico.`}
          {!!validation.errors?.length && ` ${validation.errors.length} error(es) de evaluación.`}
        </p>
      )}
      {validation && (
        <>
          <details>
            <summary className="cursor-pointer text-[12px] text-muted">Detalles técnicos del borrador y la validación</summary>
            <pre className="max-h-96 overflow-auto text-xs">{JSON.stringify(draft, null, 2)}</pre>
          </details>
          <Field label="Motivo (opcional)">
            <Textarea
              rows={2}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Por qué publicas esta versión. Queda en el historial."
            />
          </Field>
          <Button
            tone="primary"
            disabled={busy || blocked || compiling || !validation.valid}
            onClick={() => publish.mutate()}
          >
            Publicar
          </Button>
        </>
      )}
      {publish.isError && <ErrorNotice error={publish.error} />}
      <div className="border-t border-hairline pt-3">
        {confirmDiscard ? <div className="flex items-center gap-2">
          <p className="mr-auto text-[12px] text-muted">Se perderán los cambios no publicados.</p>
          <Button tone="ghost" disabled={busy} onClick={() => setConfirmDiscard(false)}>Cancelar</Button>
          <Button disabled={busy} onClick={() => discard.mutate()}>Confirmar descarte</Button>
        </div> : <Button tone="ghost" disabled={busy} onClick={() => setConfirmDiscard(true)}>
          Descartar borrador
        </Button>}
        {discard.isError && <ErrorNotice error={discard.error} />}
      </div>
    </div>
  )
}
