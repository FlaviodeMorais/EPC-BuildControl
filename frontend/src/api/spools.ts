import api from './client'
import type { PagedResponse, Spool } from '../types'

interface SpoolFilters {
  status?: string
  unit_code?: string
  hold?: boolean
  search?: string
  page?: number
  page_size?: number
}

export const getSpools = (projectId: number, filters: SpoolFilters = {}) =>
  api.get<PagedResponse<Spool>>(`/projects/${projectId}/spools`, { params: filters })
    .then(r => r.data)

export const getSpool = (projectId: number, spoolId: number) =>
  api.get<Spool & Record<string, unknown>>(`/projects/${projectId}/spools/${spoolId}`)
    .then(r => r.data)

export const updateSpool = (projectId: number, spoolId: number, payload: Partial<Spool>) =>
  api.patch(`/projects/${projectId}/spools/${spoolId}`, payload).then(r => r.data)
