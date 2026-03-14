import { useState } from 'react'
import { fetchSchema } from '../api'

interface Props {
  onRun: (sql: string) => void
  loading: boolean
}

export function SqlPanel({ onRun, loading }: Props) {
  const [sql, setSql] = useState('')
  const [copyLabel, setCopyLabel] = useState('Copy Schema')

  const copySchema = async () => {
    const schema = await fetchSchema()
    await navigator.clipboard.writeText(schema)
    setCopyLabel('Copied!')
    setTimeout(() => setCopyLabel('Copy Schema'), 2000)
  }

  return (
    <div className="bg-gray-900 border-r border-gray-700 w-80 flex flex-col p-4 gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase">SQL Query</span>
        <button
          onClick={copySchema}
          className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
        >
          {copyLabel}
        </button>
      </div>

      <p className="text-xs text-gray-500 leading-relaxed">
        Click <strong className="text-gray-400">Copy Schema</strong> to get the full DB schema,
        paste it into Claude or any AI with your question, then run the generated SELECT here.
      </p>

      <textarea
        value={sql}
        onChange={e => setSql(e.target.value)}
        placeholder={'SELECT u.id, u.filename, u.takentime\nFROM unit u\nLIMIT 20'}
        className="flex-1 min-h-64 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200 font-mono resize-none focus:outline-none focus:border-blue-500"
        spellCheck={false}
        onKeyDown={e => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            if (sql.trim() && !loading) onRun(sql)
          }
        }}
      />

      <button
        onClick={() => onRun(sql)}
        disabled={loading || !sql.trim()}
        className="py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded text-sm transition-colors"
      >
        {loading ? 'Running…' : 'Run SQL'}
        <span className="ml-2 text-xs opacity-50">⌘↵</span>
      </button>
    </div>
  )
}
