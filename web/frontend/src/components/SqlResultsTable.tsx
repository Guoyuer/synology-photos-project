import type { SqlResult } from '../types'

interface Props {
  result: SqlResult | null
}

export function SqlResultsTable({ result }: Props) {
  if (!result) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-gray-600 gap-3">
        <span className="text-5xl">🗄️</span>
        <span className="text-lg">Write a SELECT query and run it</span>
      </div>
    )
  }

  if (result.count === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">No rows returned</div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="px-4 py-3 bg-gray-900 border-b border-gray-700 shrink-0">
        <span className="text-gray-400 text-sm">{result.count} rows</span>
        <span className="ml-3 text-gray-600 text-xs">{result.columns.length} columns</span>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <table className="text-sm text-gray-300 border-collapse">
          <thead>
            <tr>
              {result.columns.map(col => (
                <th key={col} className="pb-2 pr-6 text-left text-xs text-gray-500 whitespace-nowrap border-b border-gray-700">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, i) => (
              <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/50">
                {row.map((val, j) => (
                  <td key={j} className="py-1.5 pr-6 text-xs font-mono max-w-xs truncate text-gray-300">
                    {val === null ? <span className="text-gray-600">null</span> : String(val)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
