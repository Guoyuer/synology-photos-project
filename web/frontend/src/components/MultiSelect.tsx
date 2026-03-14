import { useEffect, useRef, useState } from 'react'

interface Option {
  value: string | number
  label: string
  sub?: string
}

interface Props {
  options: Option[]
  selected: (string | number)[]
  onChange: (values: (string | number)[]) => void
  placeholder?: string
  searchable?: boolean
}

export function MultiSelect({ options, selected, onChange, placeholder = 'Select...', searchable = true }: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = query
    ? options.filter(o => o.label.toLowerCase().includes(query.toLowerCase()))
    : options

  const toggle = (val: string | number) => {
    onChange(selected.includes(val) ? selected.filter(v => v !== val) : [...selected, val])
  }

  const selectedLabels = selected.map(v => options.find(o => o.value === v)?.label ?? v).join(', ')

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full text-left px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200 flex justify-between items-center"
      >
        <span className="truncate">{selected.length ? selectedLabels : <span className="text-gray-500">{placeholder}</span>}</span>
        <span className="ml-2 text-gray-400">▾</span>
      </button>
      {open && (
        <div className="absolute z-[9999] mt-1 w-full bg-gray-800 border border-gray-600 rounded shadow-lg max-h-64 overflow-y-auto">
          {searchable && (
            <input
              autoFocus
              className="w-full px-3 py-2 bg-gray-900 text-sm text-gray-200 border-b border-gray-600 outline-none"
              placeholder="Search..."
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
          )}
          {filtered.length === 0 && <div className="px-3 py-2 text-gray-500 text-sm">No results</div>}
          {filtered.map(o => (
            <label key={o.value} className="flex items-center gap-2 px-3 py-2 hover:bg-gray-700 cursor-pointer">
              <input
                type="checkbox"
                checked={selected.includes(o.value)}
                onChange={() => toggle(o.value)}
                className="accent-blue-500"
              />
              <span className="text-sm text-gray-200">{o.label}</span>
              {o.sub && <span className="text-xs text-gray-500 ml-auto">{o.sub}</span>}
            </label>
          ))}
        </div>
      )}
    </div>
  )
}
