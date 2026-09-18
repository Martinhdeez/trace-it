import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import { Overlay } from '../shell/Overlay'
import { t } from '../../i18n'
import { paths } from '../../lib/paths'
import { cajaFileCount } from '../../data/catalog'
import { PROCESS } from '../../lib/paths'

export function NewRunDialog({
  processId,
  open,
  onClose,
}: {
  processId: string
  open: boolean
  onClose: () => void
}) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => api.createRun({ processId }),
    onSuccess: async (run) => {
      await queryClient.invalidateQueries()
      onClose()
      navigate(paths.run(processId, run.id))
    },
    onError: () => setError('No se pudo lanzar el run.'),
  })

  if (!open) return null

  const n = processId === PROCESS.reconcilePayments ? cajaFileCount : 3

  return (
    <Overlay onClose={onClose}>
      <div className="overflow-hidden rounded-[20px] bg-white p-5 shadow-[0_16px_50px_rgba(19,19,19,0.12)] ring-1 ring-black/[0.06]">
        <p className="text-[13px] text-muted">{t('process.kicker')}</p>
        <h2 className="mt-1 text-[22px] font-medium tracking-[-0.03em]">{t('process.newRun')}</h2>
        <p className="mt-2 text-[14px] leading-6 text-muted">
          {processId === PROCESS.reconcilePayments
            ? `Toma las ${n} facturas de La Caja, aplica la norma activa de este proceso y deja el lote en cola.`
            : `Run de prueba con ${n} archivos. Sirve para ver cola, decisión y revisión sin lote real.`}
        </p>
        {error ? <p className="mt-3 text-[13px] text-nopagar">{error}</p> : null}
        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-white disabled:opacity-60"
          >
            {mutation.isPending ? t('process.launching') : t('process.launchRun')}
          </button>
          <button type="button" onClick={onClose} className="rounded-full px-4 py-2 text-[13px] text-muted">
            {t('newProcess.cancel')}
          </button>
        </div>
      </div>
    </Overlay>
  )
}
