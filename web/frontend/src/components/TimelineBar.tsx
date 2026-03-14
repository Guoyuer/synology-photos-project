/**
 * TimelineBar — vertical histogram replacing the scrollbar.
 *
 * Displays photo density over time as horizontal bars (time top→bottom,
 * bar width = count). Clicking a bin scrolls the grid to that period
 * and sets the date filter.
 */
import { useMemo, useRef, useCallback } from 'react'
import type { MediaItem } from '../types'

interface Bin {
  label: string       // display label e.g. "2023" or "Jan 23"
  fromDate: string    // YYYY-MM-DD
  toDate: string      // YYYY-MM-DD
  count: number
}

interface Props {
  items: MediaItem[]
  /** Called when user clicks a bin — sets date filter */
  onDateFilter: (from: string, to: string) => void
  /** Called when user clicks a bin — scrolls grid to first item in bin */
  onScrollTo: (itemIndex: number) => void
}

function granularity(spanDays: number): 'year' | 'quarter' | 'month' {
  if (spanDays > 365 * 3) return 'year'
  if (spanDays > 90)      return 'quarter'
  return 'month'
}

function binKey(date: Date, gran: 'year' | 'quarter' | 'month'): string {
  const y = date.getUTCFullYear()
  const m = date.getUTCMonth() // 0-based
  if (gran === 'year')    return `${y}`
  if (gran === 'quarter') return `${y}-Q${Math.floor(m / 3) + 1}`
  return `${y}-${String(m + 1).padStart(2, '0')}`
}

function binRange(key: string, gran: 'year' | 'quarter' | 'month'): { from: string; to: string; label: string } {
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

export function TimelineBar({ items, onDateFilter, onScrollTo }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  const { bins, maxCount } = useMemo(() => {
    if (!items.length) return { bins: [] as Bin[], maxCount: 1 }

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
    const firstIndex = new Map<string, number>() // first item index in each bin (items sorted oldest first... but may be desc)

    // items may be sorted desc (newest first) — we need to track first occurrence for scroll
    for (let i = 0; i < items.length; i++) {
      const iso = items[i].taken_iso
      if (!iso) continue
      const d = new Date(iso + 'T00:00:00Z')
      const key = binKey(d, gran)
      counts.set(key, (counts.get(key) ?? 0) + 1)
      if (!firstIndex.has(key)) firstIndex.set(key, i)
    }

    // Sort bins chronologically
    const sortedKeys = [...counts.keys()].sort()
    const bins: Bin[] = sortedKeys.map(key => {
      const { from, to, label } = binRange(key, gran)
      return { label, fromDate: from, toDate: to, count: counts.get(key)! }
    })

    // Store first indices on bins (attach as extra prop for click handler)
    ;(bins as any[]).forEach((b, i) => {
      b._firstIndex = firstIndex.get(sortedKeys[i]) ?? 0
    })

    const maxCount = Math.max(...bins.map(b => b.count), 1)
    return { bins, maxCount }
  }, [items])

  const handleClick = useCallback((bin: Bin & { _firstIndex?: number }) => {
    onDateFilter(bin.fromDate, bin.toDate)
    if (bin._firstIndex != null) onScrollTo(bin._firstIndex)
  }, [onDateFilter, onScrollTo])

  if (!bins.length) return null

  // Height per bin: fill container, min 4px, max 32px
  const binH = Math.max(4, Math.min(32, Math.floor(600 / bins.length)))

  return (
    <div
      ref={containerRef}
      className="w-14 shrink-0 flex flex-col overflow-y-auto bg-gray-900 border-l border-gray-800 select-none"
      style={{ scrollbarWidth: 'none' }}
    >
      {bins.map((bin) => {
        const b = bin as Bin & { _firstIndex?: number }
        const pct = b.count / maxCount
        // Color intensity based on density
        const opacity = 0.25 + pct * 0.75
        return (
          <div
            key={b.fromDate}
            title={`${b.label}: ${b.count} photos`}
            onClick={() => handleClick(b)}
            className="relative flex items-center cursor-pointer hover:bg-gray-800 group shrink-0"
            style={{ height: binH }}
          >
            {/* Bar — grows from left */}
            <div
              className="absolute left-0 top-0.5 bottom-0.5 bg-blue-500 rounded-r transition-all"
              style={{ width: `${pct * 100}%`, opacity }}
            />
            {/* Label — shown when bin is tall enough */}
            {binH >= 14 && (
              <span className="relative z-10 text-[9px] text-gray-400 group-hover:text-gray-200 pl-1 truncate leading-none">
                {b.label}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
