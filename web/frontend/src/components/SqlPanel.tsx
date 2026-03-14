import { useState } from 'react'

interface Props {
  onAsk: (question: string) => void
  onSql: (sql: string) => void
  loading: boolean
  generatedSql: string | null
}

export function SqlPanel({ onAsk, onSql, loading, generatedSql }: Props) {
  const [question, setQuestion] = useState('')
  const [editedSql, setEditedSql] = useState<string | null>(null)

  const currentSql = editedSql ?? generatedSql

  const handleAsk = () => {
    if (!question.trim() || loading) return
    setEditedSql(null)
    onAsk(question)
  }

  return (
    <div className="bg-gray-900 border-r border-gray-700 w-80 flex flex-col p-4 gap-4">
      {/* Natural language input */}
      <div className="flex flex-col gap-2">
        <label className="text-xs font-semibold text-gray-400 uppercase">Ask in plain English</label>
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="e.g. Show me all 4K videos from Singapore in June 2025 longer than 30 seconds"
          className="h-28 px-3 py-2 bg-gray-800 border border-gray-600 rounded text-sm text-gray-200 resize-none focus:outline-none focus:border-blue-500"
          onKeyDown={e => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleAsk()
          }}
        />
        <button
          onClick={handleAsk}
          disabled={loading || !question.trim()}
          className="py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold rounded text-sm transition-colors"
        >
          {loading ? 'Thinking…' : 'Ask'}
          <span className="ml-2 text-xs opacity-50">⌘↵</span>
        </button>
      </div>

      {/* Generated / editable SQL */}
      {generatedSql && (
        <div className="flex flex-col gap-2 flex-1">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-gray-400 uppercase">Generated SQL</label>
            <span className="text-xs text-gray-600">editable</span>
          </div>
          <textarea
            value={currentSql ?? ''}
            onChange={e => setEditedSql(e.target.value)}
            className="flex-1 min-h-40 px-3 py-2 bg-gray-800 border border-gray-700 rounded text-xs text-green-300 font-mono resize-none focus:outline-none focus:border-blue-500"
            spellCheck={false}
          />
          {editedSql && editedSql !== generatedSql && (
            <button
              onClick={() => currentSql && onSql(currentSql)}
              disabled={loading}
              className="py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-xs transition-colors"
            >
              Re-run edited SQL
            </button>
          )}
        </div>
      )}
    </div>
  )
}
