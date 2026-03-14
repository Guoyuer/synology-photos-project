/**
 * TimelineBar — vertical histogram on the right side of the grid.
 *
 * Displays photo density over time as horizontal bars (newest at top,
 * bar width = count). Supports drill-down: clicking a year/quarter
 * zooms into months; clicking a month sets the date filter.
 */
import { useMemo, useCallback, useState } from 'react'
import type { MediaItem } from '../types'
import { computeBins, type Bin, type Granularity } from './timelineBins'

interface DrillLevel {
  gran: Granularity
  filterRange: { from: string; to: string }
  label: string // e.g. "2023" or "2023 Q2"
}

interface Props {
  items: MediaItem[]
  onDateFilter: (from: string, to: string) => void
  onScrollTo: (itemIndex: number) => void
}

export function TimelineBar({ items, onDateFilter, onScrollTo }: Props) {
  const [drillStack, setDrillStack] = useState<DrillLevel[]>([])
  // Forced top-level granularity when user navigates "back" from auto-detected level
  const [topGran, setTopGran] = useState<Granularity | null>(null)

  const currentDrill = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null

  const { bins, maxCount, gran } = useMemo(() => {
    if (currentDrill) {
      return computeBins(items, currentDrill.gran, currentDrill.filterRange)
    }
    return computeBins(items, topGran ?? undefined)
  }, [items, currentDrill, topGran])

  const handleClick = useCallback((bin: Bin) => {
    if (gran === 'year') {
      setDrillStack(prev => [...prev, {
        gran: 'quarter',
        filterRange: { from: bin.fromDate, to: bin.toDate },
        label: bin.label,
      }])
    } else if (gran === 'quarter') {
      setDrillStack(prev => [...prev, {
        gran: 'month',
        filterRange: { from: bin.fromDate, to: bin.toDate },
        label: bin.label,
      }])
    } else {
      // Month level — set date filter and scroll
      onDateFilter(bin.fromDate, bin.toDate)
      onScrollTo(bin._firstIndex)
    }
  }, [gran, onDateFilter, onScrollTo])

  const handleBack = useCallback(() => {
    if (drillStack.length > 0) {
      setDrillStack(prev => prev.slice(0, -1))
    } else {
      // At top level — zoom out to coarser granularity
      if (gran === 'month') setTopGran('quarter')
      else if (gran === 'quarter') { setTopGran(null) } // 'year' is default
    }
  }, [drillStack, gran])

  const canGoBack = drillStack.length > 0 || gran !== 'year'

  if (!bins.length && !canGoBack) return null

  const binH = bins.length > 0 ? Math.max(4, Math.min(32, Math.floor(600 / bins.length))) : 0

  return (
    <div className="w-12 shrink-0 flex flex-col overflow-y-auto bg-gray-900 border-l border-gray-800 select-none"
      style={{ scrollbarWidth: 'none' }}>

      {/* Back/up button — shown at every non-year level */}
      {canGoBack && (
        <button
          onClick={handleBack}
          title="Back"
          className="shrink-0 flex items-center justify-center h-6 text-[9px] text-blue-400 hover:text-blue-300 hover:bg-gray-800 border-b border-gray-800 transition-colors gap-0.5"
        >
          <span>{'< Back'}</span>
        </button>
      )}

      {bins.map(bin => {
        const pct = bin.count / maxCount
        const opacity = 0.25 + pct * 0.75
        return (
          <div
            key={bin.fromDate}
            title={`${bin.label}: ${bin.count} photos`}
            onClick={() => handleClick(bin)}
            className="relative flex items-center cursor-pointer hover:bg-gray-800 group shrink-0"
            style={{ height: binH }}
          >
            <div
              className="absolute left-0 top-0.5 bottom-0.5 bg-blue-500 rounded-r transition-all"
              style={{ width: `${pct * 100}%`, opacity }}
            />
            {binH >= 14 && (
              <span className="relative z-10 text-[9px] text-gray-400 group-hover:text-gray-200 pl-0.5 truncate leading-none">
                {bin.label}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}
