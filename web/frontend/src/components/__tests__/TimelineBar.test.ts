/**
 * Unit tests for TimelineBar binning logic.
 *
 * Tests the pure functions extracted from TimelineBar to verify:
 * - Granularity auto-scaling by date span
 * - Bin key computation from ISO date strings
 * - Bin range/label generation
 * - Reverse-chronological ordering (newest first)
 * - Drill-down sub-binning with forceGranularity and filterRange
 * - No NaN or invalid labels
 */

import { describe, it, expect } from 'vitest'
import { granularity, binKey, binRange, computeBins } from '../timelineBins'

describe('granularity', () => {
  it('returns year for >3 year span', () => {
    expect(granularity(365 * 5)).toBe('year')
  })
  it('returns quarter for 90d–3yr span', () => {
    expect(granularity(200)).toBe('quarter')
    expect(granularity(365 * 2)).toBe('quarter')
  })
  it('returns month for <90d span', () => {
    expect(granularity(60)).toBe('month')
  })
})

describe('binKey', () => {
  it('extracts year key from ISO string', () => {
    expect(binKey('2023-07-15T10:30:00', 'year')).toBe('2023')
  })
  it('extracts quarter key', () => {
    expect(binKey('2023-01-15T10:30:00', 'quarter')).toBe('2023-Q1')
    expect(binKey('2023-04-01T00:00:00', 'quarter')).toBe('2023-Q2')
    expect(binKey('2023-07-20T12:00:00', 'quarter')).toBe('2023-Q3')
    expect(binKey('2023-10-31T23:59:59', 'quarter')).toBe('2023-Q4')
  })
  it('extracts month key', () => {
    expect(binKey('2023-03-15T10:30:00', 'month')).toBe('2023-03')
    expect(binKey('2023-12-01T00:00:00', 'month')).toBe('2023-12')
  })
  it('never returns NaN for valid ISO strings', () => {
    const isoStrings = [
      '2026-03-03T15:30:00',
      '2002-12-08T00:00:00',
      '2023-01-01T12:00:00',
    ]
    for (const iso of isoStrings) {
      for (const gran of ['year', 'quarter', 'month'] as const) {
        const key = binKey(iso, gran)
        expect(key).not.toContain('NaN')
        expect(key).not.toContain('undefined')
      }
    }
  })
})

describe('binRange', () => {
  it('returns correct year range', () => {
    const r = binRange('2023', 'year')
    expect(r.from).toBe('2023-01-01')
    expect(r.to).toBe('2023-12-31')
    expect(r.label).toBe('2023')
  })
  it('returns correct quarter range', () => {
    const r = binRange('2023-Q2', 'quarter')
    expect(r.from).toBe('2023-04-01')
    expect(r.to).toBe('2023-06-30')
    expect(r.label).toContain('Q2')
  })
  it('returns correct month range', () => {
    const r = binRange('2023-03', 'month')
    expect(r.from).toBe('2023-03-01')
    expect(r.to).toBe('2023-03-31')
    expect(r.label).toBe('Mar 23')
  })
  it('handles February correctly', () => {
    const r = binRange('2024-02', 'month') // leap year
    expect(r.to).toBe('2024-02-29')
  })
  it('never produces NaN labels', () => {
    expect(binRange('2023', 'year').label).not.toContain('NaN')
    expect(binRange('2023-Q1', 'quarter').label).not.toContain('NaN')
    expect(binRange('2023-01', 'month').label).not.toContain('NaN')
  })
})

describe('computeBins', () => {
  const makeItem = (takentime: number, taken_iso: string) => ({
    id: takentime, filename: '', takentime, taken_iso,
    item_type: 0, type_name: 'photo', filesize: 0, cache_key: '',
    width: null, height: null, duration: null, vres_x: null,
    country: null, first_level: null, district: null,
  })

  it('groups items into yearly bins for large span (newest first)', () => {
    const items = [
      makeItem(1577836800, '2020-01-01T00:00:00'),  // 2020-01-01
      makeItem(1590969600, '2020-06-01T00:00:00'),  // 2020-06-01
      makeItem(1704067200, '2024-01-01T00:00:00'),  // 2024-01-01  (>3yr span -> yearly)
    ]
    const { bins, maxCount, gran } = computeBins(items)
    expect(gran).toBe('year')
    expect(bins.length).toBeGreaterThanOrEqual(2)
    // Newest first
    expect(bins[0].label).toBe('2024')
    expect(bins[0].count).toBe(1)
    expect(bins.at(-1)!.label).toBe('2020')
    expect(bins.at(-1)!.count).toBe(2)
    expect(maxCount).toBe(2)
  })

  it('produces no NaN labels with real ISO strings', () => {
    const items = [
      makeItem(1709424000, '2026-03-03T15:30:00'),
      makeItem(1709337600, '2026-03-01T10:00:00'),
      makeItem(1672531200, '2023-01-01T00:00:00'),
    ]
    const { bins } = computeBins(items)
    for (const bin of bins) {
      expect(bin.label).not.toContain('NaN')
      expect(bin.fromDate).not.toContain('NaN')
      expect(bin.toDate).not.toContain('NaN')
    }
  })

  it('returns empty for no items', () => {
    const { bins } = computeBins([])
    expect(bins).toEqual([])
  })

  it('handles single item', () => {
    const items = [makeItem(1672531200, '2023-01-01T00:00:00')]
    const { bins } = computeBins(items)
    expect(bins.length).toBe(1)
    expect(bins[0].count).toBe(1)
  })

  it('stores firstIndex for each bin', () => {
    const items = [
      makeItem(1577836800, '2020-01-01T00:00:00'),  // 2020
      makeItem(1704067200, '2024-01-01T00:00:00'),  // 2024  (>3yr -> yearly)
      makeItem(1704153600, '2024-01-02T00:00:00'),  // 2024
    ]
    const { bins } = computeBins(items)
    // Newest first: 2024 is first bin, 2020 is last
    expect(bins[0]._firstIndex).toBe(1) // first 2024 item
    expect(bins.at(-1)!._firstIndex).toBe(0) // first 2020 item
  })

  it('returns bins in reverse-chronological order (newest first)', () => {
    const items = [
      makeItem(1577836800, '2020-01-01T00:00:00'),
      makeItem(1640995200, '2022-01-01T00:00:00'),
      makeItem(1704067200, '2024-01-01T00:00:00'),
    ]
    const { bins } = computeBins(items)
    expect(bins[0].label).toBe('2024')
    expect(bins[1].label).toBe('2022')
    expect(bins[2].label).toBe('2020')
  })

  describe('drill-down with forceGranularity and filterRange', () => {
    const items = [
      makeItem(1577836800, '2020-01-15T00:00:00'),  // Jan 2020
      makeItem(1583020800, '2020-03-01T00:00:00'),  // Mar 2020
      makeItem(1590969600, '2020-06-01T00:00:00'),  // Jun 2020
      makeItem(1704067200, '2024-01-01T00:00:00'),  // Jan 2024
      makeItem(1709251200, '2024-03-01T00:00:00'),  // Mar 2024
    ]

    it('drills into monthly bins for a specific year', () => {
      const { bins, gran } = computeBins(items, 'month', { from: '2020-01-01', to: '2020-12-31' })
      expect(gran).toBe('month')
      // Should only contain months from 2020
      expect(bins.every(b => b.fromDate.startsWith('2020'))).toBe(true)
      // Newest month first
      expect(bins[0].label).toBe('Jun 20')
      expect(bins.at(-1)!.label).toBe('Jan 20')
    })

    it('drills into monthly bins for a specific quarter', () => {
      const { bins, gran } = computeBins(items, 'month', { from: '2020-01-01', to: '2020-03-31' })
      expect(gran).toBe('month')
      // Should contain Jan and Mar 2020
      expect(bins.length).toBe(2)
      expect(bins[0].label).toBe('Mar 20')
      expect(bins[1].label).toBe('Jan 20')
    })

    it('returns empty bins when no items match filter range', () => {
      const { bins } = computeBins(items, 'month', { from: '2021-01-01', to: '2021-12-31' })
      expect(bins).toEqual([])
    })

    it('preserves original item indices for scrollTo', () => {
      const { bins } = computeBins(items, 'month', { from: '2024-01-01', to: '2024-12-31' })
      // Jan 2024 is at index 3 in original array
      const janBin = bins.find(b => b.label === 'Jan 24')
      expect(janBin).toBeDefined()
      expect(janBin!._firstIndex).toBe(3)
    })
  })
})
