/** Shapes of the generated lote 1 catalog the mock reads. The backend contract lives in `contracts.ts`. */

export type Decision = 'PAGAR' | 'NO_PAGAR' | 'ESCALAR'

/** States of the generated catalog of lote 1. Kept for `data/*.generated.ts`. */
export type InstanceState =
  | 'RECIBIDA'
  | 'EXTRAIDA'
  | 'VALIDADA'
  | 'CRUZADA'
  | 'DECIDIDA'
  | 'EXPORTADA'
  | 'PENDIENTE_HUMANO'
  | 'REINTENTO'
  | 'OCR'
