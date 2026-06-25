import { useQuery } from '@tanstack/react-query'
import api from '../api/client'

const PID = 1

function badge(rate: number) {
  if (rate === 0) return 'bg-green-100 text-green-700'
  if (rate < 5)   return 'bg-yellow-100 text-yellow-700'
  return 'bg-red-100 text-red-700'
}

export default function WeldersPage() {
  const { data = [], isLoading } = useQuery({
    queryKey: ['welders'],
    queryFn: () => api.get(`/projects/${PID}/welders`).then(r => r.data),
  })

  const total = data.reduce((s: number, w: Record<string, number>) => s + (w.total_joints ?? 0), 0)
  const disqualified = data.filter((w: Record<string, unknown>) => w.disqualified).length

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">Soldadores</h1>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Soldadores', value: data.length, color: 'text-blue-600' },
          { label: 'Juntas Atribuídas', value: total.toLocaleString('pt-BR'), color: 'text-gray-800' },
          { label: 'Desqualificados', value: disqualified, color: 'text-red-600' },
        ].map(c => (
          <div key={c.label} className="bg-white rounded-lg border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-500">{c.label}</p>
            <p className={`text-2xl font-bold mt-1 ${c.color}`}>{c.value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b text-xs text-gray-500">
            <tr>
              <th className="px-4 py-2 text-left">SIN</th>
              <th className="px-4 py-2 text-left">Nome</th>
              <th className="px-4 py-2 text-left">Empresa</th>
              <th className="px-4 py-2 text-left">Processo</th>
              <th className="px-4 py-2 text-right">Juntas</th>
              <th className="px-4 py-2 text-right">Reparos</th>
              <th className="px-4 py-2 text-center">Índice Reparo</th>
              <th className="px-4 py-2 text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={8} className="text-center py-8 text-gray-400">Carregando...</td></tr>
            )}
            {(data as Record<string, unknown>[]).map((w, i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="px-4 py-2 font-mono text-xs">{String(w.sin ?? '—')}</td>
                <td className="px-4 py-2 font-medium">{String(w.name ?? '—')}</td>
                <td className="px-4 py-2 text-gray-500 text-xs">{String(w.company ?? '—')}</td>
                <td className="px-4 py-2 text-xs">{String(w.process ?? '—')}</td>
                <td className="px-4 py-2 text-right">{String(w.total_joints ?? 0)}</td>
                <td className="px-4 py-2 text-right text-red-500">{String(w.reparos ?? 0)}</td>
                <td className="px-4 py-2 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge(Number(w.repair_rate ?? 0))}`}>
                    {Number(w.repair_rate ?? 0).toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-2 text-center">
                  {w.disqualified
                    ? <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Desqualificado</span>
                    : <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">Ativo</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
