import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { ValidationReport, VersionDraft, VersionOut } from '../../api/contracts'
import { Button, Field, Textarea } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { HistoricalCoverage } from './HistoricalCoverage'

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
  const validation = validationOf(draft)

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
  const busy = validate.isPending || publish.isPending

  return (
    <div className="space-y-3">
      <p className="text-sm">
        Publicar incluye todos los cambios de este borrador. La validación comprueba los hechos
        guardados; no repite el OCR ni mide la calidad de un modelo.
      </p>
      <Button disabled={busy || blocked} onClick={() => validate.mutate()}>
        Validar
      </Button>
      {validate.isError && <ErrorNotice error={validate.error} />}
      {validation && (
        <div role="status">
          <HistoricalCoverage validation={validation} />
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
            <summary>Ver el borrador completo y su validación</summary>
            <pre className="max-h-96 overflow-auto text-xs">{JSON.stringify(draft, null, 2)}</pre>
          </details>
          <Field label="Motivo de la publicación">
            <Textarea value={reason} onChange={(event) => setReason(event.target.value)} />
          </Field>
          <Button
            tone="primary"
            disabled={busy || blocked || !validation.valid || !reason.trim()}
            onClick={() => publish.mutate()}
          >
            Publicar
          </Button>
        </>
      )}
      {publish.isError && <ErrorNotice error={publish.error} />}
    </div>
  )
}
