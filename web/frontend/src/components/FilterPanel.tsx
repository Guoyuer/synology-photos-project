import { useMemo } from 'react'
import type { Camera, CollectRequest, Concept, Location, Person } from '../types'
import { MultiSelect } from './MultiSelect'
import { DEFAULT_FILTERS, type FilterState } from '../hooks/useUrlFilters'

interface Props {
  persons: Person[]
  locations: Location[]
  concepts: Concept[]
  cameras: Camera[]
  filters: FilterState
  onFiltersChange: (f: FilterState) => void
  onSearch: (req: CollectRequest) => void
  loading: boolean
}

const ITEM_TYPES = [
  { value: 0, label: 'Photo' },
  { value: 1, label: 'Video' },
  { value: 3, label: 'Live Photo' },
  { value: 6, label: 'Motion Photo' },
]

export function FilterPanel({ persons, locations, concepts, cameras, filters, onFiltersChange, onSearch, loading }: Props) {
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

  const submit = () => {
    onSearch({
      person_ids: filters.personIds,
      all_persons: filters.allPersons,
      country: filters.country || null,
      first_level: filters.firstLevel || null,
      district: filters.district || null,
      from_date: filters.fromDate || null,
      to_date: filters.toDate || null,
      item_types: filters.itemTypes,
      concepts: filters.selectedConcepts,
      min_confidence: filters.minConfidence,
      cameras: filters.selectedCameras,
      min_duration: filters.minDuration ? parseInt(filters.minDuration) : null,
      min_width: filters.minWidth ? parseInt(filters.minWidth) : null,
      max_duration: filters.maxDuration ? parseInt(filters.maxDuration) : null,
      min_fps: filters.minFps ? parseInt(filters.minFps) : null,
      video_codecs: filters.videoCodecs,
      has_audio: filters.hasAudio === 'yes' ? true : filters.hasAudio === 'no' ? false : null,
      has_gps: filters.hasGps === 'yes' ? true : filters.hasGps === 'no' ? false : null,
      limit: filters.limit ? parseInt(filters.limit) : null,
      sort_desc: filters.sortDesc,
    })
  }

  return (
    <div className="bg-gray-900 border-r border-gray-700 w-96 p-4 flex flex-col gap-4 overflow-y-auto">
      <h1 className="text-lg font-bold text-white">📸 Photo Collect</h1>

      {/* Persons */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Persons</label>
        <MultiSelect
          options={persons.map(p => ({ value: p.id, label: p.name, sub: `${p.item_count}` }))}
          selected={filters.personIds}
          onChange={v => set('personIds', v as number[])}
          placeholder="Any person..."
        />
        {filters.personIds.length > 1 && (
          <label className="flex items-center gap-2 mt-2 text-xs text-gray-400 cursor-pointer">
            <input type="checkbox" checked={filters.allPersons} onChange={e => set('allPersons', e.target.checked)} className="accent-blue-500" />
            All must co-appear (intersection)
          </label>
        )}
      </section>

      {/* Location */}
      <section>
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
        <button onClick={submit} disabled={loading}
          className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white font-semibold rounded text-sm transition-colors">
          {loading ? 'Searching...' : 'Search'}
        </button>
        <button onClick={() => onFiltersChange(DEFAULT_FILTERS)}
          className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-sm transition-colors">
          Reset
        </button>
      </div>
    </div>
  )
}
