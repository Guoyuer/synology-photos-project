/**
 * Pure functions for TimelineBar bin computation.
 * Extracted for testability.
 */
import type { MediaItem } from '../types'

export interface Bin {
  label: string       // display label e.g. "2023" or "Jan 23"
  fromDate: string    // YYYY-MM-DD
  toDate: string      // YYYY-MM-DD
  count: number
  _firstIndex: number // index of first item in this bin
}

export function granularity(spanDays: number): 'year' | 'quarter' | 'month' {
  if (spanDays > 365 * 3) return 'year'
  if (spanDays > 90)      return 'quarter'
  return 'month'
}

/** Extract bin key directly from ISO string (no Date parsing needed). */
export function binKey(iso: string, gran: 'year' | 'quarter' | 'month'): string {
  const y = iso.slice(0, 4)
  const m = parseInt(iso.slice(5, 7), 10) // 1-based
  if (gran === 'year')    return y
  if (gran === 'quarter') return `${y}-Q${Math.floor((m - 1) / 3) + 1}`
  return `${y}-${String(m).padStart(2, '0')}`
}

export function binRange(key: string, gran: 'year' | 'quarter' | 'month'): { from: string; to: string; label: string } {
  if (gran === 'year') {
    const y = parseInt(key)
    return { from: `${y}-01-01`, to: `${y}-12-31`, label: `${y}` }
  }
  if (gran === 'quarter') {
    const [y, q] = key.split('-Q').map(Number)
    const startM = (q - 1) * 3 + 1
    const endM = startM + 2
    const endDay = endM === 3 ? 31 : endM === 6 ? 30 : endM === 9 ? 30 : 31
    return {
      from: `${y}-${String(startM).padStart(2, '0')}-01`,
      to:   `${y}-${String(endM).padStart(2, '0')}-${endDay}`,
      label: `${key.replace('-', ' ')}`,
    }
  }
  // month
  const [y, m] = key.split('-').map(Number)
  const lastDay = new Date(Date.UTC(y, m, 0)).getUTCDate()
  const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  return {
    from: `${y}-${String(m).padStart(2, '0')}-01`,
    to:   `${y}-${String(m).padStart(2, '0')}-${lastDay}`,
    label: `${monthNames[m - 1]} ${String(y).slice(2)}`,
  }
}

export function computeBins(items: MediaItem[]): { bins: Bin[]; maxCount: number } {
  if (!items.length) return { bins: [], maxCount: 1 }

  // Find span
  let minTs = Infinity, maxTs = -Infinity
  for (const it of items) {
    if (!it.takentime) continue
    if (it.takentime < minTs) minTs = it.takentime
    if (it.takentime > maxTs) maxTs = it.takentime
  }
  const spanDays = (maxTs - minTs) / 86400
  const gran = granularity(spanDays)

  // Count per bin
  const counts = new Map<string, number>()
  const firstIndex = new Map<string, number>()

  for (let i = 0; i < items.length; i++) {
    const iso = items[i].taken_iso
    if (!iso) continue
    const key = binKey(iso, gran)
    counts.set(key, (counts.get(key) ?? 0) + 1)
    if (!firstIndex.has(key)) firstIndex.set(key, i)
  }

  // Sort bins chronologically
  const sortedKeys = [...counts.keys()].sort()
  const bins: Bin[] = sortedKeys.map((key) => {
    const { from, to, label } = binRange(key, gran)
    return { label, fromDate: from, toDate: to, count: counts.get(key)!, _firstIndex: firstIndex.get(key) ?? 0 }
  })

  const maxCount = Math.max(...bins.map(b => b.count), 1)
  return { bins, maxCount }
}
