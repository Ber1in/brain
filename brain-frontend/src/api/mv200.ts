import apiClient from './client'
import type { MVServer, MVServerCreate, MVServerUpdate } from '@/types/api'

export const mv200Api = {
  getAll(): Promise<MVServer[]> {
    return apiClient.get('/mv-servers')
  },

  getById(id: string): Promise<MVServer> {
    return apiClient.get(`/mv-servers/${id}`)
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
}
