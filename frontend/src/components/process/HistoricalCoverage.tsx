import type { ValidationReport } from '../../api/contracts'
import { Notice } from '../shell/Notice'

export function HistoricalCoverage({ validation }: { validation: ValidationReport }) {
  const coverage = validation.coverage
  if (!coverage) {
    return <Notice tone="warning" title="Historical coverage not reported">
      This validation has no historical coverage counts. Review the full report before publishing.
    </Notice>
  }

  const { evaluated, not_evaluable: notEvaluable, partial, none } = coverage
  const total = coverage.total ?? evaluated + notEvaluable
  const zeroCoverage = total > 0 && evaluated === 0
  const incomplete = notEvaluable > 0
  const title = total === 0
    ? 'No historical decisions to evaluate'
    : zeroCoverage
      ? 'No historical decisions were fully evaluable'
      : incomplete
        ? 'Partial historical coverage'
        : 'Historical cases were evaluable'

  return <Notice tone={total === 0 || incomplete ? 'warning' : 'neutral'} title={title}>
    <p>{evaluated} of {total} historical decisions fully evaluated; {notEvaluable} could not be fully evaluated.</p>
    {notEvaluable > 0 && <>
      <p className="mt-1">{partial} retained some rule results; {none} had no evaluable rule results. Missing newly required symbols prevent a complete assessment of these historical cases.</p>
      {!!validation.not_evaluable?.length && <details className="mt-2">
        <summary>Review cases without full coverage</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5">
          {validation.not_evaluable.map(item => <li key={item.instance_id}>
            {item.name || `Case ${item.instance_id}`}: unavailable evidence for {item.missing_symbols.join(', ') || 'required fields'}
          </li>)}
        </ul>
      </details>}
    </>}
  </Notice>
}
