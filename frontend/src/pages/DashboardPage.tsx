import { useQuery } from '@tanstack/react-query'
import { getOverview, getByUnit, getSCurve } from '../api/kpis'
import KpiCard from '../components/ui/KpiCard'
import SpoolStatusDonut from '../components/charts/SpoolStatusDonut'
import SCurveChart from '../components/charts/SCurveChart'

const PROJECT_ID = 1

function fmt(n: number) {
  return n?.toLocaleString('pt-BR') ?? '—'
}

function pct(a: number, b: number) {
  return b > 0 ? `${((a / b) * 100).toFixed(1)}%` : '0%'
}

export default function DashboardPage() {
  const { data: kpi } = useQuery({ queryKey: ['kpi-overview'], queryFn: () => getOverview(PROJECT_ID) })
  const { data: curve = [] } = useQuery({ queryKey: ['s-curve'], queryFn: () => getSCurve(PROJECT_ID) })
  const { data: byUnit = [] } = useQuery({ queryKey: ['by-unit'], queryFn: () => getByUnit(PROJECT_ID) })

  const sp = kpi?.spools
  const jo = kpi?.joints

  const donutData = sp ? [
    { name: 'Não Iniciado',  value: sp.nao_iniciado },
    { name: 'Em Fabricação', value: sp.em_fabricacao },
    { name: 'Fabricado',     value: sp.fabricado },
    { name: 'Em Campo',      value: sp.em_campo },
    { name: 'Montado',       value: sp.montado },
    { name: 'Testado',       value: sp.testado },
  ] : []

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">Dashboard — UGH · TOYO</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard label="Total Spools"   value={fmt(sp?.total_spools ?? 0)} color="blue" />
        <KpiCard label="Em Hold"        value={fmt(sp?.em_hold ?? 0)} color="red" />
        <KpiCard label="Peso Total (t)" value={fmt(Math.round((sp?.peso_total_kg ?? 0) / 1000))} color="gray" />
        <KpiCard label="Juntas Total"   value={fmt(jo?.total ?? 0)} color="blue" />
        <KpiCard label="Juntas Liberadas"
          value={fmt(jo?.liberadas ?? 0)}
          sub={pct(jo?.liberadas ?? 0, jo?.total ?? 0)}
          color="green" />
        <KpiCard label="Reparos"        value={fmt(jo?.reparos ?? 0)} color="yellow" />
        <KpiCard label="Com Tratamento Térmico" value={fmt(jo?.com_tt ?? 0)} color="gray" />
        <KpiCard label="Fabricados"
          value={fmt(sp?.fabricado ?? 0)}
          sub={pct(sp?.fabricado ?? 0, sp?.total_spools ?? 0)}
          color="green" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">Status dos Spools</h2>
          <SpoolStatusDonut data={donutData} />
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">Curva S — Juntas</h2>
          <SCurveChart data={curve as never[]} />
        </div>
      </div>

      {/* Por Unidade */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-100 p-4">
        <h2 className="text-sm font-semibold text-gray-600 mb-3">Progresso por Unidade</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b">
              <th className="pb-2">Unidade</th>
              <th className="pb-2 text-right">Spools</th>
              <th className="pb-2 text-right">Fabricado</th>
              <th className="pb-2 text-right">Montado</th>
              <th className="pb-2 text-right">Juntas</th>
              <th className="pb-2 text-right">Lib.</th>
              <th className="pb-2 text-right">Peso (t)</th>
            </tr>
          </thead>
          <tbody>
            {(byUnit as never[]).map((r: Record<string, unknown>, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-1.5 font-mono text-xs">{String(r.unit)}/{String(r.sub_unit)}</td>
                <td className="py-1.5 text-right">{fmt(Number(r.spools))}</td>
                <td className="py-1.5 text-right text-blue-600">{fmt(Number(r.fabricado))}</td>
                <td className="py-1.5 text-right text-green-600">{fmt(Number(r.montado))}</td>
                <td className="py-1.5 text-right">{fmt(Number(r.juntas))}</td>
                <td className="py-1.5 text-right text-green-600">{fmt(Number(r.juntas_lib))}</td>
                <td className="py-1.5 text-right">{fmt(Math.round(Number(r.peso_kg) / 1000))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
