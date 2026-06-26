import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getMtoItems, getMtoTypes } from '../api/mto'

const PROJECT_ID = 1
const fmt = (v: number | null, dec = 2) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { maximumFractionDigits: dec })

export default function MtoPage() {
  const [type, setType]     = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage]     = useState(1)

  const { data: types = [] } = useQuery({
    queryKey: ['mto-types'],
    queryFn: () => getMtoTypes(PROJECT_ID),
  })

  const { data, isLoading } = useQuery({
    queryKey: ['mto', type, search, page],
    queryFn: () => getMtoItems(PROJECT_ID, {
      item_3d_type: type || undefined,
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

      <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-3 flex flex-wrap gap-3">
        <input type="text" placeholder="Isométrico, código ou descrição..." value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm w-64" />
        <select value={type} onChange={e => { setType(e.target.value); setPage(1) }}
          className="border border-gray-200 rounded px-3 py-1.5 text-sm">
          <option value="">Todos os tipos</option>
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-x-auto">
        <table className="w-full text-sm whitespace-nowrap">
          <thead className="bg-gray-50 border-b">
            <tr className="text-left text-xs text-gray-500">
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">Pipe Name</th>
              <th className="px-3 py-2">3D Type</th>
              <th className="px-3 py-2 text-right">Ø1 pol.</th>
              <th className="px-3 py-2 text-right">Comp. m</th>
              <th className="px-3 py-2">Descritivo</th>
              <th className="px-3 py-2">Espec.</th>
              <th className="px-3 py-2">Cód. Padrão</th>
              <th className="px-3 py-2">Posição</th>
              <th className="px-3 py-2 text-right">Elev. m</th>
              <th className="px-3 py-2 text-right">Peso kg</th>
              <th className="px-3 py-2 text-right">Sup. m²</th>
              <th className="px-3 py-2">Isométrico</th>
              <th className="px-3 py-2">Texto Iso.</th>
              <th className="px-3 py-2">Spool</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={15} className="text-center py-8 text-gray-400">Carregando...</td></tr>
            )}
            {data?.data.map(item => (
              <tr key={item.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-1.5 font-mono text-xs text-blue-700">{item.material_code_alt}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{item.line_tag}</td>
                <td className="px-3 py-1.5 text-xs">{item.item_3d_type}</td>
                <td className="px-3 py-1.5 text-right text-xs">{item.diameter_nom_mm != null ? fmt(item.diameter_nom_mm / 25.4, 3) : '—'}</td>
                <td className="px-3 py-1.5 text-right text-xs">{fmt(item.pipe_length_m, 3)}</td>
                <td className="px-3 py-1.5 text-xs text-gray-600 max-w-xs truncate" title={item.description ?? ''}>{item.description}</td>
                <td className="px-3 py-1.5 text-xs">{item.material_spec}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{item.material_code_std}</td>
                <td className="px-3 py-1.5 text-xs">{item.position}</td>
                <td className="px-3 py-1.5 text-right text-xs">{fmt(item.elevation_m, 3)}</td>
                <td className="px-3 py-1.5 text-right text-xs">{fmt(item.weight_kg)}</td>
                <td className="px-3 py-1.5 text-right text-xs">{fmt(item.surface_area_m2, 4)}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{item.isometrico}</td>
                <td className="px-3 py-1.5 text-xs">{item.iso_text}</td>
                <td className="px-3 py-1.5 font-mono text-xs">{item.spool_number_raw}</td>
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
