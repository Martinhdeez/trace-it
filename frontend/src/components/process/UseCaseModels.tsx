import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { AgentConfigOut } from '../../api/contracts'
import { keys } from '../../api/queries'
import { Input } from '../shell/Controls'
import { Empty, ErrorNotice } from '../shell/Notice'

/** The model each agent of one use case runs. One request; a change is a new agent version. */
export function UseCaseModels({ useCaseId }: { useCaseId: number }) {
  const queryClient = useQueryClient()
  const useCase = useQuery({
    queryKey: keys.useCase(useCaseId),
    queryFn: () => api.getUseCase(useCaseId),
  })
  const change = useMutation({
    mutationFn: ({ agent, model }: { agent: AgentConfigOut; model: string }) =>
      api.setAgentModel(useCaseId, agent, model),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.useCase(useCaseId) }),
  })
  const agents = useCase.data?.agents ?? []

  return (
    <>
      {useCase.isError ? <ErrorNotice error={useCase.error} /> : null}
      {useCase.data && agents.length === 0 ? <Empty>Sin papeles configurados.</Empty> : null}
      {agents.map((agent) => (
        <div key={agent.role} className="flex items-center gap-2">
          <span className="w-32 shrink-0 font-mono text-[12px] text-muted">{agent.role}</span>
          <Input
            key={`${agent.role}:${agent.version}`}
            defaultValue={agent.config.model ?? ''}
            className="font-mono"
            onBlur={(event) => {
              const model = event.target.value.trim()
              if (model && model !== agent.config.model) change.mutate({ agent, model })
            }}
          />
        </div>
      ))}
      {change.isError ? <ErrorNotice error={change.error} /> : null}
    </>
  )
}
