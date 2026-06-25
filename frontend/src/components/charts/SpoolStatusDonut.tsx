import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = ['#6b7280','#f59e0b','#3b82f6','#8b5cf6','#6366f1','#10b981']

interface Props {
  data: { name: string; value: number }[]
}

export default function SpoolStatusDonut({ data }: Props) {
  const filled = data.filter(d => d.value > 0)
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={filled} dataKey="value" nameKey="name"
          cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={2}>
          {filled.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => v.toLocaleString('pt-BR')} />
        <Legend iconType="circle" iconSize={8} />
      </PieChart>
    </ResponsiveContainer>
  )
}
