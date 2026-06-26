import { useQuery } from '@tanstack/react-query'
import { getOverview, getByUnit, getSCurve } from '../api/kpis'
import SpoolStatusDonut from '../components/charts/SpoolStatusDonut'
import SCurveChart from '../components/charts/SCurveChart'

const PID = 1
const fmt = (n: number) => n?.toLocaleString('pt-BR') ?? '—'
const pct = (a: number, b: number) => b > 0 ? ((a / b) * 100).toFixed(1) : '0'

function ProgressBar({ value, max, color = 'bg-blue-500' }: { value: number; max: number; color?: string }) {
  const p = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="w-full bg-gray-100 rounded-full h-1.5 overflow-hidden">
      <div className={`${color} h-full rounded-full transition-all`} style={{ width: `${p}%` }} />
    </div>
  )
}

function KpiCard({ label, value, sub, color = 'gray' }: { label: string; value: string | number; sub?: string; color?: string }) {
  const colors: Record<string, string> = {
    blue: 'text-blue-600', green: 'text-green-600', red: 'text-red-500',
    yellow: 'text-yellow-600', gray: 'text-gray-800',
  }
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${colors[color]}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function DashboardPage() {
  const { data: kpi } = useQuery({ queryKey: ['kpi-overview'], queryFn: () => getOverview(PID) })
  const { data: curve = [] } = useQuery({ queryKey: ['s-curve'],   queryFn: () => getSCurve(PID) })
  const { data: byUnit = [] } = useQuery({ queryKey: ['by-unit'],  queryFn: () => getByUnit(PID) })

  const sp = kpi?.spools as Record<string, number> | undefined
  const jo = kpi?.joints as Record<string, number> | undefined

  const donutData = sp ? [
    { name: 'Não Iniciado',  value: sp.nao_iniciado },
    { name: 'Em Fabricação', value: sp.em_fabricacao },
    { name: 'Fabricado',     value: sp.fabricado },
    { name: 'Em Campo',      value: sp.em_campo },
    { name: 'Montado',       value: sp.montado },
    { name: 'Testado',       value: sp.testado },
  ] : []

  const spTotal = sp?.total_spools ?? 0
  const joTotal = jo?.total ?? 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Dashboard — UGH · TOYO</h1>
        <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">Atualizado em tempo real</span>
      </div>

      {/* KPI Row 1 — Spools */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Spools</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Total"      value={fmt(spTotal)} color="blue" />
          <KpiCard label="Fabricado"  value={fmt(sp?.fabricado ?? 0)}
            sub={`${pct(sp?.fabricado ?? 0, spTotal)}% do total`} color="green" />
          <KpiCard label="Montado"    value={fmt((sp?.montado ?? 0) + (sp?.testado ?? 0))}
            sub={`${pct((sp?.montado ?? 0) + (sp?.testado ?? 0), spTotal)}%`} color="blue" />
          <KpiCard label="Em Hold"    value={fmt(sp?.em_hold ?? 0)} color="red" />
        </div>
        {sp && (
          <div className="mt-2 bg-white rounded-lg border border-gray-100 p-3 flex gap-4 items-center">
            <div className="flex-1 space-y-1">
              <div className="flex justify-between text-xs text-gray-500">
                <span>Fabricação</span>
                <span>{pct(sp.fabricado + sp.em_campo + sp.montado + sp.testado, spTotal)}%</span>
              </div>
              <ProgressBar value={sp.fabricado + sp.em_campo + sp.montado + sp.testado} max={spTotal} color="bg-blue-500" />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>Montagem</span>
                <span>{pct(sp.montado + sp.testado, spTotal)}%</span>
              </div>
              <ProgressBar value={sp.montado + sp.testado} max={spTotal} color="bg-green-500" />
            </div>
            <div className="text-right text-xs text-gray-400 min-w-fit">
              <p>{fmt(Math.round((sp.peso_total_kg ?? 0) / 1000))} t</p>
              <p className="text-gray-300">peso total</p>
            </div>
          </div>
        )}
      </div>

      {/* KPI Row 2 — Juntas */}
      <div>
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Juntas de Solda</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiCard label="Total"    value={fmt(joTotal)} color="blue" />
          <KpiCard label="Soldadas" value={fmt(jo?.soldadas ?? 0)}
            sub={`${pct(jo?.soldadas ?? 0, joTotal)}%`} color="blue" />
          <KpiCard label="Liberadas" value={fmt(jo?.liberadas ?? 0)}
            sub={`${pct(jo?.liberadas ?? 0, joTotal)}%`} color="green" />
          <KpiCard label="Com TT"   value={fmt(jo?.com_tt ?? 0)}
            sub={`Feito: ${fmt(jo?.com_tt_feito ?? 0)}`} color="gray" />
        </div>
        {jo && (
          <div className="mt-2 bg-white rounded-lg border border-gray-100 p-3 space-y-2">
            {[
              { label: 'Cortadas',   value: jo.cortadas,   color: 'bg-orange-400' },
              { label: 'Acopladas',  value: jo.acopladas,  color: 'bg-purple-400' },
              { label: 'Soldadas',   value: jo.soldadas,   color: 'bg-blue-500' },
              { label: 'Liberadas',  value: jo.liberadas,  color: 'bg-green-500' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div className="flex justify-between text-xs text-gray-500 mb-0.5">
                  <span>{label}</span>
                  <span>{fmt(value)} ({pct(value, joTotal)}%)</span>
                </div>
                <ProgressBar value={value} max={joTotal} color={color} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">Status dos Spools</h2>
          <SpoolStatusDonut data={donutData} />
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">Curva S — Juntas</h2>
          <SCurveChart data={curve as never[]} />
        </div>
      </div>

      {/* Por Unidade */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h2 className="text-sm font-semibold text-gray-600">Progresso por Unidade</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b text-xs text-gray-500">
            <tr>
              <th className="px-4 py-2 text-left">Unidade</th>
              <th className="px-4 py-2 text-right">Spools</th>
              <th className="px-4 py-2 text-right">Fabricado</th>
              <th className="px-4 py-2 text-right">Montado</th>
              <th className="px-4 py-2">Avanço Fab.</th>
              <th className="px-4 py-2 text-right">Juntas</th>
              <th className="px-4 py-2 text-right">Lib.</th>
              <th className="px-4 py-2 text-right">Peso (t)</th>
            </tr>
          </thead>
          <tbody>
            {(byUnit as Record<string, unknown>[]).map((r, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs font-medium">{String(r.unit)}/{String(r.sub_unit)}</td>
                <td className="px-4 py-2 text-right text-xs">{fmt(Number(r.spools))}</td>
                <td className="px-4 py-2 text-right text-blue-600 text-xs">{fmt(Number(r.fabricado))}</td>
                <td className="px-4 py-2 text-right text-green-600 text-xs">{fmt(Number(r.montado))}</td>
                <td className="px-4 py-2 w-32">
                  <ProgressBar value={Number(r.fabricado)} max={Number(r.spools)} color="bg-blue-400" />
                </td>
                <td className="px-4 py-2 text-right text-xs">{fmt(Number(r.juntas))}</td>
                <td className="px-4 py-2 text-right text-green-600 text-xs">{fmt(Number(r.juntas_lib))}</td>
                <td className="px-4 py-2 text-right text-xs">{fmt(Math.round(Number(r.peso_kg) / 1000))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
