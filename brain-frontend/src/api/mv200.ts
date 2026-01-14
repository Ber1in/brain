import apiClient from './client'
import type { MVServer, MVServerCreate, MVServerUpdate, MCRRequest, InterfaceCreate, InterfaceInfo, OvsflowRequest } from '@/types/api'

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
      path: mcrFilePath,
      update_options: '--force --ovs-dpdk --spdk --yun-upgrade-option "--dpu-blk-oprom --best-try" --dpuagent'
    }
    return apiClient.post(`/mv-servers/${serverId}/update_mcr`, data)
  },

  createXsc(mv200_id: string, data: InterfaceCreate): Promise<InterfaceInfo> {
    return apiClient.post(`/xsc/${mv200_id}`, data)
  },

  addXscOvsFlow(mv200_id: string, uuid: number, data: OvsflowRequest): Promise<void> {
    return apiClient.post(`/xsc/${mv200_id}/${uuid}/flowtables`, data)
  },

  removeXscOvsFlow(mv200_id: string, uuid: number): Promise<void> {
    return apiClient.delete(`/xsc/${mv200_id}/${uuid}/flowtables`)
  },

  deleteXsc(mv200_id: string, uuid: number): Promise<void> {
    return apiClient.delete(`/xsc/${mv200_id}/${uuid}`)
  },
}