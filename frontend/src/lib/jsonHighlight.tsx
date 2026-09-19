import type { ReactNode } from 'react'
import { cn } from './cn'

const PRE = 'overflow-auto bg-[#161615] px-3 py-3 font-mono text-[12px] leading-5 text-[#eceae4]'

export function JsonHighlight({ value, className }: { value: unknown; className?: string }) {
  const raw = JSON.stringify(value, null, 2)
  return <pre className={cn(PRE, className ?? 'max-h-48')}>{tokenize(raw)}</pre>
}

/** Rule code, coloured with the same palette as the JSON beside it. */
export function PythonHighlight({ code, className }: { code: string; className?: string }) {
  return <pre className={cn(PRE, className)}>{tokenizePython(code)}</pre>
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

const KEYWORDS = new Set(
  'def return if elif else for while in not and or is try except finally raise with as import from pass break continue lambda class yield global nonlocal assert del'.split(
    ' ',
  ),
)
const CONSTANTS = new Set(['True', 'False', 'None'])
const BUILTINS = new Set(
  'len str int float bool list dict set tuple any all min max sum sorted range enumerate zip isinstance abs round next iter map filter getattr hasattr print'.split(
    ' ',
  ),
)

// Docstrings, strings, comments, numbers and words; everything else stays plain.
const PYTHON =
  /("""[\s\S]*?"""|'''[\s\S]*?'''|[rbfu]{0,2}"(?:\\.|[^"\\\n])*"|[rbfu]{0,2}'(?:\\.|[^'\\\n])*'|#[^\n]*|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b)/g

function tokenizePython(source: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let last = 0
  let index = 0
  let afterDef = false
  for (const match of source.matchAll(PYTHON)) {
    const start = match.index ?? 0
    const token = match[0]
    let color: string | null = null
    if (token.startsWith('#')) color = 'italic text-[#7d7a73]'
    else if (/^[rbfu]{0,2}["']/.test(token)) color = 'text-[#9fd4a8]'
    else if (/^\d/.test(token)) color = 'text-[#e08b7a]'
    else if (afterDef) color = 'text-[#8cb4ff]'
    else if (KEYWORDS.has(token)) color = 'text-[#c79bf2]'
    else if (CONSTANTS.has(token)) color = 'text-[#e2b56b]'
    else if (BUILTINS.has(token)) color = 'text-[#7fcfd4]'
    afterDef = token === 'def' || token === 'class'
    if (!color) continue
    if (start > last) nodes.push(source.slice(last, start))
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
