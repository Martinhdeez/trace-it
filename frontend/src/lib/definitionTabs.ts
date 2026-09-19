import { paths } from './paths'

export const DEFINITION_TABS = [
  { id: 'normas', label: 'Normas', path: paths.definitionManual },
  { id: 'contexto', label: 'Contexto', path: paths.definitionContext },
  { id: 'inputs', label: 'Inputs', path: paths.definitionInputs },
  { id: 'fuentes', label: 'Fuentes de verdad', path: paths.definitionSources },
] as const

export type DefinitionTabId = (typeof DEFINITION_TABS)[number]['id']

export function definitionTabFromPath(pathname: string): DefinitionTabId {
  if (pathname.includes('/definition/contexto')) return 'contexto'
  if (pathname.includes('/definition/inputs')) return 'inputs'
  if (pathname.includes('/definition/fuentes')) return 'fuentes'
  return 'normas'
}
