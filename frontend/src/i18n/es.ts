/** Keys are English, like the rest of the code. Only the strings are Spanish. */
export const es = {
  brand: 'trace.it',
  nav: {
    filter: 'Filtrar',
    processes: 'Procesos',
    newProcess: 'Nuevo proceso',
    instances: 'Ejecuciones',
    queue: 'Revisión',
    rules: 'Definición',
    audit: 'Definición',
    sources: 'Fuentes de verdad',
    settings: 'Ajustes',
    definition: 'Definición',
    knowledge: 'Fuentes de verdad',
    review: 'Revisión',
    panel: 'Panel',
    runs: 'Ejecuciones',
    signIn: 'Entrar',
    anonymous: 'sin identificar',
  },
  health: {
    ok: 'Bien',
    degraded: 'Degradado',
    down: 'Caído',
  },
  instanceStatus: {
    PENDING: 'Pendiente',
    DECIDED: 'Decidida',
  },
  sourceStatus: {
    ok: 'Al día',
    down: 'Caída',
    none: 'Sin sincronizar',
  },
  queue: {
    review: 'Revisión del revisor',
  },
  escalation: {
    RULE_ERROR: 'Error en la regla',
    RULE_CONFLICT: 'Reglas en conflicto',
    SOURCE_UNAVAILABLE: 'Fuente no disponible',
  },
  ruleType: {
    requirement: 'Requisito',
    prohibition: 'Prohibición',
  },
  reviewStatus: {
    completed: 'Completada',
    failed: 'Fallida',
  },
  roles: {
    manager: 'Responsable',
    operator: 'Operador',
  },
  common: {
    loading: 'Cargando…',
    empty: 'Nada por aquí todavía.',
    cancel: 'Cancelar',
    save: 'Guardar',
    close: 'Cerrar',
    copy: 'Copiar',
    copied: 'Copiado',
    download: 'Descargar',
    retry: 'Reintentar',
  },
} as const
