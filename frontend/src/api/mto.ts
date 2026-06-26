import api from './client'
import type { PagedResponse } from '../types'

export interface MtoItem {
  id: number
  material_code_alt: string
  line_tag: string
  item_3d_name: string
  item_3d_type: string
  diameter_nom_mm: number | null
  diameter_sec_mm: number | null
  diameter_ter_mm: number | null
  pipe_length_m: number | null
  description: string
  material_spec: string
  material_code_std: string
  position: string
  elevation_m: number | null
  weight_kg: number | null
  surface_area_m2: number | null
  isometrico: string
  iso_text: string
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
