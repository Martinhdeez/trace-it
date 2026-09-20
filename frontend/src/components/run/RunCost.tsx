import type { RunOut } from '../../api/contracts'
import { label, money, number } from '../metrics/usage'

export function RunCost({ cost, detail = false }: { cost: RunOut['cost']; detail?: boolean }) {
  const amount = !cost
    ? label('runCostUnavailable')
    : !cost.known_cost_usd && cost.unpriced_requests
      ? label('unknownOnly')
      : `${money(cost.known_cost_usd)}${cost.unpriced_requests ? ` (${label('partial')})` : ''}`
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
        </>
      )}
    </span>
  )
}
