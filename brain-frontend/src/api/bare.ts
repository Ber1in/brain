import apiClient from './client'
import type { BareMetalServer, BareMetalServerCreate, BareMetalServerUpdate, BootEntriesResponse } from '@/types/api'

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

  getBootEntries(serverId: string, user: string, pwd: string): Promise<BootEntriesResponse> {
    return apiClient.get(`/bare-metals/${serverId}/boot-entries`, {
      params: { user, pwd }
    })
  },

  setBootEntry(serverId: string, bootId: string, user: string, pwd: string): Promise<void> {
    return apiClient.post(`/bare-metals/${serverId}/set-boot`, null, {
      params: { boot_id: bootId, user, pwd }
    })
  },

  powerCycle(serverId: string): Promise<void> {
    return apiClient.post(`/bare-metals/${serverId}/power-cycle`)
  },

  powerReset(serverId: string): Promise<void> {
    return apiClient.post(`/bare-metals/${serverId}/power-reset`)
  }
}