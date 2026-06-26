import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

interface SCurvePoint {
  snapshot_dt: string
  cortado: number
  acoplado: number
  soldado: number
  liberado: number
}

interface Props { data: SCurvePoint[] }

export default function SCurveChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="snapshot_dt" tick={{ fontSize: 11 }}
          tickFormatter={d => d?.slice(5) ?? ''} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend iconType="circle" iconSize={8} />
        <Line type="monotone" dataKey="cortado"  stroke="#f59e0b" dot={false} name="Cortado" />
        <Line type="monotone" dataKey="acoplado" stroke="#a855f7" dot={false} name="Acoplado" />
        <Line type="monotone" dataKey="soldado"  stroke="#3b82f6" dot={false} name="Soldado" />
        <Line type="monotone" dataKey="liberado" stroke="#10b981" dot={false} name="Liberado" />
      </LineChart>
    </ResponsiveContainer>
  )
}
