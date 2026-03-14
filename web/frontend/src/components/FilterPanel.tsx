import { useMemo } from 'react'
import type { Camera, Concept, Location, Person } from '../types'
import { MultiSelect } from './MultiSelect'
import { DEFAULT_FILTERS, type FilterState } from '../hooks/useUrlFilters'

interface Props {
  persons: Person[]
  locations: Location[]
  concepts: Concept[]
  cameras: Camera[]
  filters: FilterState
  onFiltersChange: (f: FilterState) => void
}

const ITEM_TYPES = [
  { value: 0, label: 'Photo' },
  { value: 1, label: 'Video' },
  { value: 3, label: 'Live Photo' },
  { value: 6, label: 'Motion Photo' },
]

export function FilterPanel({ persons, locations, concepts, cameras, filters, onFiltersChange }: Props) {
  const set = <K extends keyof FilterState>(key: K, value: FilterState[K]) =>
    onFiltersChange({ ...filters, [key]: value })

  const countries = useMemo(() =>
    [...new Set(locations.map(l => l.country))].sort(), [locations])

  const firstLevels = useMemo(() =>
    [...new Set(
      locations.filter(l => l.country === filters.country && l.first_level).map(l => l.first_level)
    )].sort(), [locations, filters.country])

  const districts = useMemo(() =>
    [...new Set(
      locations
        .filter(l => l.country === filters.country && (!filters.firstLevel || l.first_level === filters.firstLevel) && l.second_level)
        .map(l => l.second_level)
    )].filter(Boolean).sort(), [locations, filters.country, filters.firstLevel])

  return (
    <div className="bg-gray-900 border-r border-gray-700 w-96 p-4 flex flex-col gap-4 overflow-y-auto">
      <h1 className="text-lg font-bold text-white">📸 Photo Collect</h1>

      {/* Persons */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Persons</label>
        {(() => {
          const GROUP_RE = /^(>=|=)(\d+)$/
          const gm = filters.personCount ? GROUP_RE.exec(filters.personCount) : null
          const isGroup = !!gm
          const groupOp = gm ? gm[1] : '>='
          const groupN = gm ? parseInt(gm[2]) : 2
          const setGroup = (op: string, n: number) =>
            onFiltersChange({ ...filters, personCount: `${op}${n}` })
          const isNone = filters.personCount === 'none'
          const isSolo = filters.personCount === '1'

          return (
            <>
              <div className="flex gap-1.5 mb-2">
                {/* No face pill */}
                {(['none', '1'] as const).map(v => {
                  const active = filters.personCount === v
                  return (
                    <button key={v} type="button"
                      onClick={() => onFiltersChange({
                        ...filters,
                        personCount: active ? '' : v,
                        personIds: v === 'none' ? [] : v === '1' ? filters.personIds.slice(0, 1) : filters.personIds,
                      })}
                      className={`flex-1 py-1 rounded text-xs font-medium transition-colors
                        ${active ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'}`}
                    >
                      {v === 'none' ? 'No face' : 'Solo'}
                    </button>
                  )
                })}

                {/* Group widget */}
                <div
                  onClick={() => !isGroup && setGroup(groupOp, groupN)}
                  className={`flex-1 flex items-center justify-center gap-1 py-1 px-2 rounded text-xs font-medium cursor-pointer transition-colors
                    ${isGroup ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200'}`}
                >
                  <select
                    value={groupOp}
                    onChange={e => { e.stopPropagation(); setGroup(e.target.value, groupN) }}
                    onClick={e => e.stopPropagation()}
                    className="bg-transparent outline-none cursor-pointer"
                  >
                    <option value=">=">≥</option>
                    <option value="=">=</option>
                  </select>
                  <input
                    type="number" min={2} value={groupN}
                    onChange={e => setGroup(groupOp, Math.max(2, parseInt(e.target.value) || 2))}
                    onClick={e => e.stopPropagation()}
                    className="w-7 bg-transparent text-center outline-none"
                  />
                  <span>ppl</span>
                </div>
              </div>

              <MultiSelect
                options={persons.map(p => ({ value: p.id, label: p.name, sub: `${p.item_count}` }))}
                selected={filters.personIds}
                onChange={v => {
                  const ids = v as number[]
                  const next = isSolo ? ids.slice(-1) : ids
                  onFiltersChange({ ...filters, personIds: next })
                }}
                placeholder="Any named person..."
                disabled={isNone}
              />
            </>
          )
        })()}
      </section>

      {/* Has GPS */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">GPS</label>
        <select value={filters.hasGps} onChange={e => set('hasGps', e.target.value)}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200">
          <option value="">Any</option>
          <option value="yes">With GPS</option>
          <option value="no">Without GPS</option>
        </select>
      </section>

      {/* Location — only shown when GPS is not excluded */}
      {filters.hasGps !== 'no' && <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Country</label>
        <select
          value={filters.country}
          onChange={e => onFiltersChange({ ...filters, country: e.target.value, firstLevel: '', district: '' })}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200"
        >
          <option value="">Any location</option>
          {countries.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        {filters.country && firstLevels.length > 0 && (
          <>
            <label className="block text-xs font-semibold text-gray-400 uppercase mt-2 mb-1">City / Region</label>
            <select
              value={filters.firstLevel}
              onChange={e => onFiltersChange({ ...filters, firstLevel: e.target.value, district: '' })}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200"
            >
              <option value="">All</option>
              {firstLevels.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </>
        )}
        {filters.country && districts.length > 0 && (
          <>
            <label className="block text-xs font-semibold text-gray-400 uppercase mt-2 mb-1">District</label>
            <select
              value={filters.district}
              onChange={e => set('district', e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200"
            >
              <option value="">All</option>
              {districts.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </>
        )}
      </section>}

      {/* Date range */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Date Range</label>
        <div className="flex gap-2">
          <input type="date" value={filters.fromDate} onChange={e => set('fromDate', e.target.value)}
            className="flex-1 px-2 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
          <input type="date" value={filters.toDate} onChange={e => set('toDate', e.target.value)}
            className="flex-1 px-2 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
        </div>
      </section>

      {/* Media type */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Type</label>
        <div className="flex flex-wrap gap-2">
          {ITEM_TYPES.map(t => (
            <label key={t.value} className="flex items-center gap-1 text-sm text-gray-300 cursor-pointer">
              <input type="checkbox"
                checked={filters.itemTypes.includes(t.value)}
                onChange={() => set('itemTypes',
                  filters.itemTypes.includes(t.value)
                    ? filters.itemTypes.filter(x => x !== t.value)
                    : [...filters.itemTypes, t.value]
                )}
                className="accent-blue-500"
              />
              {t.label}
            </label>
          ))}
        </div>
      </section>

      {/* AI Concepts */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">AI Concepts</label>
        <MultiSelect
          options={concepts.map(c => ({ value: c.stem, label: c.stem, sub: `${c.usage_count}` }))}
          selected={filters.selectedConcepts}
          onChange={v => set('selectedConcepts', v as string[])}
          placeholder="food, beach, cityscape..."
        />
        {filters.selectedConcepts.length > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <label className="text-xs text-gray-400">Min confidence:</label>
            <input type="range" min="0.5" max="1" step="0.05" value={filters.minConfidence}
              onChange={e => set('minConfidence', parseFloat(e.target.value))}
              className="flex-1" />
            <span className="text-xs text-gray-300 w-8">{filters.minConfidence.toFixed(2)}</span>
          </div>
        )}
      </section>

      {/* Camera */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Camera</label>
        <MultiSelect
          options={cameras.map(c => ({ value: c.camera, label: c.camera, sub: `${c.item_count}` }))}
          selected={filters.selectedCameras}
          onChange={v => set('selectedCameras', v as string[])}
          placeholder="Any camera..."
        />
      </section>

      {/* Video filters — only relevant when Video type is selected */}
      {filters.itemTypes.includes(1) && <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Video Filters</label>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-24">Min duration</label>
            <input type="number" value={filters.minDuration} onChange={e => set('minDuration', e.target.value)}
              placeholder="sec" className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-24">Min width</label>
            <select value={filters.minWidth} onChange={e => set('minWidth', e.target.value)}
              className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200">
              <option value="">Any</option>
              <option value="1920">1080p (1920)</option>
              <option value="2560">1440p (2560)</option>
              <option value="3840">4K (3840)</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-24">Max duration</label>
            <input type="number" value={filters.maxDuration} onChange={e => set('maxDuration', e.target.value)}
              placeholder="sec" className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-24">Min FPS</label>
            <select value={filters.minFps} onChange={e => set('minFps', e.target.value)}
              className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200">
              <option value="">Any</option>
              <option value="30">30fps+</option>
              <option value="60">60fps+</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-400">Codec</label>
            <div className="flex gap-3">
              {(['hevc', 'h264', 'vp9'] as const).map(codec => (
                <label key={codec} className="flex items-center gap-1 text-xs text-gray-300 cursor-pointer">
                  <input type="checkbox"
                    checked={filters.videoCodecs.includes(codec)}
                    onChange={() => set('videoCodecs',
                      filters.videoCodecs.includes(codec)
                        ? filters.videoCodecs.filter(c => c !== codec)
                        : [...filters.videoCodecs, codec]
                    )}
                    className="accent-blue-500"
                  />
                  {codec.toUpperCase().replace('264', '-264')}
                </label>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-24">Audio</label>
            <select value={filters.hasAudio} onChange={e => set('hasAudio', e.target.value)}
              className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200">
              <option value="">Any</option>
              <option value="yes">With audio</option>
              <option value="no">Without audio</option>
            </select>
          </div>
        </div>
      </section>}

      {/* Limit */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Limit results</label>
        <input type="number" value={filters.limit} onChange={e => set('limit', e.target.value)}
          placeholder="No limit"
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
      </section>

      <div className="flex gap-2 mt-2">
        <button onClick={() => onFiltersChange(DEFAULT_FILTERS)}
          className="w-full px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-sm transition-colors">
          Reset filters
        </button>
      </div>
    </div>
  )
}
