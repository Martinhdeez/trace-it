import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { keys } from '../api/queries'
import { ProcessScreen } from '../components/process/ProcessScreen'
import { Input, Select } from '../components/shell/Controls'
import { Empty, ErrorNotice } from '../components/shell/Notice'
import { NestedCard } from '../components/shell/Well'
import { paths } from '../lib/paths'

const OCR_KEY = (processId: number) => `trace.process.${processId}.ocr`
const REVIEWER_KEY = (processId: number) => `trace.process.${processId}.reviewer`

const OCR_OPTIONS = [
  { value: 'local', label: 'Local', hint: 'Preproceso propio. Sin coste por página.' },
  { value: 'gemini', label: 'Gemini', hint: 'Mejor en escaneos difíciles. Sale por página.' },
  { value: 'got', label: 'GOT-OCR', hint: 'Experimento. No sustituye la ruta local.' },
] as const

export function ProcessSettings() {
  const processId = Number(useParams().processId)
  const queryClient = useQueryClient()
  const [ocr, setOcr] = useState('local')
  const [reviewer, setReviewer] = useState(false)

  const process = useQuery({
    queryKey: keys.process(processId),
    queryFn: () => api.getProcess(processId),
  })
  const llm = useQuery({ queryKey: keys.llm, queryFn: () => api.listLlmConfig() })

  const change = useMutation({
    mutationFn: ({ role, model }: { role: string; model: string }) =>
      api.setLlmConfig(role, model),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.llm }),
  })

  useEffect(() => {
    setOcr(window.localStorage.getItem(OCR_KEY(processId)) ?? 'local')
    setReviewer(window.localStorage.getItem(REVIEWER_KEY(processId)) === '1')
  }, [processId])

  const persistOcr = (value: string) => {
    setOcr(value)
    window.localStorage.setItem(OCR_KEY(processId), value)
  }
  const persistReviewer = (value: boolean) => {
    setReviewer(value)
    window.localStorage.setItem(REVIEWER_KEY(processId), value ? '1' : '0')
  }

  return (
    <ProcessScreen
      processId={processId}
      crumbs={[
        { label: 'Procesos', to: paths.processes },
        { label: process.data?.nombre ?? '…', to: paths.process(processId) },
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
                Qué lee las páginas antes de extraer símbolos. Hoy se guarda en este
                navegador; el motor seguirá la ruta local hasta que el API acepte el campo.
              </p>
              <Select value={ocr} onChange={(event) => persistOcr(event.target.value)}>
                {OCR_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
              <p className="text-[12px] text-faint">
                {OCR_OPTIONS.find((option) => option.value === ocr)?.hint}
              </p>
            </div>
          </NestedCard>

          <NestedCard label="modelo por paso">
            <div className="space-y-2 px-3.5 py-3">
              <p className="text-[12px] text-muted">
                Compilador, extractores y asistente. El API actual es por espacio, no por
                proceso: un cambio aquí mueve el mismo registro que ves en Ajustes globales.
              </p>
              {llm.isError ? <ErrorNotice error={llm.error} /> : null}
              {llm.data?.length === 0 ? <Empty>Sin papeles configurados.</Empty> : null}
              {(llm.data ?? []).map((config) => (
                <div key={config.papel} className="flex items-center gap-2">
                  <span className="w-32 shrink-0 font-mono text-[12px] text-muted">
                    {config.papel}
                  </span>
                  <Input
                    defaultValue={config.modelo}
                    className="font-mono"
                    onBlur={(event) => {
                      const model = event.target.value.trim()
                      if (model && model !== config.modelo) {
                        change.mutate({ role: config.papel, model })
                      }
                    }}
                  />
                </div>
              ))}
              {change.isError ? <ErrorNotice error={change.error} /> : null}
            </div>
          </NestedCard>

          <NestedCard label="revisor opcional">
            <div className="px-3.5 py-3">
              <label className="flex items-start gap-3">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={reviewer}
                  onChange={(event) => persistReviewer(event.target.checked)}
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
            </div>
          </NestedCard>
        </div>
      </div>
    </ProcessScreen>
  )
}
