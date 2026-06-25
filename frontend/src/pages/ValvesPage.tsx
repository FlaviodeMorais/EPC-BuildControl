import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getValves } from '../api/valves'
import { getValveAvailability } from '../api/kpis'

const PROJECT_ID = 1

const AVAIL_COLORS = {
  AVAILABLE: 'bg-green-100 text-green-700',
  PARTIAL:   'bg-yellow-100 text-yellow-700',
  MISSING:   'bg-red-100 text-red-700',
}
const AVAIL_LABELS = {
  AVAILABLE: 'Disponível',
  PARTIAL:   'Parcial',
  MISSING:   'Faltando',
}

type ColFilter = { id: string; desc: string; dn: string; status: string }

function ColInput({ value, onChange, placeholder, align = 'left' }: {
  value: string; onChange: (v: string) => void; placeholder: string; align?: string
}) {
  return (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full mt-1 px-1.5 py-0.5 text-xs border border-gray-200 rounded bg-white text-gray-700
        focus:outline-none focus:border-blue-400 placeholder-gray-300 text-${align}`}
    />
  )
}

export default function ValvesPage() {
  const [availFilter, setAvailFilter] = useState('')
  const [col, setCol] = useState<ColFilter>({ id: '', desc: '', dn: '', status: '' })

  const { data: valves = [], isLoading } = useQuery({
    queryKey: ['valves', availFilter],
    queryFn: () => getValves(PROJECT_ID, availFilter || undefined),
  })
  const { data: summary = [] } = useQuery({
    queryKey: ['valve-summary'],
    queryFn: () => getValveAvailability(PROJECT_ID),
  })

  const totals = (summary as Record<string, unknown>[]).reduce(
    (acc, s) => ({
      planned:   acc.planned   + Number(s.qtd_prevista  ?? 0),
      received:  acc.received  + Number(s.qtd_recebida  ?? 0),
      wPlanned:  acc.wPlanned  + Number(s.peso_previsto ?? 0),
      wReceived: acc.wReceived + Number(s.peso_recebido ?? 0),
    }),
    { planned: 0, received: 0, wPlanned: 0, wReceived: 0 }
  )

  const filtered = useMemo(() => {
    return valves.filter(v => {
      if (col.id   && !String(v.valve_id_raw ?? '').toLowerCase().includes(col.id.toLowerCase())) return false
      if (col.desc && !String(v.description  ?? '').toLowerCase().includes(col.desc.toLowerCase())) return false
      if (col.dn   && !String(v.dn_mm        ?? '').includes(col.dn)) return false
      if (col.status) {
        const label = AVAIL_LABELS[v.availability ?? 'MISSING'].toLowerCase()
        if (!label.includes(col.status.toLowerCase())) return false
      }
      return true
    })
  }, [valves, col])

  const hasColFilter = Object.values(col).some(Boolean)

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Válvulas</h1>

      <div className="flex gap-3 flex-wrap">
        {(summary as Record<string, unknown>[]).map((s, i) => (
          <button key={i}
            onClick={() => setAvailFilter(availFilter === String(s.availability) ? '' : String(s.availability))}
            className={`rounded-lg px-4 py-2.5 text-sm font-medium transition border-2 ${
              availFilter === String(s.availability) ? 'border-current' : 'border-transparent'
            } ${AVAIL_COLORS[(s.availability as keyof typeof AVAIL_COLORS) ?? 'MISSING']}`}>
            {AVAIL_LABELS[(s.availability as keyof typeof AVAIL_LABELS)] ?? String(s.availability)}
            <span className="ml-2 font-bold">{String(s.items)}</span> itens
          </button>
        ))}
        {availFilter && (
          <button onClick={() => setAvailFilter('')}
            className="text-xs text-gray-500 hover:text-gray-800 px-2">✕ limpar</button>
        )}
      </div>

      <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-3 flex gap-6 text-sm">
        <div><span className="text-gray-500">Qtd Prevista:</span>{' '}
          <span className="font-semibold">{totals.planned.toLocaleString('pt-BR')}</span></div>
        <div><span className="text-gray-500">Qtd Recebida:</span>{' '}
          <span className="font-semibold text-green-700">{totals.received.toLocaleString('pt-BR')}</span></div>
        <div><span className="text-gray-500">Peso Previsto:</span>{' '}
          <span className="font-semibold">{totals.wPlanned.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} kg</span></div>
        <div><span className="text-gray-500">Peso Recebido:</span>{' '}
          <span className="font-semibold text-green-700">{totals.wReceived.toLocaleString('pt-BR', { maximumFractionDigits: 0 })} kg</span></div>
        <div className="ml-auto text-gray-400 self-center text-xs">
          {hasColFilter ? `${filtered.length} / ${valves.length}` : `${valves.length}`} itens
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr className="text-left text-xs text-gray-500">
              <th className="px-3 py-2">
                ID
                <ColInput value={col.id} onChange={v => setCol(c => ({...c, id: v}))} placeholder="filtrar..." />
              </th>
              <th className="px-3 py-2">
                Descrição
                <ColInput value={col.desc} onChange={v => setCol(c => ({...c, desc: v}))} placeholder="filtrar..." />
              </th>
              <th className="px-3 py-2 text-right">DN mm</th>
              <th className="px-3 py-2 text-right">Peso Unit.</th>
              <th className="px-3 py-2 text-right">Qtd Prev.</th>
              <th className="px-3 py-2 text-right">Qtd Receb.</th>
              <th className="px-3 py-2 text-right">Reservado</th>
              <th className="px-3 py-2 text-right">Emitido</th>
              <th className="px-3 py-2 text-center">
                Status
                <ColInput value={col.status} onChange={v => setCol(c => ({...c, status: v}))} placeholder="filtrar..." align="center" />
              </th>
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={9} className="text-center py-8 text-gray-400">Carregando...</td></tr>}
            {!isLoading && filtered.length === 0 && (
              <tr><td colSpan={9} className="text-center py-8 text-gray-400">Nenhum resultado</td></tr>
            )}
            {filtered.map(v => (
              <tr key={v.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-3 py-1.5 font-mono text-xs">{v.valve_id_raw}</td>
                <td className="px-3 py-1.5 text-xs text-gray-700 max-w-sm truncate" title={v.description}>{v.description}</td>
                <td className="px-3 py-1.5 text-right text-xs">{v.dn_mm ?? '—'}</td>
                <td className="px-3 py-1.5 text-right text-xs">{v.unit_weight_kg?.toLocaleString('pt-BR') ?? '—'}</td>
                <td className="px-3 py-1.5 text-right">{v.qty_planned?.toLocaleString('pt-BR') ?? '—'}</td>
                <td className="px-3 py-1.5 text-right text-green-700 font-medium">{v.qty_received?.toLocaleString('pt-BR') ?? '—'}</td>
                <td className="px-3 py-1.5 text-right text-blue-600">{v.qty_reserved?.toLocaleString('pt-BR') ?? '—'}</td>
                <td className="px-3 py-1.5 text-right">{v.qty_issued?.toLocaleString('pt-BR') ?? '—'}</td>
                <td className="px-3 py-1.5 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded font-medium ${AVAIL_COLORS[v.availability ?? 'MISSING']}`}>
                    {AVAIL_LABELS[v.availability ?? 'MISSING']}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
