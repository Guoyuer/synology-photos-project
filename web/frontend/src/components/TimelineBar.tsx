/**
 * TimelineBar — vertical histogram on the right side of the grid.
 *
 * Displays photo density over time as horizontal bars (time top→bottom,
 * bar width = count). Clicking a bin scrolls the grid to that period
 * and sets the date filter.
 */
import { useMemo, useCallback } from 'react'
import type { MediaItem } from '../types'
import { computeBins, type Bin } from './timelineBins'

interface Props {
  items: MediaItem[]
  onDateFilter: (from: string, to: string) => void
  onScrollTo: (itemIndex: number) => void
}

export function TimelineBar({ items, onDateFilter, onScrollTo }: Props) {
  const { bins, maxCount } = useMemo(() => computeBins(items), [items])

  const handleClick = useCallback((bin: Bin) => {
    onDateFilter(bin.fromDate, bin.toDate)
    onScrollTo(bin._firstIndex)
  }, [onDateFilter, onScrollTo])

  if (!bins.length) return null

  const binH = Math.max(4, Math.min(32, Math.floor(600 / bins.length)))

  return (
    <div className="w-12 shrink-0 flex flex-col overflow-y-auto bg-gray-900 border-l border-gray-800 select-none"
      style={{ scrollbarWidth: 'none' }}>
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
