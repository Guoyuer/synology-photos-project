import { useState } from 'react'
import { downloadItems } from '../api'
import type { MediaItem } from '../types'

interface Props {
  cart: MediaItem[]
  onClear: () => void
}

function fmt(bytes: number) {
  if (bytes >= 1024 * 1024 * 1024) return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

export function CartBar({ cart, onClear }: Props) {
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
    <div className="shrink-0 bg-gray-900 border-t border-green-700 px-4 py-3 flex items-center gap-4">
      <span className="text-green-400 font-semibold text-sm">🛒 Cart</span>
      <span className="text-gray-300 text-sm">{cart.length} items</span>
      <span className="text-gray-500 text-sm">{fmt(totalBytes)}</span>
      {error && <span className="text-red-400 text-xs">{error}</span>}
      <div className="ml-auto flex items-center gap-2">
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
  )
}
