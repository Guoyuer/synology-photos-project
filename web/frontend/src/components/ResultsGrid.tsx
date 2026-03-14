import { useState } from 'react'
import { thumbnailUrl } from '../api'
import { ContextMenu } from './ContextMenu'
import { Lightbox } from './Lightbox'
import type { MediaItem } from '../types'

interface Props {
  items: MediaItem[]
  totalMb: number
  cartIds: Set<number>
  onToggle: (item: MediaItem) => void
  onSelectAll: (items: MediaItem[]) => void
  onClearAll: (ids: number[]) => void
}

const TYPE_BADGE: Record<string, string> = {
  photo: 'bg-blue-700',
  video: 'bg-red-700',
  live: 'bg-green-700',
  motion: 'bg-purple-700',
}

function fmt(bytes: number) {
  if (bytes > 1024 * 1024 * 1024) return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function fmtDur(ms: number | null) {
  if (!ms) return ''
  const s = Math.round(ms / 1000)
  return s >= 60 ? `${Math.floor(s / 60)}m${s % 60}s` : `${s}s`
}

export function ResultsGrid({ items, totalMb, cartIds, onToggle, onSelectAll, onClearAll }: Props) {
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [preview, setPreview] = useState<MediaItem | null>(null)
  const [ctxMenu, setCtxMenu] = useState<{ item: MediaItem; x: number; y: number } | null>(null)

  const openCtxMenu = (e: React.MouseEvent, item: MediaItem) => {
    e.preventDefault()
    setCtxMenu({ item, x: e.clientX, y: e.clientY })
  }

  const selectedInView = items.filter(i => cartIds.has(i.id))
  const selectedBytes = selectedInView.reduce((s, i) => s + (i.filesize || 0), 0)

  if (items.length === 0) {
    return <div className="flex-1 flex items-center justify-center text-gray-500 text-lg">No results</div>
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex items-center gap-4 px-4 py-3 bg-gray-900 border-b border-gray-700 shrink-0">
        <span className="text-gray-300 font-semibold">{items.length} items</span>
        <span className="text-gray-500 text-sm">{totalMb.toFixed(1)} MB total</span>
        <div className="ml-auto flex items-center gap-3">
          <button onClick={() => onSelectAll(items)} className="text-xs text-blue-400 hover:text-blue-300">Select all</button>
          <button onClick={() => onClearAll(items.map(i => i.id))} className="text-xs text-gray-400 hover:text-gray-300">Clear</button>
          {selectedInView.length > 0 && (
            <span className="text-xs text-yellow-400">{selectedInView.length} selected · {fmt(selectedBytes)}</span>
          )}
          <div className="flex gap-1">
            <button onClick={() => setView('grid')}
              className={`px-2 py-1 rounded text-xs ${view === 'grid' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'}`}>
              Grid
            </button>
            <button onClick={() => setView('list')}
              className={`px-2 py-1 rounded text-xs ${view === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300'}`}>
              List
            </button>
          </div>
        </div>
      </div>

      {/* Items */}
      <div className="flex-1 overflow-y-auto p-4">
        {view === 'grid' ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(160px,1fr))] gap-3">
            {items.map(item => (
              <div
                key={item.id}
                onClick={() => onToggle(item)}
                onContextMenu={e => openCtxMenu(e, item)}
                className={`relative rounded overflow-hidden cursor-pointer border-2 transition-all
                  ${cartIds.has(item.id) ? 'border-blue-500' : 'border-transparent hover:border-gray-500'}`}
              >
                <img
                  src={thumbnailUrl(item.id, 'sm')}
                  alt={item.filename}
                  className="w-full h-32 object-cover bg-gray-800"
                  loading="lazy"
                />
                <div className="absolute top-1 left-1">
                  <span className={`text-xs px-1 py-0.5 rounded ${TYPE_BADGE[item.type_name] ?? 'bg-gray-700'} text-white`}>
                    {item.type_name}
                  </span>
                </div>
                {item.duration && (
                  <div className="absolute bottom-1 right-1 text-xs bg-black/70 text-white px-1 rounded">
                    {fmtDur(item.duration)}
                  </div>
                )}
                {cartIds.has(item.id) && (
                  <div className="absolute inset-0 bg-blue-500/20 flex items-center justify-center">
                    <span className="text-2xl">✓</span>
                  </div>
                )}
                <div className="p-1.5">
                  <p className="text-xs text-gray-300 truncate">{item.filename}</p>
                  <p className="text-xs text-gray-500">{item.district ?? item.country ?? ''}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <table className="w-full text-sm text-gray-300">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-700">
                <th className="pb-2 pr-3">Filename</th>
                <th className="pb-2 pr-3">Type</th>
                <th className="pb-2 pr-3">Date</th>
                <th className="pb-2 pr-3">Size</th>
                <th className="pb-2 pr-3">Res / Duration</th>
                <th className="pb-2 pr-3">Location</th>
                <th className="pb-2">Camera</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id}
                  onClick={() => onToggle(item)}
                  onContextMenu={e => openCtxMenu(e, item)}
                  className={`border-b border-gray-800 cursor-pointer ${cartIds.has(item.id) ? 'bg-blue-900/30' : 'hover:bg-gray-800'}`}
                >
                  <td className="py-2 pr-3 font-mono text-xs max-w-xs truncate">{item.filename}</td>
                  <td className="py-2 pr-3">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${TYPE_BADGE[item.type_name] ?? 'bg-gray-700'} text-white`}>
                      {item.type_name}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-xs text-gray-400 whitespace-nowrap">
                    {item.taken_iso?.slice(0, 16).replace('T', ' ')}
                  </td>
                  <td className="py-2 pr-3 text-xs">{fmt(item.filesize)}</td>
                  <td className="py-2 pr-3 text-xs">
                    {item.vres_x ? `${item.vres_x}p` : item.width ? `${item.width}×${item.height}` : ''}
                    {item.duration ? ` · ${fmtDur(item.duration)}` : ''}
                  </td>
                  <td className="py-2 pr-3 text-xs text-gray-400">{item.district ?? item.country ?? '—'}</td>
                  <td className="py-2 text-xs text-gray-400 max-w-[120px] truncate">{item.camera ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x} y={ctxMenu.y}
          onClose={() => setCtxMenu(null)}
          items={[
            { label: '🔍 View full size', onClick: () => setPreview(ctxMenu.item) },
            {
              label: cartIds.has(ctxMenu.item.id) ? '✓ Remove from cart' : '+ Add to cart',
              onClick: () => onToggle(ctxMenu.item),
            },
          ]}
        />
      )}

      {preview && (
        <Lightbox
          item={preview}
          items={items}
          onClose={() => setPreview(null)}
          onNav={setPreview}
        />
      )}
    </div>
  )
}
