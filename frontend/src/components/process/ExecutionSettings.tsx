import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { DecisionReview, ExecutionOut, Preset, VersionDraft } from '../../api/contracts'
import { keys } from '../../api/queries'
import { useSession } from '../../state/session'
import { Button, Field, Input, Select, Textarea } from '../shell/Controls'
import { ErrorNotice } from '../shell/Notice'
import { NestedCard } from '../shell/Well'
import { ExecutionEditor } from './ExecutionEditor'
import { PublishDraft } from './PublishDraft'

const presetNames: readonly Preset[] = ['lowest_cost', 'fastest', 'balanced', 'highest_quality']

export function ProcessExecutionSettings({ processId }: { processId: number }) {
  const { isManager } = useSession()
  const query = useQuery({ queryKey: keys.execution(processId), queryFn: () => api.getExecution(processId), enabled: isManager, refetchOnWindowFocus: false })
  if (!isManager) return null
  return <section className="mt-6"><NestedCard label="Models and execution effort">
    <div className="space-y-3 p-4">
      {query.isError && <ErrorNotice error={query.error} />}
      {query.data && <SettingsForm key={`${processId}:${query.data.revision}:${query.data.version_id}`} processId={processId} initial={query.data} />}
      {query.isPending && <p>Loading execution settings…</p>}
    </div>
  </NestedCard></section>
}

function SettingsForm({ processId, initial }: { processId: number; initial: ExecutionOut }) {
  const queryClient = useQueryClient()
  const [value, setValue] = useState(initial.settings)
  const [review, setReview] = useState(initial.decision_review as DecisionReview | null)
  const [revision, setRevision] = useState(initial.revision)
  const [draft, setDraft] = useState<VersionDraft | null>(null)
  const [dirty, setDirty] = useState(false)
  const [preset, setPreset] = useState<Preset | ''>('')
  const [editorKey, setEditorKey] = useState(0)
  const [invalid, setInvalid] = useState<Record<string, boolean>>({})
  const [notice, setNotice] = useState('')
  const pendingPreset = preset ? initial.presets[preset] : null
  const save = useMutation({ mutationFn: async () => {
    const saved = await api.saveDraft(processId, {
      expected_revision: revision,
      execution: value,
      decision_review: review,
      refresh_agents: false,
    })
    setRevision(saved.revision)
    setDirty(false)
    setDraft(saved)
    const validated = await api.validateDraft(processId)
    setDraft(validated)
    void queryClient.invalidateQueries({ queryKey: keys.draft(processId) })
    setNotice('Draft saved. Review the complete candidate before publishing.')
  } })
  const busy = save.isPending
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
    {draft && <div className="border-t border-hairline pt-3">
      <PublishDraft
        key={`${draft.revision}:${draft.validation?.hash}`}
        processId={processId}
        draft={draft}
        blocked={dirty || Object.values(invalid).some(Boolean)}
      />
    </div>}
  </div>
}
