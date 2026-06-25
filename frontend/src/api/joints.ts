import api from './client'
import type { PagedResponse, Joint } from '../types'

interface JointFilters {
  spool_id?: number
  status?: string
  material?: string
  is_repair?: boolean
  requires_tt?: boolean
  search?: string
  page?: number
  page_size?: number
}

export const getJoints = (projectId: number, filters: JointFilters = {}) =>
  api.get<PagedResponse<Joint>>(`/projects/${projectId}/joints`, { params: filters })
    .then(r => r.data)

export const getJoint = (projectId: number, jointId: number) =>
  api.get<Joint & Record<string, unknown>>(`/projects/${projectId}/joints/${jointId}`)
    .then(r => r.data)
