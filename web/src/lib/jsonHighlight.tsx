import type { ReactNode } from 'react'

export function JsonHighlight({ value }: { value: unknown }) {
  const raw = JSON.stringify(value, null, 2)
  return (
    <pre className="max-h-48 overflow-auto bg-[#161615] px-3 py-3 font-mono text-[12px] leading-5 text-[#eceae4]">
      {tokenize(raw)}
    </pre>
  )
}

function tokenize(source: string): ReactNode[] {
  const pattern =
    /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(?:\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g
  const nodes: ReactNode[] = []
  let last = 0
  let index = 0
  for (const match of source.matchAll(pattern)) {
    const start = match.index ?? 0
    if (start > last) nodes.push(source.slice(last, start))
    const token = match[0]
    let color = 'text-[#d4d0c8]'
    if (token.startsWith('"')) {
      color = token.endsWith(':') ? 'text-[#8cb4ff]' : 'text-[#9fd4a8]'
    } else if (token === 'true' || token === 'false' || token === 'null') {
      color = 'text-[#e2b56b]'
    } else {
      color = 'text-[#e08b7a]'
    }
    nodes.push(
      <span key={index} className={color}>
        {token}
      </span>,
    )
    index += 1
    last = start + token.length
  }
  if (last < source.length) nodes.push(source.slice(last))
  return nodes
}
