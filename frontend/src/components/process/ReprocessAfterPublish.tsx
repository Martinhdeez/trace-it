import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { families } from '../../api/queries'
import { Button } from '../shell/Controls'
import { ErrorNotice, Notice } from '../shell/Notice'
import { ValidationImpact } from './ValidationImpact'

export function ReprocessAfterPublish({
  processId,
  version,
  onClose,
}: {
  processId: number
  version: number
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const preview = useMutation({ mutationFn: () => api.reprocess(processId, true) })
  const apply = useMutation({
    mutationFn: () => api.reprocess(processId, false),
    onSuccess: async () => {
      await Promise.all(
        families.decisions.map((family) => queryClient.invalidateQueries({ queryKey: [family] })),
      )
    },
  })
  const result = apply.data ?? preview.data
  const changes = result?.changes.length ?? 0

  return <div className="space-y-3 rounded-[14px] bg-well p-3.5 ring-1 ring-line">
    <Notice
      title={`Versión v${version} publicada`}
      action={<button type="button" onClick={onClose} className="text-[12px] text-muted hover:text-ink">Cerrar</button>}
    >
      Las decisiones existentes siguen intactas hasta que decidas reprocesarlas.
    </Notice>

    {!result ? <Button disabled={preview.isPending} onClick={() => preview.mutate()}>
      {preview.isPending ? 'Calculando…' : 'Previsualizar reprocesado'}
    </Button> : <>
      <ValidationImpact processId={processId} validation={result} />
      {Object.keys(result.down_sources ?? {}).length ? <p className="text-[12px] text-escalar">
        Hay fuentes no disponibles: {Object.keys(result.down_sources ?? {}).join(', ')}.
      </p> : null}
      {apply.isSuccess ? <Notice title={`${changes} decisión${changes === 1 ? '' : 'es'} actualizada${changes === 1 ? '' : 's'}`} /> : changes > 0 ? <div className="space-y-1.5">
        <Button tone="primary" disabled={apply.isPending} onClick={() => apply.mutate()}>
          {apply.isPending ? 'Reprocesando…' : `Aplicar a ${changes} decisión${changes === 1 ? '' : 'es'}`}
        </Button>
        <p className="text-[11px] text-faint">Al aplicar se sincronizan las fuentes. Las decisiones protegidas no se sustituyen.</p>
      </div> : null}
    </>}
    {preview.isError ? <ErrorNotice error={preview.error} /> : null}
    {apply.isError ? <ErrorNotice error={apply.error} /> : null}
  </div>
}
