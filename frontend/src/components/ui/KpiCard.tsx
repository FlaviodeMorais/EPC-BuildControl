interface Props {
  label: string
  value: string | number
  sub?: string
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'gray'
}

const BORDER: Record<string, string> = {
  blue:   'border-l-blue-500',
  green:  'border-l-green-500',
  yellow: 'border-l-yellow-500',
  red:    'border-l-red-500',
  gray:   'border-l-gray-400',
}

export default function KpiCard({ label, value, sub, color = 'blue' }: Props) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-100 border-l-4 ${BORDER[color]} p-4`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-800 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}
