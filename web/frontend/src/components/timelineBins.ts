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

export type Granularity = 'year' | 'quarter' | 'month'

export function granularity(spanDays: number): Granularity {
  if (spanDays > 365 * 3) return 'year'
  if (spanDays > 90)      return 'quarter'
  return 'month'
}

/** Extract bin key directly from ISO string (no Date parsing needed). */
export function binKey(iso: string, gran: Granularity): string {
  const y = iso.slice(0, 4)
  const m = parseInt(iso.slice(5, 7), 10) // 1-based
  if (gran === 'year')    return y
  if (gran === 'quarter') return `${y}-Q${Math.floor((m - 1) / 3) + 1}`
  return `${y}-${String(m).padStart(2, '0')}`
}

export function binRange(key: string, gran: Granularity): { from: string; to: string; label: string } {
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

/**
 * Compute bins for items with optional forced granularity and date range filter.
 * When filterRange is given, only items within that range are binned.
 * When forceGranularity is given, that granularity is used instead of auto-detection.
 */
export function computeBins(
  items: MediaItem[],
  forceGranularity?: Granularity,
  filterRange?: { from: string; to: string },
): { bins: Bin[]; maxCount: number; gran: Granularity } {
  // Filter items if a range is specified
  let filtered = items
  if (filterRange) {
    const fromTs = dateToUnix(filterRange.from)
    const toTs = dateToUnix(filterRange.to) + 86400 // include the whole last day
    filtered = items.filter(it => it.takentime && it.takentime >= fromTs && it.takentime < toTs)
  }

  if (!filtered.length) return { bins: [], maxCount: 1, gran: forceGranularity ?? 'month' }

  // Find span
  let minTs = Infinity, maxTs = -Infinity
  for (const it of filtered) {
    if (!it.takentime) continue
    if (it.takentime < minTs) minTs = it.takentime
    if (it.takentime > maxTs) maxTs = it.takentime
  }
  const spanDays = (maxTs - minTs) / 86400
  const gran = forceGranularity ?? granularity(spanDays)

  // Count per bin — use indices from the original items array
  const counts = new Map<string, number>()
  const firstIndex = new Map<string, number>()

  // Build a set of filtered item ids for efficient lookup when filterRange is active
  const filteredIds = filterRange ? new Set(filtered.map(it => it.id)) : null

  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (!item.taken_iso) continue
    if (filteredIds && !filteredIds.has(item.id)) continue
    const key = binKey(item.taken_iso, gran)
    counts.set(key, (counts.get(key) ?? 0) + 1)
    if (!firstIndex.has(key)) firstIndex.set(key, i)
  }

  // Sort bins reverse-chronologically (newest first)
  const sortedKeys = [...counts.keys()].sort().reverse()
  const bins: Bin[] = sortedKeys.map((key) => {
    const { from, to, label } = binRange(key, gran)
    return { label, fromDate: from, toDate: to, count: counts.get(key)!, _firstIndex: firstIndex.get(key) ?? 0 }
  })

  const maxCount = Math.max(...bins.map(b => b.count), 1)
  return { bins, maxCount, gran }
}

/** Convert YYYY-MM-DD to unix timestamp (seconds). */
function dateToUnix(ymd: string): number {
  const [y, m, d] = ymd.split('-').map(Number)
  return Date.UTC(y, m - 1, d) / 1000
}

// ---------------------------------------------------------------------------
// Interaction logic — pure functions for click and back, testable without React
// ---------------------------------------------------------------------------

export interface DrillLevel {
  gran: Granularity
  filterRange: { from: string; to: string }
  label: string
}

export interface ClickResult {
  newDrillStack: DrillLevel[]
  dateFilter: { from: string; to: string }  // always set — every click narrows the filter
  scrollTo: number | null                   // only set at month level
}

/**
 * What happens when the user clicks a bin.
 * Year → drills to quarters (sets date filter to year range).
 * Quarter → drills to months (sets date filter to quarter range).
 * Month → leaf: sets date filter + scrollTo.
 */
export function handleBinClick(gran: Granularity, bin: Bin, drillStack: DrillLevel[]): ClickResult {
  const dateFilter = { from: bin.fromDate, to: bin.toDate }
  if (gran === 'year') {
    return {
      newDrillStack: [...drillStack, { gran: 'quarter', filterRange: dateFilter, label: bin.label }],
      dateFilter,
      scrollTo: null,
    }
  }
  if (gran === 'quarter') {
    return {
      newDrillStack: [...drillStack, { gran: 'month', filterRange: dateFilter, label: bin.label }],
      dateFilter,
      scrollTo: null,
    }
  }
  // month — leaf level
  return { newDrillStack: drillStack, dateFilter, scrollTo: bin._firstIndex }
}

export interface BackResult {
  newDrillStack: DrillLevel[]
  newTopGran: Granularity | null
  dateFilter: { from: string; to: string } | null  // null = clear
}

/**
 * What happens when the user clicks Back.
 * If drilled down: pop one level, expand filter to parent range (or clear if now at root).
 * If at auto top-level: zoom out to coarser granularity and clear filter.
 */
export function handleBinBack(gran: Granularity, drillStack: DrillLevel[], topGran: Granularity | null): BackResult {
  if (drillStack.length > 0) {
    const newStack = drillStack.slice(0, -1)
    if (newStack.length > 0) {
      const parent = newStack[newStack.length - 1]
      return { newDrillStack: newStack, newTopGran: topGran, dateFilter: { from: parent.filterRange.from, to: parent.filterRange.to } }
    }
    return { newDrillStack: newStack, newTopGran: topGran, dateFilter: null }
  }
  // At forced/auto top level — zoom out one notch
  const newTopGran = gran === 'month' ? 'quarter' : null
  return { newDrillStack: [], newTopGran, dateFilter: null }
}
