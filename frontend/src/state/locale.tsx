import { Fragment, createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { getLocale, setLocale as applyLocale, type Locale } from '../i18n'

type LocaleState = {
  locale: Locale
  setLocale: (locale: Locale) => void
}

const Ctx = createContext<LocaleState | null>(null)

/** `t()` reads a module value, so a new language remounts the screens under it. */
export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getLocale)

  const setLocale = useCallback((next: Locale) => {
    applyLocale(next)
    setLocaleState(next)
  }, [])

  const value = useMemo(() => ({ locale, setLocale }), [locale, setLocale])
  return (
    <Ctx.Provider value={value}>
      <Fragment key={locale}>{children}</Fragment>
    </Ctx.Provider>
  )
}

export function useLocale(): LocaleState {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useLocale fuera de LocaleProvider')
  return ctx
}
