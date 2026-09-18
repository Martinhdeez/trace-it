import { es } from './es'

export type Messages = typeof es
export type Locale = 'es'

const catalogs: Record<Locale, Messages> = { es }
let locale: Locale = 'es'

type Leaf = string

function lookup(tree: unknown, path: string): Leaf {
  const parts = path.split('.')
  let node: unknown = tree
  for (const part of parts) {
    if (typeof node !== 'object' || node === null || !(part in node)) {
      return path
    }
    node = (node as Record<string, unknown>)[part]
  }
  return typeof node === 'string' ? node : path
}

export function t(path: string): string {
  return lookup(catalogs[locale], path)
}

export function processCopy(id: string): { name: string; description: string; summary: string } {
  return {
    name: t(`processes.${id}.name`),
    description: t(`processes.${id}.description`),
    summary: t(`processes.${id}.summary`),
  }
}

export function getLocale(): Locale {
  return locale
}

export function setLocale(next: Locale) {
  locale = next
}
