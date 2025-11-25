import apiClient from './client'
import type { ServerRequest, ServerDetailResponse, ServerUpdateRequest, BootEntriesResponse, MCRRequest } from '@/types/api'

export const deviceApi = {
  // 获取所有设备
  getAll(): Promise<ServerDetailResponse[]> {
    return apiClient.get('/api/devices')
  },

  // 获取设备详情
  getById(id: string): Promise<ServerDetailResponse> {
    return apiClient.get(`/api/devices/${id}`)
  },

  // 创建设备
  create(data: ServerRequest): Promise<ServerDetailResponse> {
    return apiClient.post('/api/devices', data)
  },

  // 更新设备
  update(id: string, data: ServerUpdateRequest): Promise<ServerDetailResponse> {
    return apiClient.put(`/api/devices/${id}`, data)
  },

  // 删除设备
  delete(id: string): Promise<void> {
    return apiClient.delete(`/api/devices/${id}`)
  },

  // 获取启动项（支持使用保存的凭据）
  getBootEntries(serverId: string): Promise<BootEntriesResponse> {
    return apiClient.get(`/api/devices/${serverId}/boot-entries`, { cache: false })
  },

  
  // 设置启动项（支持使用保存的凭据）
  setBootEntry(
    serverId: string, 
    bootId: string, 
    setDefault: boolean = false,
  ): Promise<void> {
    const params: any = { 
      boot_id: bootId,
      set_default: setDefault
    }
    return apiClient.post(`/api/devices/${serverId}/set-boot`, null, { params })
  },

  powerCycle(serverId: string): Promise<void> {
    return apiClient.post(`/api/devices/${serverId}/power-cycle`)
  },

  powerReset(serverId: string): Promise<void> {
    return apiClient.post(`/api/devices/${serverId}/power-reset`)
  },

  resetMcr(serverId: string, mcrFilePath: string, updateOptions: 'all' | 'fw' | 'no-fw' = 'all'): Promise<void> {
    const data: MCRRequest = {
      path: mcrFilePath,
      update_options: updateOptions
    }
    return apiClient.post(`/api/devices/${serverId}/update_mcr`, data)
  }
}