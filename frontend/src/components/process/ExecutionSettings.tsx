import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { executionApi, presetNames, type Draft, type ExecutionResponse, type Preset } from '../../api/execution'
import { useSession } from '../../state/session'
import { Button, Field, Input, Select, Textarea } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { NestedCard } from '../shell/Well'
import { ExecutionEditor } from './ExecutionEditor'
import { HistoricalCoverage } from './HistoricalCoverage'

export function ProcessExecutionSettings({ processId }: { processId: number }) {
  const { isManager } = useSession()
  const query = useQuery({ queryKey: ['execution', processId], queryFn: () => executionApi.get(processId), enabled: isManager, refetchOnWindowFocus: false })
  if (!isManager) return null
  return <section className="mt-6"><NestedCard label="Models and execution effort">
    <div className="space-y-3 p-4">
      {query.isError && <ErrorNotice error={query.error} />}
      {query.data && <SettingsForm key={`${processId}:${query.data.revision}:${query.data.version_id}`} processId={processId} initial={query.data} />}
      {query.isPending && <p>Loading execution settings…</p>}
    </div>
  </NestedCard></section>
}

function SettingsForm({ processId, initial }: { processId: number; initial: ExecutionResponse }) {
  const queryClient = useQueryClient()
  const [value, setValue] = useState(initial.settings)
  const [review, setReview] = useState(initial.decision_review)
  const [revision, setRevision] = useState(initial.revision)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [dirty, setDirty] = useState(false)
  const [preset, setPreset] = useState<Preset | ''>('')
  const [editorKey, setEditorKey] = useState(0)
  const [invalid, setInvalid] = useState<Record<string, boolean>>({})
  const [reason, setReason] = useState('')
  const [notice, setNotice] = useState('')
  const pendingPreset = preset ? initial.presets[preset] : null
  const save = useMutation({ mutationFn: async () => {
    const saved = await executionApi.save(processId, revision, value, review)
    setRevision(saved.revision)
    setDirty(false)
    setDraft(saved)
    const validated = await executionApi.validate(processId)
    setDraft(validated)
    setNotice('Draft saved. Review the complete candidate before publishing.')
  } })
  const publish = useMutation({ mutationFn: async () => {
    if (!draft) return
    await executionApi.publish(processId, draft, reason)
    await queryClient.invalidateQueries()
  } })
  const busy = save.isPending || publish.isPending
  return <div className="space-y-4">
    <p className="text-sm text-muted">Presets fill editable settings. Model choices are retained unless the deployment supplies a preset model mapping. Changes take effect after publication.</p>
    <p className="text-sm">Current configuration: <strong>{value.preset.replaceAll('_', ' ')}</strong></p>
    <fieldset disabled={busy} className="space-y-4">
      <div className="flex gap-2">
        <Select aria-label="Preview a preset" value={preset} onChange={e => setPreset(e.target.value as Preset | '')}>
          <option value="">Preview a preset…</option>
          {presetNames.map(name => <option key={name} value={name}>{name.replaceAll('_', ' ')}</option>)}
        </Select>
      </div>
      {pendingPreset && <div className="space-y-2 rounded-lg bg-canvas p-3">
        {pendingPreset.error ? <p role="alert">{pendingPreset.error}</p> : <>
          <p className="text-sm">Applying this preset replaces the settings below, including manual changes. It does not change decision-review approval rules.</p>
          <details><summary>Preview replacement settings</summary><pre className="max-h-64 overflow-auto text-xs">{JSON.stringify(pendingPreset.settings, null, 2)}</pre></details>
          <Button onClick={() => {
            if (!pendingPreset.settings) return
            setValue(structuredClone(pendingPreset.settings))
            setDirty(true)
            setInvalid({})
            setEditorKey(key => key + 1)
            setPreset('')
          }}>Apply to editor</Button>
        </>}
      </div>}
      <ExecutionEditor key={editorKey} value={value} onChange={next => { setValue(next); setDirty(true) }} onValidity={(field, valid) => setInvalid(previous => ({ ...previous, [field]: !valid }))} />
      <label className="flex gap-2 text-sm"><input type="checkbox" checked={review !== null} onChange={e => {
        setReview(e.target.checked ? { guidance: '', timeout_seconds: 30 } : null)
        setDirty(true)
      }} />Optional decision review</label>
      {review && <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Review guidance"><Textarea value={review.guidance} onChange={e => { setReview({ ...review, guidance: e.target.value }); setDirty(true) }} /></Field>
        <Field label="Review deadline, seconds"><Input type="number" min={1} max={120} value={review.timeout_seconds} onChange={e => { setReview({ ...review, timeout_seconds: Number(e.target.value) }); setDirty(true) }} /></Field>
      </div>}
      <Button disabled={Object.values(invalid).some(Boolean) || !!review && !review.guidance.trim()} onClick={() => save.mutate()}>Save draft and validate</Button>
    </fieldset>
    {save.isError && <ErrorNotice error={save.error} />}
    {notice && <p role="status" className="text-sm">{notice}</p>}
    {draft && <div className="space-y-3 border-t border-hairline pt-3">
      <p className="text-sm">Publication includes all changes in this draft. Validation checks saved facts; it does not rerun OCR or measure model quality.</p>
      <details><summary>Review complete draft and validation</summary><pre className="max-h-96 overflow-auto text-xs">{JSON.stringify(draft, null, 2)}</pre></details>
      {draft.validation && <div role="status"><HistoricalCoverage validation={draft.validation} /></div>}
      {draft.validation && !draft.validation.valid && <p role="alert" className="text-sm text-nopagar">
        Validation failed. {draft.validation.error || 'Resolve the blocking issues before publishing.'}
        {!!draft.validation.conflicts?.length && ` ${draft.validation.conflicts.length} historical conflict(s).`}
        {!!draft.validation.errors?.length && ` ${draft.validation.errors.length} evaluation error(s).`}
      </p>}
      <Field label="Publication reason"><Input value={reason} onChange={e => setReason(e.target.value)} /></Field>
      <Button tone="primary" disabled={busy || dirty || Object.values(invalid).some(Boolean) || !draft.validation?.valid || !reason.trim()} onClick={() => publish.mutate()}>Publish reviewed version</Button>
      {publish.isError && <ErrorNotice error={publish.error} />}
    </div>}
  </div>
}
