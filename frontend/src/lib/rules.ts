import type { RuleInput, RuleIn } from '../api/contracts'

/** The rule forms still speak Spanish until the definition screens move to the English codes. */
export function toRuleIn(body: RuleInput): RuleIn {
  return {
    text: body.texto,
    type: body.tipo === 'requisito' ? 'requirement' : 'prohibition',
    decision: body.decision,
  }
}
