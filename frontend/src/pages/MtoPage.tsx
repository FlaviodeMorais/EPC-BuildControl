import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMtoItems } from '../api/mto'

const PROJECT_ID = 1

const TYPES = [
  'PIPE','FLANGE','ELBOW','TEE','REDUCER','VALVE',
  'CAP','COUPLING','OLET','SUPPORT',
]

export default function MtoPage() {
  const [type, setType]     = useState('')
  const [scope, setScope]   = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage]     = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['mto', type, scope, search, page],
    queryFn: () => getMtoItems(PROJECT_ID, {
      item_3d_type: type || undefined,
      scope: scope || undefined,
      search: search || undefined,
      page,
      page_size: 100,
    }),
  })

  const total = data?.total ?? 0
  const pages = Math.ceil(total / 100)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">MTO — Materiais de Tubulação</h1>
        <span className="text-sm text-gray-500">{total.toLocaleString('pt-BR')} itens</span>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-3 flex flex-wrap gap-3">
        <input type="text" placeholder="Isométrico, código ou descrição..." value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm w-64" />
        <select value={type} onChange={e => { setType(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Todos os tipos</option>
          {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={scope} onChange={e => { setScope(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Todos os escopos</option>
          <option value="SHOP">SHOP</option>
          <option value="FIELD">FIELD</option>
          <option value="VENDOR">VENDOR</option>
        </select>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr className="text-left text-xs text-gray-500">
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2">Descrição</th>
              <th className="px-3 py-2">Cód. Material</th>
              <th className="px-3 py-2">Espec.</th>
              <th className="px-3 py-2 text-right">Ø mm</th>
              <th className="px-3 py-2 text-right">Peso kg</th>
              <th className="px-3 py-2">Isométrico</th>
              <th className="px-3 py-2">Spool</th>
              <th className="px-3 py-2">Escopo</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={10} className="text-center py-8 text-gray-400">Carregando...</td></tr>
            )}
            {data?.data.map(item => (
              <tr key={item.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-1.5 font-mono text-xs text-blue-700">{item.material_code_alt}</td>
                <td className="px-3 py-1.5 text-xs">{item.item_3d_type}</td>
                <td className="px-3 py-1.5 text-xs text-gray-600 max-w-xs truncate" title={item.description}>
                  {item.description}
                </td>
                <td className="px-3 py-1.5 font-mono text-xs">{item.material_code_std}</td>
                <td className="px-3 py-1.5 text-xs">{item.material_spec}</td>
                <td className="px-3 py-1.5 text-right text-xs">{item.diameter_nom_mm ?? '—'}</td>
                <td className="px-3 py-1.5 text-right text-xs">{item.weight_kg?.toLocaleString('pt-BR') ?? '—'}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{item.isometrico}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{item.spool_number_raw}</td>
                <td className="px-3 py-1.5 text-xs">
                  <span className="bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded text-xs">{item.scope}</span>
                </td>
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
