import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { api, ApiError } from '../../api/client'
import { Button } from '../shell/Controls'
import { Overlay } from '../shell/Overlay'
import { Notice } from '../shell/Notice'

/**
 * The backend answers 409 while any instance is still PENDING, so the blocked
 * case is the one worth showing well.
 */
export function ExportButton({ processId }: { processId: number }) {
  const [blocked, setBlocked] = useState<string | null>(null)

  const download = useMutation({
    mutationFn: () => api.exportOutcomes(processId),
    onSuccess: (jsonl) => {
      const blob = new Blob([jsonl], { type: 'application/x-ndjson' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'outcomes.jsonl'
      link.click()
      URL.revokeObjectURL(url)
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) setBlocked(error.message)
    },
  })

  return (
    <>
      <Button
        tone="primary"
        onClick={() => {
          setBlocked(null)
          download.mutate()
        }}
        disabled={download.isPending}
      >
        <Download size={12} strokeWidth={2} />
        {download.isPending ? 'Exportando…' : 'Exportar'}
      </Button>

      {blocked ? (
        <Overlay onClose={() => setBlocked(null)}>
          <div className="rounded-[16px] bg-white p-4 shadow-[0_16px_50px_rgba(19,19,19,0.12)] ring-1 ring-black/[0.06]">
            <Notice tone="warning" title="No se puede exportar todavía">
              {blocked}
            </Notice>
            <div className="mt-3 flex justify-end">
              <Button tone="soft" onClick={() => setBlocked(null)}>
                Entendido
              </Button>
            </div>
          </div>
        </Overlay>
      ) : null}
    </>
  )
}
