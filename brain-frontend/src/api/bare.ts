import apiClient from './client'
import type { BareMetalServer, BareMetalServerCreate, BareMetalServerUpdate } from '@/types/api'

export const bareApi = {
  getAll(): Promise<BareMetalServer[]> {
    return apiClient.get('/bare-metals')
  },

  getById(id: string): Promise<BareMetalServer> {
    return apiClient.get(`/bare-metals/${id}`)
  },

  create(data: BareMetalServerCreate): Promise<BareMetalServer> {
    return apiClient.post('/bare-metals', data)
  },

  update(id: string, data: BareMetalServerUpdate): Promise<BareMetalServer> {
    return apiClient.put(`/bare-metals/${id}`, data)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`/bare-metals/${id}`)
  },
}
