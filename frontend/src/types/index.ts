export type SpoolStatus =
  | 'NAO_INICIADO' | 'EM_FABRICACAO' | 'FABRICADO'
  | 'EM_CAMPO' | 'MONTADO' | 'TESTADO'

export type JointStatus =
  | '01_NAO_INICIADA' | '03_AGUARD_ACOPLAMENTO' | '04_AGUARD_SOLDAGEM'
  | '09_AGUARD_VS' | '12_AGUARD_LP_PM' | '14_AGUARD_LIB_LOTE'
  | '15_AGUARD_RX_US' | '18_AGUARD_RX_REPARO' | '23_AGUARD_TT'
  | '30_LIBERADA'

export type Material = 'AC' | 'AL' | 'AI' | 'ST'

export interface Spool {
  id: number
  spool_key: string
  status: SpoolStatus
  material: Material
  diameter_mm: number
  weight_kg: number
  joints_total: number
  joints_welded: number
  joints_released: number
  hold: boolean
  pct_fab: number
  pct_mon: number
  dt_embarque: string | null
  dt_montagem: string | null
  unit_code?: string
}

export interface Joint {
  id: number
  joint_key: string
  joint_type: string
  diameter_mm: number
  material: Material
  status: JointStatus
  is_repair: boolean
  requires_tt: boolean
  dt_soldagem: string | null
  dt_lib_end: string | null
  result_rx: string | null
  result_lp: string | null
  welder_root: string | null
  welder_fill: string | null
}

export interface KpiOverview {
  spools: {
    total_spools: number
    testado: number
    montado: number
    em_campo: number
    fabricado: number
    em_fabricacao: number
    nao_iniciado: number
    em_hold: number
    peso_total_kg: number
    comprimento_total_m: number
    juntas_total: number
    juntas_soldadas: number
    juntas_liberadas: number
  }
  joints: {
    total: number
    liberadas: number
    reparos: number
    com_tt: number
    com_ut: number
  }
}

export interface PagedResponse<T> {
  total: number
  page: number
  page_size: number
  data: T[]
}
