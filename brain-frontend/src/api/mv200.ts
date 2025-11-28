import apiClient from './client'
import type { MVServer, MVServerCreate, MVServerUpdate, MCRRequest } from '@/types/api'

export const mv200Api = {
  getAll(): Promise<MVServer[]> {
    return apiClient.get('/mv-servers')
  },

  getById(id: string): Promise<MVServer> {
    return apiClient.get(`/mv-servers/${id}`, { cache: false })
  },

  create(data: MVServerCreate): Promise<MVServer> {
    return apiClient.post('/mv-servers', data)
  },

  update(id: string, data: MVServerUpdate): Promise<MVServer> {
    return apiClient.put(`/mv-servers/${id}`, data)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`/mv-servers/${id}`)
  },

  upgradeMcr(serverId: string, mcrFilePath: string): Promise<void> {
    const data: MCRRequest = {
      path: mcrFilePath
    }
    return apiClient.post(`/mv-servers/${serverId}/update_mcr`, data)
  },

}