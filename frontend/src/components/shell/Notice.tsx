import type { ReactNode } from 'react'
import { ApiError } from '../../api/client'
import { cn } from '../../lib/cn'

export function Notice({
  tone = 'neutral',
  title,
  children,
  action,
}: {
  tone?: 'neutral' | 'warning' | 'error'
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-4 rounded-[14px] px-3.5 py-3 ring-1',
        tone === 'error' && 'bg-nopagar-soft ring-nopagar/15',
        tone === 'warning' && 'bg-escalar-soft ring-escalar/15',
        tone === 'neutral' && 'bg-well ring-line',
      )}
    >
      <div className="min-w-0">
        <p
          className={cn(
            'text-[13px] font-medium',
            tone === 'error' && 'text-nopagar',
            tone === 'warning' && 'text-escalar',
          )}
        >
          {title}
        </p>
        {children ? <div className="mt-1 text-[12.5px] text-muted">{children}</div> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

/** Turns a thrown error into something an operator can act on. */
export function ErrorNotice({ error, action }: { error: unknown; action?: ReactNode }) {
  if (!(error instanceof ApiError)) {
    return (
      <Notice tone="error" title="Algo ha fallado" action={action}>
        {error instanceof Error ? error.message : 'Error desconocido'}
      </Notice>
    )
  }
  if (error.unreachable) {
    return (
      <Notice tone="warning" title="El backend no responde" action={action}>
        Arranca la API con <span className="font-mono">make setup</span> (
        <span className="font-mono">:8000</span>) o apunta el proxy a otra con{' '}
        <span className="font-mono">VITE_API_TARGET</span>.
      </Notice>
    )
  }
  if (error.notImplemented) {
    return (
      <Notice tone="warning" title="Endpoint pendiente" action={action}>
        El contrato existe pero nadie lo ha implementado todavía (501). {error.message}
      </Notice>
    )
  }
  return (
    <Notice tone={error.status >= 500 ? 'error' : 'warning'} title={error.message} action={action}>
      <span className="font-mono text-[11px]">
        {error.status} · {error.code}
      </span>
    </Notice>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="px-3.5 py-6 text-[13px] text-muted">{children}</p>
}
