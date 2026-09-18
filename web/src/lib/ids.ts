export function instanceId(fileId: string): string {
  return fileId
    .replace(/\.pdf$/i, '')
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/[^\w]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase()
}
