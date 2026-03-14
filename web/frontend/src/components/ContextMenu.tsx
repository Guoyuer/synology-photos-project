import { useEffect, useRef } from 'react'

interface MenuItem {
  label: string
  onClick: () => void
}

interface Props {
  x: number
  y: number
  items: MenuItem[]
  onClose: () => void
}

export function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    const escHandler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', escHandler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', escHandler)
    }
  }, [])

  // Keep menu inside viewport
  const style: React.CSSProperties = {
    position: 'fixed',
    top: y,
    left: x,
    zIndex: 99999,
  }

  return (
    <div ref={ref} style={style}
      className="bg-gray-800 border border-gray-600 rounded shadow-xl py-1 min-w-[160px]">
      {items.map(item => (
        <button
          key={item.label}
          onClick={() => { item.onClick(); onClose() }}
          className="w-full text-left px-4 py-2 text-sm text-gray-200 hover:bg-gray-700 transition-colors"
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}
