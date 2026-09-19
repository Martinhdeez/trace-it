export function formatEuro(value: number, digits = 2): string {
  return value.toLocaleString('es-ES', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function formatMs(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toLocaleString('es-ES', { minimumFractionDigits: 3, maximumFractionDigits: 3 })} s`
  }
  return `${value} ms`
}

export function formatRunDate(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleString('es-ES', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}
