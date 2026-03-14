export function fmt(bytes: number) {
  if (bytes >= 1024 * 1024 * 1024) return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

export function fmtDur(ms: number | null) {
  if (!ms) return ''
  const s = Math.round(ms / 1000)
  return s >= 60 ? `${Math.floor(s / 60)}m${s % 60}s` : `${s}s`
}

export function fmtFps(fps: number | null): string | null {
  if (fps == null) return null
  const n = fps >= 1000 ? fps / 1000 : fps
  return `${n} fps`
}

export const TYPE_BADGE: Record<string, string> = {
  photo: 'bg-blue-700',
  video: 'bg-red-700',
  live: 'bg-green-700',
  motion: 'bg-purple-700',
}
