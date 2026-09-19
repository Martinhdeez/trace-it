import { useState } from 'react'
import type { AgentSettings, ExecutionSettings, ExtractionSettings } from '../../api/contracts'
import { Field, Input, Textarea } from '../shell/Controls'

function JsonField({ value, label, onChange, onValidity }: {
  value: object; label: string; onChange: (value: Record<string, never>) => void
  onValidity: (valid: boolean) => void
}) {
  const [text, setText] = useState(JSON.stringify(value, null, 2))
  const [error, setError] = useState(false)
  return <Field label={label}>
    <Textarea rows={3} className="font-mono text-xs" value={text} onChange={event => {
      setText(event.target.value)
      try {
        const parsed = JSON.parse(event.target.value)
        if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error()
        onChange(parsed)
        setError(false)
        onValidity(true)
      } catch {
        setError(true)
        onValidity(false)
      }
    }} />
    {error && <span role="alert">Enter a valid JSON object.</span>}
  </Field>
}

export function ExecutionEditor({ value, onChange, onValidity }: {
  value: ExecutionSettings; onChange: (value: ExecutionSettings) => void
  onValidity: (field: string, valid: boolean) => void
}) {
  const [verificationText, setVerificationText] = useState<string | null>(null)
  const change = (patch: Partial<ExecutionSettings>) => onChange({ ...value, ...patch, preset: 'custom' })
  const agent = (role: string, patch: Partial<AgentSettings>) => change({
    agents: { ...value.agents, [role]: { ...value.agents[role], ...patch } },
  })
  const extraction = (patch: Partial<ExecutionSettings['extraction']>) => change({
    extraction: { ...value.extraction, ...patch },
  })
  return <div className="space-y-5">
    <label className="flex gap-2 text-sm">
      <input type="checkbox" checked={value.local_only} onChange={e => change({ local_only: e.target.checked })} />
      Local model calls only, including fallbacks
    </label>
    <p className="text-xs text-muted">Use provider:model names for agents. Use local:model for the local server. Local-only requires every selected model and fallback to be local.</p>
    <div className="grid gap-3 sm:grid-cols-2">
      <Field label="Local server endpoint"><Input value={value.local_endpoint} onChange={e => change({ local_endpoint: e.target.value })} /></Field>
      <Field label="Compatible reader endpoint"><Input value={value.compatible_endpoint ?? ''} onChange={e => change({ compatible_endpoint: e.target.value || null })} /></Field>
    </div>
    {Object.entries(value.agents).map(([role, config]) => <details key={role} className="rounded-lg bg-canvas p-3">
      <summary className="cursor-pointer text-sm">{role.replaceAll('_', ' ')} <span className="ml-2 font-mono text-xs text-muted">{config.model}</span></summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="Model"><Input value={config.model ?? ''} onChange={e => agent(role, { model: e.target.value })} /></Field>
        <Field label="Fallback models, comma separated"><Input defaultValue={config.fallback_models.join(', ')} onChange={e => agent(role, { fallback_models: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })} /></Field>
        {(['timeout_seconds', 'retries', 'request_limit'] as const).map(key => <Field key={key} label={key.replaceAll('_', ' ')} hint="Blank uses the agent default.">
          <Input type="number" min={key === 'retries' ? 0 : 1} value={config[key] ?? ''} onChange={e => agent(role, { [key]: e.target.value === '' ? null : Number(e.target.value) })} />
        </Field>)}
        <JsonField label="Model parameters, including supported reasoning effort" value={config.model_settings} onChange={v => agent(role, { model_settings: v })} onValidity={valid => onValidity(`${role}.parameters`, valid)} />
        <JsonField label="Agent effort limits" value={config.limits} onChange={v => agent(role, { limits: v })} onValidity={valid => onValidity(`${role}.limits`, valid)} />
      </div>
    </details>)}
    <details open className="rounded-lg bg-canvas p-3">
      <summary className="cursor-pointer text-sm">Document extraction</summary>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <Field label="OCR mode"><select value={value.extraction.mode} onChange={e => extraction({ mode: e.target.value as ExtractionSettings['mode'] })}>
          <option value="local">Local OCR</option><option value="api">API vision</option><option value="hybrid">Hybrid</option>
        </select></Field>
        {(['primary_model_dir', 'verification_model_dir', 'vision_model', 'text_judge_model'] as const).map(key => <Field key={key} label={key.replaceAll('_', ' ')} hint={key.endsWith('_model') ? 'Blank disables. Vision: helmcode:qwen3.6, helmcode:gemma4, local:, compatible:. Judge: local:, compatible:, jev:, helmcode:.' : 'Directory of installed local OCR weights.'}>
          <Input value={value.extraction[key] ?? ''} onChange={e => extraction({ [key]: e.target.value || (key.endsWith('_model') ? null : '') })} />
        </Field>)}
        <Field label="Independent visual readers, comma separated" hint="Use different models to verify scans, for example helmcode:gemma4 or gemini:gemini-3.1-flash-lite. Later entries replace unavailable readers.">
          <Input value={verificationText ?? (value.extraction.vision_verification_models ?? []).join(', ')} onChange={e => {
            setVerificationText(e.target.value)
            extraction({ vision_verification_models: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })
          }} onBlur={() => setVerificationText(null)} />
        </Field>
        {value.extraction.mode === 'api' && !(value.extraction.vision_verification_models ?? []).length && <p role="status" className="text-sm text-amber-700">Scans need two independent visual readers to produce verified fields. Add a verification reader.</p>}
        {(['dpi', 'vision_timeout_seconds', 'judge_timeout_seconds', 'vision_max_tokens', 'judge_max_tokens', 'timeout_seconds'] as const).map(key => <Field key={key} label={key.replaceAll('_', ' ')}>
          <Input type="number" min={1} value={value.extraction[key]} onChange={e => extraction({ [key]: Number(e.target.value) })} />
        </Field>)}
        {(['ocr', 'secondary_ocr', 'focused_verification', 'source_verification'] as const).map(key => <label key={key} className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={value.extraction[key]} onChange={e => extraction({ [key]: e.target.checked })} />{key.replaceAll('_', ' ')}
        </label>)}
      </div>
    </details>
  </div>
}
