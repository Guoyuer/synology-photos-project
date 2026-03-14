import { useRef, useState, useMemo, useCallback } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { downloadItems, thumbnailUrl } from '../api'
import { fmt, fmtDur, TYPE_BADGE } from '../utils'
import { ContextMenu } from './ContextMenu'
import { Lightbox } from './Lightbox'
import { MetaPanel } from './MetaPanel'
import type { MediaItem } from '../types'

interface Props {
  items: MediaItem[]
  totalMb: number
  cart: MediaItem[]
  cartIds: Set<number>
  sortDesc: boolean
  onSortToggle: () => void
  onToggle: (item: MediaItem) => void
  onSelectAll: (items: MediaItem[]) => void
  onClearAll: (ids: number[]) => void
  onClearCart: () => void
  onRemoveFromCart: (id: number) => void
}

const ITEM_W = 172  // approximate grid item width + gap

export function ResultsGrid({ items, totalMb, cart, cartIds, sortDesc, onSortToggle, onToggle, onSelectAll, onClearAll, onClearCart, onRemoveFromCart }: Props) {
  const [view, setView] = useState<'grid' | 'list'>('grid')
  const [preview, setPreview] = useState<MediaItem | null>(null)
  const [infoItem, setInfoItem] = useState<MediaItem | null>(null)
  const [ctxMenu, setCtxMenu] = useState<{ item: MediaItem; x: number; y: number } | null>(null)
  const [cartExpanded, setCartExpanded] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [dlError, setDlError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const roRef = useRef<ResizeObserver | null>(null)
  const [containerWidth, setContainerWidth] = useState(800)

  const containerRef = useCallback((node: HTMLDivElement | null) => {
    if (roRef.current) { roRef.current.disconnect(); roRef.current = null }
    if (!node) return
    setContainerWidth(node.offsetWidth)
    const ro = new ResizeObserver(entries => setContainerWidth(entries[0].contentRect.width))
    ro.observe(node)
    roRef.current = ro
  }, [])

  const cols = Math.max(1, Math.floor((containerWidth - 16) / ITEM_W))
  const rowHeight = 200

  const rows = useMemo(() => {
    const r: MediaItem[][] = []
    for (let i = 0; i < items.length; i += cols) r.push(items.slice(i, i + cols))
    return r
  }, [items, cols])

  const gridVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowHeight,
    overscan: 5,
  })

  const listVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 44,
    overscan: 10,
  })

  const openCtxMenu = (e: React.MouseEvent, item: MediaItem) => {
    e.preventDefault()
    setCtxMenu({ item, x: e.clientX, y: e.clientY })
  }

  const cartBytes = cart.reduce((s, i) => s + (i.filesize || 0), 0)

  const handleDownload = async () => {
    setDownloading(true)
    setDlError(null)
    try {
      await downloadItems(cart.map(i => i.id))
    } catch (e) {
      setDlError(String(e))
    } finally {
      setDownloading(false)
    }
  }

  if (items.length === 0) {
    return <div className="flex-1 flex items-center justify-center text-gray-500 text-lg">No results</div>
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Toolbar */}
      <div className="flex items-center gap-4 px-4 py-3 bg-gray-900 border-b border-gray-700 shrink-0">
        <span className="text-gray-300 font-semibold">{items.length} items</span>
        <span className="text-gray-500 text-sm">{totalMb >= 1000 ? (totalMb / 1024).toFixed(1) + ' GB' : totalMb.toFixed(1) + ' MB'} total</span>
        <div className="ml-auto flex items-center gap-3">
          <button onClick={() => onSelectAll(items)} className="text-xs text-blue-400 hover:text-blue-300">Select all</button>
          <button onClick={() => onClearAll(items.map(i => i.id))} className="text-xs text-gray-400 hover:text-gray-300">Clear</button>

          {/* Cart summary button */}
          {cart.length > 0 && (
            <button
              onClick={() => setCartExpanded(e => !e)}
              className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-yellow-600/20 hover:bg-yellow-600/30 text-yellow-400 border border-yellow-700/50 transition-colors"
            >
              🛒 {cart.length} selected · {fmt(cartBytes)}
              <span className="text-yellow-600">{cartExpanded ? '▲' : '▼'}</span>
            </button>
          )}

          <button
            onClick={onSortToggle}
            title={sortDesc ? 'Newest first — click for oldest first' : 'Oldest first — click for newest first'}
            className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300 hover:bg-gray-600"
          >
            {sortDesc ? '↓ Newest' : '↑ Oldest'}
          </button>
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

      {/* Cart dropdown */}
      {cartExpanded && cart.length > 0 && (
        <div className="shrink-0 bg-gray-900 border-b border-yellow-700/40">
          <div className="max-h-56 overflow-y-auto">
            {cart.map(item => (
              <div key={item.id} className="flex items-center gap-3 px-4 py-2 hover:bg-gray-800 border-b border-gray-800">
                <img src={thumbnailUrl(item.id, item.cache_key, 'sm')} className="w-10 h-10 object-cover rounded bg-gray-700 shrink-0" />
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
                <button onClick={() => onRemoveFromCart(item.id)}
                  className="text-gray-600 hover:text-red-400 text-lg leading-none px-1 transition-colors">×</button>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-2 px-4 py-2 border-t border-gray-700">
            {dlError && <span className="text-red-400 text-xs flex-1">{dlError}</span>}
            <div className="ml-auto flex gap-2">
              <button onClick={onClearCart}
                className="text-xs px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors">
                Clear cart
              </button>
              <button onClick={handleDownload} disabled={downloading}
                className="text-xs px-4 py-1.5 bg-green-700 hover:bg-green-600 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded transition-colors">
                {downloading ? 'Preparing…' : `Download ${cart.length} files`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Scrollable container */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto overflow-x-hidden styled-scrollbar">
        {view === 'grid' ? (
          <div ref={containerRef} className="p-4">
            <div style={{ height: gridVirtualizer.getTotalSize(), position: 'relative' }}>
              {gridVirtualizer.getVirtualItems().map(vrow => (
                <div
                  key={vrow.key}
                  style={{ position: 'absolute', top: vrow.start, left: 0, right: 0, height: rowHeight, display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: '12px' }}
                >
                  {rows[vrow.index].map(item => (
                    <div
                      key={item.id}
                      onClick={() => onToggle(item)}
                      onContextMenu={e => openCtxMenu(e, item)}
                      className={`relative rounded overflow-hidden cursor-pointer border-2 transition-all
                        ${cartIds.has(item.id) ? 'border-blue-500' : 'border-transparent hover:border-gray-500'}`}
                    >
                      <img src={thumbnailUrl(item.id, item.cache_key, 'sm')} alt={item.filename} title={item.filename} className="w-full h-32 object-cover bg-gray-800"
                        onError={e => { (e.target as HTMLImageElement).style.visibility = 'hidden' }} />
                      {item.type_name !== 'photo' && (
                        <div className="absolute top-1 left-1">
                          <span className={`text-xs px-1 py-0.5 rounded ${TYPE_BADGE[item.type_name] ?? 'bg-gray-700'} text-white`}>
                            {item.type_name}
                          </span>
                        </div>
                      )}
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
                      <div className="p-1.5" title={item.filename}>
                        <p className="text-xs text-gray-300 truncate">{item.taken_iso?.slice(0, 10)}</p>
                        <p className="text-xs text-gray-500">{item.district ?? item.country ?? ''}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <table className="w-full text-sm text-gray-300">
            <thead className="sticky top-0 bg-gray-950 z-10">
              <tr className="text-left text-xs text-gray-500 border-b border-gray-700">
                <th className="pb-2 pr-3 pl-4">Filename</th>
                <th className="pb-2 pr-3">Type</th>
                <th className="pb-2 pr-3">Date</th>
                <th className="pb-2 pr-3">Size</th>
                <th className="pb-2 pr-3">Res / Duration</th>
                <th className="pb-2">Location</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ height: listVirtualizer.getVirtualItems()[0]?.start ?? 0 }} />
              {listVirtualizer.getVirtualItems().map(vrow => {
                const item = items[vrow.index]
                return (
                  <tr key={vrow.key}
                    onClick={() => onToggle(item)}
                    onContextMenu={e => openCtxMenu(e, item)}
                    className={`border-b border-gray-800 cursor-pointer ${cartIds.has(item.id) ? 'bg-blue-900/30' : 'hover:bg-gray-800'}`}
                  >
                    <td className="py-2 pr-3 pl-4 font-mono text-xs max-w-xs truncate">{item.filename}</td>
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
                    <td className="py-2 text-xs text-gray-400">{item.district ?? item.country ?? '—'}</td>
                  </tr>
                )
              })}
              <tr style={{ height: listVirtualizer.getTotalSize() - (listVirtualizer.getVirtualItems().at(-1)?.end ?? 0) }} />
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
            { label: 'ⓘ Info', onClick: () => setInfoItem(ctxMenu.item) },
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
          onInfo={setInfoItem}
        />
      )}

      {infoItem && <MetaPanel item={infoItem} onClose={() => setInfoItem(null)} />}
    </div>
  )
}
