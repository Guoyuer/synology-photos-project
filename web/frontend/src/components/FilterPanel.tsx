import { useMemo, useState } from 'react'
import type { Camera, CollectRequest, Concept, Location, Person } from '../types'
import { MultiSelect } from './MultiSelect'

interface Props {
  persons: Person[]
  locations: Location[]
  concepts: Concept[]
  cameras: Camera[]
  onSearch: (req: CollectRequest) => void
  loading: boolean
}

const ITEM_TYPES = [
  { value: 0, label: 'Photo' },
  { value: 1, label: 'Video' },
  { value: 3, label: 'Live Photo' },
  { value: 6, label: 'Motion Photo' },
]

export function FilterPanel({ persons, locations, concepts, cameras, onSearch, loading }: Props) {
  const [personIds, setPersonIds] = useState<number[]>([])
  const [allPersons, setAllPersons] = useState(false)
  const [country, setCountry] = useState('')
  const [district, setDistrict] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const [itemTypes, setItemTypes] = useState<number[]>([])
  const [selectedConcepts, setSelectedConcepts] = useState<string[]>([])
  const [minConfidence, setMinConfidence] = useState(0.7)
  const [selectedCameras, setSelectedCameras] = useState<string[]>([])
  const [minDuration, setMinDuration] = useState('')
  const [minWidth, setMinWidth] = useState('')
  const [limit, setLimit] = useState('')

  const countries = useMemo(() =>
    [...new Set(locations.map(l => l.country))].sort(), [locations])

  const districts = useMemo(() =>
    locations
      .filter(l => l.country === country && l.second_level)
      .map(l => l.second_level)
      .filter(Boolean)
      .sort(), [locations, country])

  const submit = () => {
    onSearch({
      person_ids: personIds,
      all_persons: allPersons,
      country: country || null,
      district: district || null,
      from_date: fromDate || null,
      to_date: toDate || null,
      item_types: itemTypes,
      concepts: selectedConcepts,
      min_confidence: minConfidence,
      cameras: selectedCameras,
      min_duration: minDuration ? parseInt(minDuration) : null,
      min_width: minWidth ? parseInt(minWidth) : null,
      limit: limit ? parseInt(limit) : null,
    })
  }

  const reset = () => {
    setPersonIds([]); setAllPersons(false); setCountry(''); setDistrict('')
    setFromDate(''); setToDate(''); setItemTypes([]); setSelectedConcepts([])
    setMinConfidence(0.7); setSelectedCameras([]); setMinDuration(''); setMinWidth(''); setLimit('')
  }

  return (
    <div className="bg-gray-900 border-r border-gray-700 w-72 p-4 flex flex-col gap-4 overflow-y-auto">
      {/* Persons */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Persons</label>
        <MultiSelect
          options={persons.map(p => ({ value: p.id, label: p.name, sub: `${p.item_count}` }))}
          selected={personIds}
          onChange={v => setPersonIds(v as number[])}
          placeholder="Any person..."
        />
        {personIds.length > 1 && (
          <label className="flex items-center gap-2 mt-2 text-xs text-gray-400 cursor-pointer">
            <input type="checkbox" checked={allPersons} onChange={e => setAllPersons(e.target.checked)} className="accent-blue-500" />
            All must co-appear (intersection)
          </label>
        )}
      </section>

      {/* Location */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Country</label>
        <select
          value={country}
          onChange={e => { setCountry(e.target.value); setDistrict('') }}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200"
        >
          <option value="">Any location</option>
          {countries.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        {country && districts.length > 0 && (
          <>
            <label className="block text-xs font-semibold text-gray-400 uppercase mt-2 mb-1">District</label>
            <select
              value={district}
              onChange={e => setDistrict(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200"
            >
              <option value="">All districts</option>
              {districts.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </>
        )}
      </section>

      {/* Date range */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Date Range</label>
        <div className="flex gap-2">
          <input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)}
            className="flex-1 px-2 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
          <input type="date" value={toDate} onChange={e => setToDate(e.target.value)}
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
                checked={itemTypes.includes(t.value)}
                onChange={() => setItemTypes(v => v.includes(t.value) ? v.filter(x => x !== t.value) : [...v, t.value])}
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
          selected={selectedConcepts}
          onChange={v => setSelectedConcepts(v as string[])}
          placeholder="food, beach, cityscape..."
        />
        {selectedConcepts.length > 0 && (
          <div className="mt-2 flex items-center gap-2">
            <label className="text-xs text-gray-400">Min confidence:</label>
            <input type="range" min="0.5" max="1" step="0.05" value={minConfidence}
              onChange={e => setMinConfidence(parseFloat(e.target.value))}
              className="flex-1" />
            <span className="text-xs text-gray-300 w-8">{minConfidence.toFixed(2)}</span>
          </div>
        )}
      </section>

      {/* Camera */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Camera</label>
        <MultiSelect
          options={cameras.map(c => ({ value: c.camera, label: c.camera, sub: `${c.item_count}` }))}
          selected={selectedCameras}
          onChange={v => setSelectedCameras(v as string[])}
          placeholder="Any camera..."
        />
      </section>

      {/* Video filters */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Video Filters</label>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-24">Min duration</label>
            <input type="number" value={minDuration} onChange={e => setMinDuration(e.target.value)}
              placeholder="sec" className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-24">Min width</label>
            <select value={minWidth} onChange={e => setMinWidth(e.target.value)}
              className="flex-1 px-2 py-1 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200">
              <option value="">Any</option>
              <option value="1920">1080p (1920)</option>
              <option value="2560">1440p (2560)</option>
              <option value="3840">4K (3840)</option>
            </select>
          </div>
        </div>
      </section>

      {/* Limit */}
      <section>
        <label className="block text-xs font-semibold text-gray-400 uppercase mb-1">Limit results</label>
        <input type="number" value={limit} onChange={e => setLimit(e.target.value)}
          placeholder="No limit"
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200" />
      </section>

      <div className="flex gap-2 mt-2">
        <button onClick={submit} disabled={loading}
          className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white font-semibold rounded text-sm transition-colors">
          {loading ? 'Searching...' : 'Search'}
        </button>
        <button onClick={reset}
          className="px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded text-sm transition-colors">
          Reset
        </button>
      </div>
    </div>
  )
}
