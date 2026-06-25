import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

const PID = 1

export default function NcrPage() {
  const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all')

  const { data = [], isLoading } = useQuery({
    queryKey: ['ncr'],
    queryFn: () => api.get(`/projects/${PID}/ncr`).then(r => r.data),
  })

  const filtered = (data as Record<string, unknown>[]).filter(n => {
    if (filter === 'open')   return !n.released
    if (filter === 'closed') return n.released
    return true
  })

  const open   = (data as Record<string, unknown>[]).filter(n => !n.released).length
  const closed = (data as Record<string, unknown>[]).filter(n =>  n.released).length

  function fmtDate(d: unknown) {
    if (!d) return '—'
    return String(d).slice(0, 10)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">Não Conformidades (NCR / RNC)</h1>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4">
          <p className="text-xs text-gray-500">Total NCR</p>
          <p className="text-2xl font-bold text-gray-800 mt-1">{data.length}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 cursor-pointer" onClick={() => setFilter('open')}>
          <p className="text-xs text-gray-500">Abertas</p>
          <p className="text-2xl font-bold text-red-600 mt-1">{open}</p>
        </div>
        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 cursor-pointer" onClick={() => setFilter('closed')}>
          <p className="text-xs text-gray-500">Encerradas</p>
          <p className="text-2xl font-bold text-green-600 mt-1">{closed}</p>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-100 shadow-sm">
        <div className="flex gap-2 px-4 py-3 border-b">
          {(['all','open','closed'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-xs px-3 py-1 rounded-full transition ${filter===f ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {f==='all' ? 'Todas' : f==='open' ? 'Abertas' : 'Encerradas'}
            </button>
          ))}
          <span className="ml-auto text-xs text-gray-400 self-center">{filtered.length} registros</span>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b text-xs text-gray-500">
            <tr>
              <th className="px-4 py-2 text-left">RNC Nº</th>
              <th className="px-4 py-2 text-left">Descrição</th>
              <th className="px-4 py-2 text-left">Operação</th>
              <th className="px-4 py-2 text-center">Gerado em</th>
              <th className="px-4 py-2 text-center">Status</th>
              <th className="px-4 py-2 text-center">Encerrado em</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={6} className="text-center py-8 text-gray-400">Carregando...</td></tr>}
            {filtered.length === 0 && !isLoading && (
              <tr><td colSpan={6} className="text-center py-8 text-gray-400">Nenhum registro</td></tr>
            )}
            {filtered.map((n, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{String(n.rnc_number ?? '—')}</td>
                <td className="px-4 py-2 text-xs text-gray-700 max-w-xs truncate">{String(n.description ?? '—')}</td>
                <td className="px-4 py-2 text-xs">{String(n.operation_code ?? '—')}</td>
                <td className="px-4 py-2 text-center text-xs text-gray-500">{fmtDate(n.dt_generated)}</td>
                <td className="px-4 py-2 text-center">
                  {n.released
                    ? <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Encerrada</span>
                    : <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Aberta</span>}
                </td>
                <td className="px-4 py-2 text-center text-xs text-gray-500">{fmtDate(n.dt_released)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
