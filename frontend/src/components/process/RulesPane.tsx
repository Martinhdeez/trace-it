import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { BookOpenText, Hammer, Plus } from 'lucide-react'
import { api } from '../../api/client'
import type { Rule, RuleStatus as RuleStatusCode } from '../../api/contracts'
import { ErrorNotice, EmptyState } from '../shell/Notice'
import { t } from '../../i18n'
import { cn } from '../../lib/cn'
import { paths } from '../../lib/paths'
import { ruleLabel } from '../../lib/process'

const RULE_STATUS: Record<
  RuleStatusCode,
  { dot: string; ink: string; soft: string; pill: string; ring: string }
> = {
  active: {
    dot: 'bg-pagar',
    ink: 'text-pagar',
    soft: 'bg-pagar-soft',
    pill: 'group-hover:bg-pagar-soft [@media(hover:none)]:bg-pagar-soft',
    ring: 'border-pagar/20 border-t-pagar',
  },
  compiling: {
    dot: 'bg-ocr',
    ink: 'text-ocr',
    soft: 'bg-ocr-soft',
    pill: 'group-hover:bg-ocr-soft [@media(hover:none)]:bg-ocr-soft',
    ring: 'border-ocr/20 border-t-ocr',
  },
  draft: {
    dot: 'bg-faint',
    ink: 'text-muted',
    soft: 'bg-well',
    pill: 'group-hover:bg-well [@media(hover:none)]:bg-well',
    ring: 'border-faint/25 border-t-faint',
  },
  blocked: {
    dot: 'bg-escalar',
    ink: 'text-escalar',
    soft: 'bg-escalar-soft',
    pill: 'group-hover:bg-escalar-soft [@media(hover:none)]:bg-escalar-soft',
    ring: 'border-escalar/20 border-t-escalar',
  },
  retired: {
    dot: 'bg-faint/50',
    ink: 'text-faint',
    soft: 'bg-well',
    pill: 'group-hover:bg-well [@media(hover:none)]:bg-well',
    ring: 'border-faint/20 border-t-faint',
  },
}

export function RulesPane({
  processId,
  rules,
  outcomes,
}: {
  processId: number
  rules: Rule[]
  outcomes: string[]
}) {
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [adding, setAdding] = useState(false)
  const [text, setText] = useState('')
  const [pending, setPending] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (adding) input.current?.focus()
  }, [adding])

  const create = useMutation({
    mutationFn: (text: string) =>
      api.createRule(processId, { text, type: 'requirement', decision: outcomes[0] ?? 'ESCALAR' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
      setText('')
      requestAnimationFrame(() => input.current?.focus())
    },
  })

  const compile = useMutation({
    mutationFn: (id: number) => api.compileRule(id),
    onMutate: (id) => {
      setPending((current) => new Set(current).add(id))
    },
    onSettled: (_data, _error, id) => {
      setPending((current) => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
      void queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })

  const submit = () => {
    const value = text.trim()
    if (!value || create.isPending) return
    create.mutate(value)
  }

  return (
    <>
      <p className="mb-2 font-mono text-[11px] tracking-[0.12em] text-faint">
        NORMA · {rules.length}
      </p>
      {rules.length === 0 ? (
        <EmptyState icon={BookOpenText} title="Aún no hay normas" className="py-8">
          Pídelas en el chat del proceso, o añade una a mano aquí abajo.
        </EmptyState>
      ) : null}
      <ul className="divide-y divide-hairline">
        {rules.map((rule) => {
          const status = rule.status as RuleStatusCode
          const working = pending.has(rule.id) || status === 'compiling'
          const canCompile = !working && (status === 'draft' || status === 'blocked')
          return (
            <li key={rule.id} className="group flex h-9 items-center gap-2">
              <Link
                to={paths.rule(processId, rule.id)}
                title={rule.text}
                className="min-w-0 flex-1 truncate text-[13px] leading-5 text-ink hover:text-ink"
              >
                {ruleLabel(rule)}
              </Link>
              <RuleStatus
                status={status}
                working={working}
                action={canCompile ? 'Compilar' : undefined}
                onAction={canCompile ? () => compile.mutate(rule.id) : undefined}
              />
            </li>
          )
        })}
      </ul>

      {adding ? (
        <div className="flex items-center gap-2 py-2">
          <Plus size={12} strokeWidth={2} className="shrink-0 text-faint" />
          <input
            ref={input}
            value={text}
            disabled={create.isPending}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                submit()
              }
              if (event.key === 'Escape') {
                setAdding(false)
                setText('')
              }
            }}
            onBlur={() => {
              if (!text.trim() && !create.isPending) setAdding(false)
            }}
            placeholder="Una frase. Enter guarda, Esc cancela."
            className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-faint disabled:opacity-60"
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="mt-1 flex w-full items-center gap-2 py-2 text-left text-[13px] text-muted hover:text-ink"
        >
          <Plus size={12} strokeWidth={2} />
          Añadir regla
        </button>
      )}

      {create.isError ? (
        <div className="mt-3">
          <ErrorNotice error={create.error} />
        </div>
      ) : null}
      {compile.isError ? (
        <div className="mt-3">
          <ErrorNotice error={compile.error} />
        </div>
      ) : null}
    </>
  )
}

function RuleStatus({
  status,
  working,
  action,
  onAction,
}: {
  status: RuleStatusCode
  working: boolean
  action?: string
  onAction?: () => void
}) {
  const [seconds, setSeconds] = useState(0)
  const tone = RULE_STATUS[status] ?? RULE_STATUS.draft
  const label = working ? `${seconds}s` : t(`ruleStatus.${status}`)

  useEffect(() => {
    if (!working) {
      setSeconds(0)
      return
    }
    const id = window.setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => window.clearInterval(id)
  }, [working])

  return (
    <div
      className={cn(
        'inline-flex h-5 max-w-2 shrink-0 items-center overflow-hidden rounded-full',
        'transition-[max-width,padding,gap,background-color] duration-150 ease-out',
        'group-hover:max-w-[12rem] group-hover:gap-1 group-hover:px-1',
        '[@media(hover:none)]:max-w-[12rem] [@media(hover:none)]:gap-1 [@media(hover:none)]:px-1',
        working && 'max-w-[12rem] gap-1 px-1',
        tone.pill,
        working && tone.soft,
      )}
    >
      <span className="relative h-2 w-2 shrink-0">
        {working ? (
          <>
            <span className={cn('absolute inset-[2px] rounded-full', tone.dot)} />
            <span
              aria-hidden
              className={cn(
                'absolute inset-0 rounded-full border-[1.5px] animate-spin motion-reduce:animate-none',
                tone.ring,
              )}
            />
          </>
        ) : (
          <span className={cn('absolute inset-0 rounded-full', tone.dot)} />
        )}
      </span>
      <span
        className={cn(
          'whitespace-nowrap text-[11px] leading-none tabular-nums',
          'opacity-0 transition-opacity duration-150 ease-out',
          'group-hover:opacity-100 [@media(hover:none)]:opacity-100',
          working && 'opacity-100',
          tone.ink,
        )}
      >
        {label}
      </span>
      {action && onAction && !working ? (
        <button
          type="button"
          title={action}
          onClick={onAction}
          className={cn(
            'grid h-4 w-4 shrink-0 place-items-center text-faint',
            'opacity-0 transition-opacity duration-150 ease-out',
            'group-hover:opacity-100 hover:text-ink',
            '[@media(hover:none)]:opacity-100',
          )}
        >
          <Hammer size={11} strokeWidth={1.7} />
        </button>
      ) : null}
    </div>
  )
}

