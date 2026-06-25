import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '../api/client'
import StatusBadge from '../components/ui/StatusBadge'
import type { Joint, JointStatus, PagedResponse } from '../types'

const PROJECT_ID = 1

const STATUSES: JointStatus[] = [
  '01_NAO_INICIADA','04_AGUARD_SOLDAGEM','09_AGUARD_VS',
  '12_AGUARD_LP_PM','15_AGUARD_RX_US','30_LIBERADA',
]

const NDT_COLOR: Record<string, string> = {
  A: 'text-green-600', R: 'text-red-600', N: 'text-gray-400', M: 'text-blue-600',
}

export default function JointListPage() {
  const [status, setStatus]   = useState('')
  const [material, setMat]    = useState('')
  const [isRepair, setRepair] = useState('')
  const [search, setSearch]   = useState('')
  const [page, setPage]       = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['joints', status, material, isRepair, search, page],
    queryFn: () => api.get<PagedResponse<Joint>>(`/projects/${PROJECT_ID}/joints`, {
      params: {
        status: status || undefined,
        material: material || undefined,
        is_repair: isRepair === '' ? undefined : isRepair === 'true',
        search: search || undefined,
        page,
        page_size: 100,
      },
    }).then(r => r.data),
  })

  const total = data?.total ?? 0
  const pages = Math.ceil(total / 100)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Juntas</h1>
        <span className="text-sm text-gray-500">{total.toLocaleString('pt-BR')} registros</span>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-3 flex flex-wrap gap-3">
        <input type="text" placeholder="Buscar junta..." value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm w-52" />
        <select value={status} onChange={e => { setStatus(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Todos os status</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace(/_/g,' ')}</option>)}
        </select>
        <select value={material} onChange={e => { setMat(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Material: todos</option>
          <option value="AC">AC — Carbono</option>
          <option value="AI">AI — Inox</option>
          <option value="AL">AL — Liga</option>
        </select>
        <select value={isRepair} onChange={e => { setRepair(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Reparos: todos</option>
          <option value="true">Somente reparos</option>
          <option value="false">Sem reparos</option>
        </select>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr className="text-left text-xs text-gray-500">
              <th className="px-3 py-2">Junta</th>
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2 text-right">Ø mm</th>
              <th className="px-3 py-2">Mat.</th>
              <th className="px-3 py-2">Soldador R</th>
              <th className="px-3 py-2">Soldador E</th>
              <th className="px-3 py-2 text-center">RX</th>
              <th className="px-3 py-2 text-center">LP</th>
              <th className="px-3 py-2 text-center">TT</th>
              <th className="px-3 py-2 text-center">Rep.</th>
              <th className="px-3 py-2">Soldagem</th>
              <th className="px-3 py-2">Liberação</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={13} className="text-center py-8 text-gray-400">Carregando...</td></tr>
            )}
            {data?.data.map(j => (
              <tr key={j.id} className={`border-b border-gray-50 hover:bg-gray-50 ${j.is_repair ? 'bg-red-50' : ''}`}>
                <td className="px-3 py-1.5 font-mono text-xs text-blue-700">{j.joint_key}</td>
                <td className="px-3 py-1.5 text-xs">{j.joint_type}</td>
                <td className="px-3 py-1.5">
                  <StatusBadge status={j.status} type="joint" />
                </td>
                <td className="px-3 py-1.5 text-right text-xs">{j.diameter_mm ?? '—'}</td>
                <td className="px-3 py-1.5 text-xs font-mono">{j.material}</td>
                <td className="px-3 py-1.5 text-xs font-mono">{j.welder_root ?? '—'}</td>
                <td className="px-3 py-1.5 text-xs font-mono">{j.welder_fill ?? '—'}</td>
                <td className={`px-3 py-1.5 text-center text-xs font-bold ${NDT_COLOR[j.result_rx ?? 'N']}`}>
                  {j.result_rx ?? '—'}
                </td>
                <td className={`px-3 py-1.5 text-center text-xs font-bold ${NDT_COLOR[j.result_lp ?? 'N']}`}>
                  {j.result_lp ?? '—'}
                </td>
                <td className="px-3 py-1.5 text-center text-xs">
                  {j.requires_tt ? <span className="text-amber-600 font-bold">TT</span> : '—'}
                </td>
                <td className="px-3 py-1.5 text-center">
                  {j.is_repair && <span className="text-red-500 text-xs font-bold">R</span>}
                </td>
                <td className="px-3 py-1.5 text-xs text-gray-500">{j.dt_soldagem?.slice(0,10) ?? '—'}</td>
                <td className="px-3 py-1.5 text-xs text-gray-500">{j.dt_lib_end?.slice(0,10) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

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
