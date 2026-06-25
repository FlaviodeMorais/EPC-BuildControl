import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getSpools } from '../api/spools'
import StatusBadge from '../components/ui/StatusBadge'
import type { SpoolStatus } from '../types'

const PROJECT_ID = 1

const STATUSES: SpoolStatus[] = [
  'NAO_INICIADO','EM_FABRICACAO','FABRICADO','EM_CAMPO','MONTADO','TESTADO',
]

export default function SpoolListPage() {
  const [status, setStatus] = useState('')
  const [hold, setHold] = useState<boolean | undefined>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['spools', status, hold, search, page],
    queryFn: () => getSpools(PROJECT_ID, {
      status: status || undefined,
      hold,
      search: search || undefined,
      page,
      page_size: 50,
    }),
  })

  const total = data?.total ?? 0
  const pages = Math.ceil(total / 50)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Spools</h1>
        <span className="text-sm text-gray-500">{total.toLocaleString('pt-BR')} registros</span>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-3 flex flex-wrap gap-3">
        <input
          type="text" placeholder="Buscar spool..." value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm w-52"
        />
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Todos os status</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g,' ')}</option>)}
        </select>
        <select value={hold === undefined ? '' : String(hold)}
          onChange={e => { setHold(e.target.value === '' ? undefined : e.target.value === 'true'); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Hold: todos</option>
          <option value="true">Em Hold</option>
          <option value="false">Sem Hold</option>
        </select>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr className="text-left text-xs text-gray-500">
              <th className="px-3 py-2">Spool</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Mat.</th>
              <th className="px-3 py-2 text-right">Ø mm</th>
              <th className="px-3 py-2 text-right">Peso kg</th>
              <th className="px-3 py-2 text-right">Juntas</th>
              <th className="px-3 py-2 text-right">Sold.</th>
              <th className="px-3 py-2 text-right">Lib.</th>
              <th className="px-3 py-2 text-center">Hold</th>
              <th className="px-3 py-2">Embarque</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={10} className="text-center py-8 text-gray-400">Carregando...</td></tr>
            )}
            {data?.data.map(s => (
              <tr key={s.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-2">
                  <Link to={`/spools/${s.id}`} className="font-mono text-blue-600 hover:underline text-xs">
                    {s.spool_key}
                  </Link>
                </td>
                <td className="px-3 py-2">
                  <StatusBadge status={s.status} type="spool" />
                </td>
                <td className="px-3 py-2 text-xs font-mono">{s.material}</td>
                <td className="px-3 py-2 text-right text-xs">{s.diameter_mm ?? '—'}</td>
                <td className="px-3 py-2 text-right text-xs">{s.weight_kg?.toLocaleString('pt-BR') ?? '—'}</td>
                <td className="px-3 py-2 text-right">{s.joints_total ?? '—'}</td>
                <td className="px-3 py-2 text-right text-blue-600">{s.joints_welded ?? '—'}</td>
                <td className="px-3 py-2 text-right text-green-600">{s.joints_released ?? '—'}</td>
                <td className="px-3 py-2 text-center">
                  {s.hold && <span className="bg-red-100 text-red-600 text-xs px-1.5 py-0.5 rounded">HOLD</span>}
                </td>
                <td className="px-3 py-2 text-xs text-gray-500">{s.dt_embarque?.slice(0,10) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Paginação */}
      {pages > 1 && (
        <div className="flex items-center gap-2 justify-end text-sm">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 border rounded disabled:opacity-40">‹</button>
          <span className="text-gray-600">Pág. {page} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page === pages}
            className="px-3 py-1 border rounded disabled:opacity-40">›</button>
        </div>
      )}
    </div>
  )
}
