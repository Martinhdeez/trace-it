import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { ChevronDown } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../api/client'
import { keys } from '../../api/queries'
import type { Rule } from '../../api/contracts'
import { StatusBadge } from '../shell/StatusBadge'

const ease = [0.23, 1, 0.32, 1] as const

/** The norm as a numbered list: one line each, unfolding into its code. */
export function RuleSteps({ rules }: { rules: Rule[] }) {
  const [openId, setOpenId] = useState<number | null>(null)
  const reduce = useReducedMotion()

  return (
    <ul>
      {rules.map((rule, index) => {
        const open = openId === rule.id
        return (
          <li key={rule.id} className="border-t border-hairline first:border-0">
            <button
              type="button"
              onClick={() => setOpenId(open ? null : rule.id)}
              aria-expanded={open}
              className="flex w-full items-center gap-3 px-3.5 py-2.5 text-left hover:bg-canvas"
            >
              <span className="w-5 shrink-0 font-mono text-[11px] tabular-nums text-faint">
                {String(index + 1).padStart(2, '0')}
              </span>
              <span className="min-w-0 flex-1 text-[13px]">{rule.texto}</span>
              <StatusBadge value={rule.decision} />
              <motion.span
                animate={{ rotate: open ? 180 : 0 }}
                transition={{ duration: reduce ? 0 : 0.18, ease }}
                className="text-faint"
              >
                <ChevronDown size={14} strokeWidth={1.5} />
              </motion.span>
            </button>
            <AnimatePresence initial={false}>
              {open ? (
                <motion.div
                  initial={reduce ? false : { height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
                  transition={{ duration: reduce ? 0.12 : 0.22, ease }}
                  className="overflow-hidden"
                >
                  <Code rule={rule} />
                </motion.div>
              ) : null}
            </AnimatePresence>
          </li>
        )
      })}
    </ul>
  )
}

function Code({ rule }: { rule: Rule }) {
  const detail = useQuery({ queryKey: keys.rule(rule.id), queryFn: () => api.getRule(rule.id) })

  return (
    <div className="space-y-3 px-3.5 pb-3.5 pl-11">
      <p className="text-[12.5px] leading-5 text-muted">
        {rule.tipo === 'requisito'
          ? 'Requisito: salta cuando no se cumple.'
          : 'Prohibición: salta cuando se cumple.'}{' '}
        Al saltar, la instancia va a {rule.decision.replaceAll('_', ' ')}.
      </p>
      <div>
        <p className="mb-1.5 font-mono text-[11px] text-faint">
          codigo_a.py {rule.hash ? `· ${rule.hash.slice(0, 16)}` : ''}
        </p>
        <pre className="overflow-x-auto rounded-[12px] bg-canvas px-3 py-2.5 font-mono text-[12px] leading-5 text-ink">
          {detail.data?.codigo_a ?? (detail.isPending ? 'Cargando…' : 'Sin compilar.')}
        </pre>
      </div>
    </div>
  )
}
