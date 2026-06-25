import api from './client'
import type { KpiOverview } from '../types'

export const getOverview = (projectId: number) =>
  api.get<KpiOverview>(`/projects/${projectId}/kpis/overview`).then(r => r.data)

export const getByUnit = (projectId: number) =>
  api.get<unknown[]>(`/projects/${projectId}/kpis/by-unit`).then(r => r.data)

export const getHolds = (projectId: number) =>
  api.get<unknown[]>(`/projects/${projectId}/kpis/holds`).then(r => r.data)

export const getSCurve = (projectId: number) =>
  api.get<unknown[]>(`/projects/${projectId}/kpis/s-curve`).then(r => r.data)

export const getValveAvailability = (projectId: number) =>
  api.get<unknown[]>(`/projects/${projectId}/kpis/valve-availability`).then(r => r.data)
