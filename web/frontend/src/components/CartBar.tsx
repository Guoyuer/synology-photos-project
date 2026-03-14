import { useState } from 'react'
import { downloadItems, thumbnailUrl } from '../api'
import { fmt, fmtDur, TYPE_BADGE } from '../utils'
import type { MediaItem } from '../types'

interface Props {
  cart: MediaItem[]
  onClear: () => void
  onRemove: (id: number) => void
}

export function CartBar({ cart, onClear, onRemove }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (cart.length === 0) return null

  const totalBytes = cart.reduce((s, i) => s + (i.filesize || 0), 0)

  const handleDownload = async () => {
    setDownloading(true)
    setError(null)
    try {
      await downloadItems(cart.map(i => i.id))
    } catch (e) {
      setError(String(e))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="shrink-0 bg-gray-900 border-t border-green-700">
      {/* Summary bar — click to expand */}
      <div
        className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-gray-800 transition-colors select-none"
        onClick={() => setExpanded(e => !e)}
      >
        <span className="text-green-400 font-semibold text-sm">🛒 Cart</span>
        <span className="text-gray-300 text-sm">{cart.length} items</span>
        <span className="text-gray-500 text-sm">{fmt(totalBytes)}</span>
        <span className="text-gray-600 text-xs ml-1">{expanded ? '▼' : '▲'}</span>
        {error && <span className="text-red-400 text-xs">{error}</span>}
        <div className="ml-auto flex items-center gap-2" onClick={e => e.stopPropagation()}>
          <button onClick={onClear}
            className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors">
            Clear
          </button>
          <button onClick={handleDownload} disabled={downloading}
            className="text-xs px-4 py-1.5 bg-green-700 hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded transition-colors">
            {downloading ? 'Preparing…' : `Download ${cart.length} files`}
          </button>
        </div>
      </div>

      {/* Expanded list */}
      {expanded && (
        <div className="max-h-64 overflow-y-auto border-t border-gray-700">
          {cart.map(item => (
            <div key={item.id} className="flex items-center gap-3 px-4 py-2 hover:bg-gray-800 border-b border-gray-800">
              <img
                src={thumbnailUrl(item.id, 'sm')}
                className="w-10 h-10 object-cover rounded bg-gray-700 shrink-0"
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-200 truncate font-mono">{item.filename}</p>
                <p className="text-xs text-gray-500">
                  <span className={`inline px-1 py-0.5 rounded text-white mr-1 ${TYPE_BADGE[item.type_name] ?? 'bg-gray-700'}`}>
                    {item.type_name}
                  </span>
                  {fmt(item.filesize)}
                  {item.duration ? ` · ${fmtDur(item.duration)}` : ''}
                  {item.taken_iso ? ` · ${item.taken_iso.slice(0, 10)}` : ''}
                </p>
              </div>
              <button onClick={() => onRemove(item.id)}
                className="text-gray-600 hover:text-red-400 text-lg leading-none px-1 transition-colors">
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
