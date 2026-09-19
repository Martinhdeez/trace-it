import { en } from './en'
import { es } from './es'

/** Same keys as `es`, any string as a value. */
type Catalog<T> = { readonly [K in keyof T]: T[K] extends string ? string : Catalog<T[K]> }

export type Messages = Catalog<typeof es>
export type Locale = 'es' | 'en'

const STORAGE_KEY = 'trace.idioma'
const catalogs: Record<Locale, Messages> = { es, en }

function stored(): Locale {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'es'
  } catch {
    return 'es'
  }
}

let locale: Locale = stored()
document.documentElement.lang = locale

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

export function getLocale(): Locale {
  return locale
}

/** Kept in this browser. The caller re-renders the tree so every `t()` reads it. */
export function setLocale(next: Locale) {
  locale = next
  document.documentElement.lang = next
  try {
    if (next === 'es') window.localStorage.removeItem(STORAGE_KEY)
    else window.localStorage.setItem(STORAGE_KEY, next)
  } catch {
    /* private mode */
  }
}
