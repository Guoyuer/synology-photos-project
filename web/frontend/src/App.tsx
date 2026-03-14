import { useEffect, useRef, useState } from 'react'
import { fetchCameras, fetchConcepts, fetchLocations, fetchPersons, runCollect } from './api'
import { FilterPanel } from './components/FilterPanel'
import { ResultsGrid } from './components/ResultsGrid'
import { useUrlFilters, type FilterState } from './hooks/useUrlFilters'
import type { Camera, CollectRequest, CollectResult, Concept, Location, MediaItem, Person } from './types'

function toRequest(f: FilterState): CollectRequest {
  return {
    person_ids: f.personIds,
    person_count: f.personCount || null,
    country: f.country || null,
    first_level: f.firstLevel || null,
    district: f.district || null,
    from_date: f.fromDate || null,
    to_date: f.toDate || null,
    item_types: f.itemTypes,
    concepts: f.selectedConcepts,
    min_confidence: f.minConfidence,
    cameras: f.selectedCameras,
    min_duration: f.minDuration ? parseInt(f.minDuration) : null,
    min_width: f.minWidth ? parseInt(f.minWidth) : null,
    max_duration: f.maxDuration ? parseInt(f.maxDuration) : null,
    min_fps: f.minFps ? parseInt(f.minFps) : null,
    video_codecs: f.videoCodecs,
    has_audio: f.hasAudio === 'yes' ? true : f.hasAudio === 'no' ? false : null,
    has_gps: f.hasGps === 'yes' ? true : f.hasGps === 'no' ? false : null,
    limit: f.limit ? parseInt(f.limit) : null,
    sort_desc: f.sortDesc,
  }
}

function hasAnyFilter(f: FilterState): boolean {
  return (
    f.personIds.length > 0 || !!f.personCount ||
    !!f.country || !!f.fromDate || !!f.toDate ||
    f.itemTypes.length > 0 ||
    f.selectedConcepts.length > 0 ||
    f.selectedCameras.length > 0 ||
    !!f.minDuration || !!f.maxDuration || !!f.minWidth || !!f.minFps ||
    f.videoCodecs.length > 0 ||
    !!f.hasAudio || !!f.hasGps
  )
}

export default function App() {
  const [persons, setPersons] = useState<Person[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [cameras, setCameras] = useState<Camera[]>([])
  const [result, setResult] = useState<CollectResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cart, setCart] = useState<MediaItem[]>([])
  const { filters, setFilters } = useUrlFilters()
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    Promise.all([fetchPersons(), fetchLocations(), fetchConcepts(), fetchCameras()])
      .then(([p, l, c, cam]) => {
        setPersons(p)
        setLocations(l)
        setConcepts(c)
        setCameras(cam)
      })
      .catch(e => setError(String(e)))
  }, [])

  const handleSearch = async (req: CollectRequest) => {
    setLoading(true)
    setError(null)
    try {
      const res = await runCollect(req)
      setResult(res)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  // Auto-search on filter change with 400ms debounce
  useEffect(() => {
    if (!hasAnyFilter(filters)) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => handleSearch(toRequest(filters)), 400)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [filters])

  const cartIds = new Set(cart.map(i => i.id))

  const toggleCart = (item: MediaItem) => {
    setCart(prev =>
      prev.some(i => i.id === item.id) ? prev.filter(i => i.id !== item.id) : [...prev, item]
    )
  }

  const addAllToCart = (items: MediaItem[]) => {
    setCart(prev => {
      const ids = new Set(prev.map(i => i.id))
      return [...prev, ...items.filter(i => !ids.has(i.id))]
    })
  }

  const removeFromCart = (ids: number[]) => {
    const remove = new Set(ids)
    setCart(prev => prev.filter(i => !remove.has(i.id)))
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      <FilterPanel
        persons={persons}
        locations={locations}
        concepts={concepts}
        cameras={cameras}
        filters={filters}
        onFiltersChange={setFilters}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {error && (
          <div className="p-4 bg-red-900/50 text-red-300 text-sm border-b border-red-700">{error}</div>
        )}
        {loading && (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-lg">Searching…</div>
        )}
        {!loading && result && (
          <ResultsGrid items={result.items} totalMb={result.total_mb}
            cart={cart} cartIds={cartIds} onToggle={toggleCart}
            onSelectAll={addAllToCart} onClearAll={removeFromCart}
            onClearCart={() => setCart([])}
            onRemoveFromCart={id => setCart(prev => prev.filter(i => i.id !== id))}
            sortDesc={filters.sortDesc}
            onSortToggle={() => {
              const next = { ...filters, sortDesc: !filters.sortDesc }
              setFilters(next)
              handleSearch(toRequest(next))
            }} />
        )}
        {!loading && !result && !error && (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-600 gap-3">
            <span className="text-5xl">🎬</span>
            <span className="text-lg">Set filters to find your vlog material</span>
          </div>
        )}
      </div>
    </div>
  )
}
