import type { RunOut } from '../../api/contracts'
import { label, money, number } from '../metrics/usage'

export function RunCost({ cost, detail = false }: { cost: RunOut['cost']; detail?: boolean }) {
  const total = cost ? cost.known_cost_usd + (cost.estimated_cost_usd ?? 0) : 0
  const missing = cost ? cost.unpriced_requests - (cost.estimated_requests ?? 0) : 0
  const amount = !cost
    ? label('runCostUnavailable')
    : !total && missing && !cost.estimated_requests
      ? label('unknownOnly')
      : `${money(total)}${cost.estimated_requests ? ` (${label('estimated')})` : ''}${missing > 0 ? ` (${label('partial')})` : ''}`
  return (
    <span className="block text-xs text-muted" title={label('runCostScope')}>
      <span className="tabular-nums">{label('runCost')}: {amount}</span>
      {detail && (
        <>
          {cost && (
            <span className="mt-1 block tabular-nums">
              {number(cost.requests)} {label('requests')} ·{' '}
              {number(cost.input_tokens + cost.output_tokens)} {label('tokens')} ·{' '}
              {number(cost.unpriced_requests)} {label('unknown')}
            </span>
          )}
          <span className="mt-1 block">{label('runCostScope')}</span>
          {cost?.estimated_requests ? <span className="mt-1 block">{label('referenceNote')}</span> : null}
        </>
      )}
    </span>
  )
}
