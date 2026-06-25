import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getSpool } from '../api/spools'
import { getJoints } from '../api/joints'
import StatusBadge from '../components/ui/StatusBadge'
import type { SpoolStatus, JointStatus } from '../types'

const PROJECT_ID = 1

type Tab = 'overview' | 'milestones' | 'joints' | 'ncr'

const MILESTONES = [
  { key: 'dt_lib_fab',    label: 'Lib. Fabricação' },
  { key: 'dt_corte',      label: 'Corte' },
  { key: 'dt_acoplamento',label: 'Acoplamento' },
  { key: 'dt_soldagem',   label: 'Soldagem' },
  { key: 'dt_vs',         label: 'Inspeção Visual' },
  { key: 'dt_lib_end',    label: 'Lib. END' },
  { key: 'dt_tt',         label: 'Trat. Térmico' },
  { key: 'dt_pintura',    label: 'Pintura' },
  { key: 'dt_embarque',   label: 'Embarque' },
  { key: 'dt_lib_mon',    label: 'Lib. Montagem' },
  { key: 'dt_montagem',   label: 'Montagem' },
  { key: 'dt_sth',        label: 'STH' },
  { key: 'dt_lavagem',    label: 'Lavagem' },
]

function DateRow({ label, value }: { label: string; value: unknown }) {
  const d = value as string | null
  return (
    <div className="flex justify-between py-1.5 border-b border-gray-50 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={d ? 'text-gray-800 font-medium' : 'text-gray-300'}>
        {d ? d.slice(0, 10) : '—'}
      </span>
    </div>
  )
}

export default function SpoolDetailPage() {
  const { spoolId } = useParams<{ spoolId: string }>()
  const [tab, setTab] = useState<Tab>('overview')

  const { data: spool, isLoading } = useQuery({
    queryKey: ['spool', spoolId],
    queryFn: () => getSpool(PROJECT_ID, Number(spoolId)),
    enabled: !!spoolId,
  })

  const { data: joints } = useQuery({
    queryKey: ['spool-joints', spoolId],
    queryFn: () => getJoints(PROJECT_ID, { spool_id: Number(spoolId), page_size: 500 }),
    enabled: tab === 'joints' && !!spoolId,
  })

  if (isLoading) return <div className="p-6 text-gray-400">Carregando...</div>
  if (!spool) return <div className="p-6 text-red-400">Spool não encontrado</div>

  const TABS: { id: Tab; label: string }[] = [
    { id: 'overview',   label: 'Dados Gerais' },
    { id: 'milestones', label: 'Marcos' },
    { id: 'joints',     label: `Juntas (${spool.joints_total ?? 0})` },
    { id: 'ncr',        label: 'NCR' },
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/spools" className="text-xs text-blue-500 hover:underline">← Spools</Link>
          <h1 className="text-xl font-bold text-gray-800 font-mono mt-1">{spool.spool_key as string}</h1>
          <div className="flex gap-2 mt-1">
            <StatusBadge status={spool.status as SpoolStatus} type="spool" />
            {(spool.hold as boolean) && (
              <span className="bg-red-100 text-red-600 text-xs px-2 py-0.5 rounded font-medium">HOLD</span>
            )}
          </div>
        </div>
        <div className="text-right text-sm text-gray-500">
          <div>{spool.unit_code as string} / {spool.sub_unit as string}</div>
          <div className="font-mono text-xs mt-1">{spool.material as string} · Ø {spool.diameter_mm as number} mm</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors
              ${tab === t.id
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 space-y-0">
            {[
              ['Isométrico',   spool.isometrico],
              ['Spool',        spool.spool],
              ['Revisão',      spool.revision],
              ['Fabricante',   spool.manufacturer],
              ['Material',     spool.material],
              ['Diâmetro mm',  spool.diameter_mm],
              ['Espessura mm', spool.thickness_mm],
              ['Comprimento m',spool.length_m],
              ['Peso kg',      spool.weight_kg],
              ['Área m²',      spool.area_m2],
            ].map(([l, v]) => (
              <div key={String(l)} className="flex justify-between py-1.5 border-b border-gray-50 text-sm">
                <span className="text-gray-500">{String(l)}</span>
                <span className="text-gray-800 font-medium">{v != null ? String(v) : '—'}</span>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 space-y-0">
            {[
              ['Juntas Total',    spool.joints_total],
              ['Juntas Soldadas', spool.joints_welded],
              ['Juntas Liberadas',spool.joints_released],
              ['% Fabricação',   spool.pct_fab],
              ['% Montagem',     spool.pct_mon],
              ['Observações',    spool.obs],
            ].map(([l, v]) => (
              <div key={String(l)} className="flex justify-between py-1.5 border-b border-gray-50 text-sm">
                <span className="text-gray-500">{String(l)}</span>
                <span className="text-gray-800 font-medium">{v != null ? String(v) : '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Milestones */}
      {tab === 'milestones' && (
        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 max-w-sm">
          {MILESTONES.map(m => (
            <DateRow key={m.key} label={m.label} value={spool[m.key]} />
          ))}
        </div>
      )}

      {/* Juntas */}
      {tab === 'joints' && (
        <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr className="text-left text-xs text-gray-500">
                <th className="px-3 py-2">Junta</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Ø mm</th>
                <th className="px-3 py-2">Mat.</th>
                <th className="px-3 py-2 text-center">RX</th>
                <th className="px-3 py-2 text-center">LP</th>
                <th className="px-3 py-2 text-center">TT</th>
                <th className="px-3 py-2 text-center">Rep.</th>
                <th className="px-3 py-2">Soldagem</th>
                <th className="px-3 py-2">Liberação</th>
              </tr>
            </thead>
            <tbody>
              {joints?.data.map(j => (
                <tr key={j.id} className={`border-b border-gray-50 hover:bg-gray-50 ${j.is_repair ? 'bg-red-50' : ''}`}>
                  <td className="px-3 py-1.5 font-mono text-xs text-blue-700">{j.joint_key}</td>
                  <td className="px-3 py-1.5 text-xs">{j.joint_type}</td>
                  <td className="px-3 py-1.5">
                    <StatusBadge status={j.status as JointStatus} type="joint" />
                  </td>
                  <td className="px-3 py-1.5 text-right text-xs">{j.diameter_mm ?? '—'}</td>
                  <td className="px-3 py-1.5 font-mono text-xs">{j.material}</td>
                  <td className={`px-3 py-1.5 text-center text-xs font-bold
                    ${j.result_rx === 'A' ? 'text-green-600' : j.result_rx === 'R' ? 'text-red-600' : 'text-gray-400'}`}>
                    {j.result_rx ?? '—'}
                  </td>
                  <td className={`px-3 py-1.5 text-center text-xs font-bold
                    ${j.result_lp === 'A' ? 'text-green-600' : j.result_lp === 'R' ? 'text-red-600' : 'text-gray-400'}`}>
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
      )}

      {tab === 'ncr' && (
        <div className="bg-white rounded-lg border border-gray-100 shadow-sm p-4 text-gray-400 text-sm">
          NCR — integração com tabela nonconformances (em breve)
        </div>
      )}
    </div>
  )
}
