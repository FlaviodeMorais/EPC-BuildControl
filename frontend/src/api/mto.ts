import api from './client'
import type { PagedResponse } from '../types'

export interface MtoItem {
  id: number
  item_3d_name: string
  item_3d_type: string
  description: string
  material_code_alt: string
  material_code_std: string
  material_spec: string
  diameter_nom_mm: number
  weight_kg: number
  isometrico: string
  spool_number_raw: string
  scope: string
  zone: string
}

interface MtoFilters {
  item_3d_type?: string
  isometrico?: string
  scope?: string
  search?: string
  page?: number
  page_size?: number
}

export const getMtoItems = (projectId: number, filters: MtoFilters = {}) =>
  api.get<PagedResponse<MtoItem>>(`/projects/${projectId}/mto-items`, { params: filters })
    .then(r => r.data)
