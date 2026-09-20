import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { keys } from '../../api/queries'

/**
 * The draft is where every edit goes. `GET /execution` says whether one exists
 * (`revision`), so the console never asks for a draft that is not there.
 */
export function useDraft(processId: number, enabled = true) {
  const execution = useQuery({
    queryKey: keys.execution(processId),
    queryFn: () => api.getExecution(processId),
    enabled,
  })
  const revision = execution.data?.revision ?? null
  const draft = useQuery({
    queryKey: keys.draft(processId),
    queryFn: () => api.getDraft(processId),
    enabled: enabled && revision != null,
  })
  return {
    revision,
    snapshot: revision != null ? draft.data?.snapshot : undefined,
    pending: execution.isPending,
  }
}

