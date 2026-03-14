import { useEffect } from 'react'
import { mediaUrl } from '../api'
import type { MediaItem } from '../types'

interface Props {
  item: MediaItem
  items: MediaItem[]
  onClose: () => void
  onNav: (item: MediaItem) => void
}

function fmt(bytes: number) {
  if (bytes >= 1024 * 1024 * 1024) return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

function fmtDur(ms: number | null) {
  if (!ms) return ''
  const s = Math.round(ms / 1000)
  return s >= 60 ? `${Math.floor(s / 60)}m${s % 60}s` : `${s}s`
}

export function Lightbox({ item, items, onClose, onNav }: Props) {
  const idx = items.findIndex(i => i.id === item.id)
  const prev = idx > 0 ? items[idx - 1] : null
  const next = idx < items.length - 1 ? items[idx + 1] : null
  // type 1=video, 3=live photo, 6=motion photo — all have a playable video component
  const isVideo = item.item_type === 1
  const isLive = item.item_type === 3 || item.item_type === 6

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft' && prev) onNav(prev)
      if (e.key === 'ArrowRight' && next) onNav(next)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [item, prev, next])

  return (
    <div
      className="fixed inset-0 z-[99999] bg-black/90 flex flex-col"
      onClick={onClose}
    >
      {/* Header */}
      <div className="shrink-0 flex items-center justify-between px-5 py-3 bg-black/50"
        onClick={e => e.stopPropagation()}>
        <div className="text-sm text-gray-300 font-mono truncate max-w-lg">{item.filename}</div>
        <div className="flex items-center gap-4 text-xs text-gray-500 ml-4 shrink-0">
          {item.taken_iso && <span>{item.taken_iso.slice(0, 16).replace('T', ' ')}</span>}
          {item.camera && <span>{item.camera}</span>}
          {item.vres_x ? <span>{item.vres_x}p</span> : item.width ? <span>{item.width}×{item.height}</span> : null}
          {item.duration && <span>{fmtDur(item.duration)}</span>}
          <span>{fmt(item.filesize)}</span>
          <span className="text-gray-400">{idx + 1} / {items.length}</span>
        </div>
        <button onClick={onClose}
          className="ml-6 text-gray-400 hover:text-white text-2xl leading-none transition-colors">
          ×
        </button>
      </div>

      {/* Media */}
      <div className="flex-1 flex items-center justify-center min-h-0 relative"
        onClick={onClose}>
        {isVideo ? (
          <video
            key={item.id}
            src={mediaUrl(item.id)}
            controls
            autoPlay
            className="max-w-full max-h-full"
            onClick={e => e.stopPropagation()}
          />
        ) : isLive ? (
          <video
            key={item.id}
            src={mediaUrl(item.id, true)}
            controls
            autoPlay
            loop
            className="max-w-full max-h-full"
            onClick={e => e.stopPropagation()}
          />
        ) : (
          <img
            key={item.id}
            src={mediaUrl(item.id)}
            alt={item.filename}
            className="max-w-full max-h-full object-contain"
            onClick={e => e.stopPropagation()}
          />
        )}

        {/* Prev */}
        {prev && (
          <button
            onClick={e => { e.stopPropagation(); onNav(prev) }}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-4xl text-white/60 hover:text-white transition-colors px-2"
          >
            ‹
          </button>
        )}

        {/* Next */}
        {next && (
          <button
            onClick={e => { e.stopPropagation(); onNav(next) }}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-4xl text-white/60 hover:text-white transition-colors px-2"
          >
            ›
          </button>
        )}
      </div>
    </div>
  )
}
