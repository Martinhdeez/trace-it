import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

export type Column<T> = {
  key: string
  header: string
  width?: string
  render: (row: T) => ReactNode
}

export function DataTable<T extends { id: string }>({
  columns,
  rows,
  onRowClick,
  selectedId,
  framed = true,
}: {
  columns: Column<T>[]
  rows: T[]
  onRowClick?: (row: T) => void
  selectedId?: string
  framed?: boolean
}) {
  const table = (
    <table className="w-full border-collapse text-left">
      <thead>
        <tr className="border-b border-hairline text-[11px] font-medium tracking-[0.04em] text-muted">
          {columns.map((column) => (
            <th
              key={column.key}
              className="px-3.5 py-2.5 font-medium"
              style={column.width ? { width: column.width } : undefined}
            >
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.id}
            tabIndex={onRowClick ? 0 : undefined}
            onClick={() => onRowClick?.(row)}
            onKeyDown={(event) => {
              if (!onRowClick) return
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onRowClick(row)
              }
            }}
            className={cn(
              'border-b border-hairline last:border-0',
              onRowClick && 'cursor-pointer hover:bg-canvas focus-visible:bg-canvas',
              selectedId === row.id && 'bg-canvas',
            )}
          >
            {columns.map((column) => (
              <td key={column.key} className="px-3.5 py-[9px] align-middle">
                {column.render(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )

  if (!framed) return table

  return <div className="overflow-hidden rounded-[16px] ring-1 ring-black/[0.06]">{table}</div>
}
