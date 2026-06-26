import api from './client'
import type { PagedResponse } from '../types'

export interface MtoItem {
  id: number
  line_tag: string | null
  item_3d_type: string | null
  diameter_nom_mm: number | null
  pipe_length_m: number | null
  description: string | null
  material_spec: string | null
  material_code_std: string | null
  material_code_alt: string | null
  position: string | null
  elevation_m: number | null
  weight_kg: number | null
  surface_area_m2: number | null
  isometrico: string | null
  iso_text: string | null
  spool_number_raw: string | null
}

interface MtoFilters {
  item_3d_type?: string
  isometrico?: string
  search?: string
  page?: number
  page_size?: number
}

export const getMtoItems = (projectId: number, filters: MtoFilters = {}) =>
  api.get<PagedResponse<MtoItem>>(`/projects/${projectId}/mto-items`, { params: filters })
    .then(r => r.data)

export const getMtoTypes = (projectId: number) =>
  api.get<string[]>(`/projects/${projectId}/mto-items/types`).then(r => r.data)
