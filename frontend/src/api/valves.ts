import api from './client'

export interface Valve {
  id: number
  valve_id_raw: string
  description: string
  dn_mm: number
  unit_weight_kg: number
  qty_planned: number
  qty_received: number
  qty_reserved: number
  qty_issued: number
  weight_planned_kg: number
  weight_received_kg: number
  availability: 'AVAILABLE' | 'PARTIAL' | 'MISSING'
}

export const getValves = (projectId: number, availability?: string) =>
  api.get<Valve[]>(`/projects/${projectId}/valves`, {
    params: availability ? { availability } : {},
  }).then(r => r.data)
