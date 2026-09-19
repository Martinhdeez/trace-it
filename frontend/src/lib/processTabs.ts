import { paths } from './paths'

export const PROCESS_TABS = [
  { id: 'panel', label: 'Panel', path: paths.panel },
  { id: 'definition', label: 'Definición', path: paths.definition },
  { id: 'runs', label: 'Ejecuciones', path: paths.instances },
  { id: 'review', label: 'Revisión', path: paths.review },
  { id: 'settings', label: 'Ajustes', path: paths.processSettings },
] as const

export type ProcessTabId = (typeof PROCESS_TABS)[number]['id']

export function processTabFromPath(pathname: string, processId: number): ProcessTabId {
  const base = `/processes/${processId}`
  if (
    pathname.startsWith(`${base}/definition`) ||
    pathname.startsWith(`${base}/rules`) ||
    pathname.startsWith(`${base}/versions`) ||
    pathname.startsWith(`${base}/knowledge`)
  ) {
    return 'definition'
  }
  if (pathname.startsWith(`${base}/instances`)) return 'runs'
  if (pathname.startsWith(`${base}/review`)) return 'review'
  if (pathname.startsWith(`${base}/settings`)) return 'settings'
  return 'panel'
}
