import type { SpoolStatus, JointStatus } from '../../types'

const SPOOL_COLORS: Record<SpoolStatus, string> = {
  NAO_INICIADO:   'bg-gray-100 text-gray-600',
  EM_FABRICACAO:  'bg-yellow-100 text-yellow-700',
  FABRICADO:      'bg-blue-100 text-blue-700',
  EM_CAMPO:       'bg-purple-100 text-purple-700',
  MONTADO:        'bg-indigo-100 text-indigo-700',
  TESTADO:        'bg-green-100 text-green-700',
}

const SPOOL_LABELS: Record<SpoolStatus, string> = {
  NAO_INICIADO:   'Não Iniciado',
  EM_FABRICACAO:  'Em Fabricação',
  FABRICADO:      'Fabricado',
  EM_CAMPO:       'Em Campo',
  MONTADO:        'Montado',
  TESTADO:        'Testado',
}

const JOINT_COLORS: Record<JointStatus, string> = {
  '01_NAO_INICIADA':       'bg-gray-100 text-gray-600',
  '03_AGUARD_ACOPLAMENTO': 'bg-orange-100 text-orange-700',
  '04_AGUARD_SOLDAGEM':    'bg-yellow-100 text-yellow-700',
  '09_AGUARD_VS':          'bg-cyan-100 text-cyan-700',
  '12_AGUARD_LP_PM':       'bg-teal-100 text-teal-700',
  '14_AGUARD_LIB_LOTE':    'bg-blue-100 text-blue-700',
  '15_AGUARD_RX_US':       'bg-violet-100 text-violet-700',
  '18_AGUARD_RX_REPARO':   'bg-red-100 text-red-700',
  '23_AGUARD_TT':          'bg-amber-100 text-amber-700',
  '30_LIBERADA':           'bg-green-100 text-green-700',
}

const JOINT_LABELS: Record<JointStatus, string> = {
  '01_NAO_INICIADA':       'Não Iniciada',
  '03_AGUARD_ACOPLAMENTO': 'Aguard. Acoplamento',
  '04_AGUARD_SOLDAGEM':    'Aguard. Soldagem',
  '09_AGUARD_VS':          'Aguard. VS',
  '12_AGUARD_LP_PM':       'Aguard. LP/PM',
  '14_AGUARD_LIB_LOTE':    'Aguard. Lib. Lote',
  '15_AGUARD_RX_US':       'Aguard. RX/US',
  '18_AGUARD_RX_REPARO':   'Aguard. RX Reparo',
  '23_AGUARD_TT':          'Aguard. TT',
  '30_LIBERADA':           'Liberada',
}

interface Props {
  status: SpoolStatus | JointStatus
  type?: 'spool' | 'joint'
}

export default function StatusBadge({ status, type = 'spool' }: Props) {
  const colors = type === 'spool'
    ? SPOOL_COLORS[status as SpoolStatus]
    : JOINT_COLORS[status as JointStatus]
  const label = type === 'spool'
    ? SPOOL_LABELS[status as SpoolStatus]
    : JOINT_LABELS[status as JointStatus]

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors ?? 'bg-gray-100 text-gray-600'}`}>
      {label ?? status}
    </span>
  )
}
