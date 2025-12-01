import apiClient from './client'
import type { ServerRequest, ServerDetailResponse, ServerUpdateRequest, BootEntriesResponse, MCRRequest, ResetFwRequest } from '@/types/api'

export const deviceApi = {
  // 获取所有设备
  getAll(): Promise<ServerDetailResponse[]> {
    return apiClient.get('/api/servers')
  },

  // 获取设备详情
  getById(id: string): Promise<ServerDetailResponse> {
    return apiClient.get(`/api/servers/${id}`)
  },

  // 创建设备
  create(data: ServerRequest): Promise<ServerDetailResponse> {
    return apiClient.post('/api/servers', data)
  },

  // 更新设备
  update(id: string, data: ServerUpdateRequest): Promise<ServerDetailResponse> {
    return apiClient.put(`/api/servers/${id}`, data)
  },

  // 删除设备
  delete(id: string): Promise<void> {
    return apiClient.delete(`/api/servers/${id}`)
  },

  // 获取启动项（支持使用保存的凭据）
  getBootEntries(serverId: string): Promise<BootEntriesResponse> {
    return apiClient.get(`/api/servers/${serverId}/boot-entries`, { cache: false })
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
    return apiClient.post(`/api/servers/${serverId}/set-boot`, null, { params })
  },

  powerCycle(serverId: string): Promise<void> {
    return apiClient.post(`/api/servers/${serverId}/power-cycle`)
  },

  powerReset(serverId: string): Promise<void> {
    return apiClient.post(`/api/servers/${serverId}/power-reset`)
  },

  upgradeMcr(serverId: string, mcrFilePath: string, updateOptions: 'all' | 'fw' | 'no-fw' = 'all'): Promise<void> {
    const data: MCRRequest = {
      path: mcrFilePath,
      update_options: updateOptions
    }
    return apiClient.post(`/api/servers/${serverId}/update_mcr`, data)
  },

  resetFw(serverId: string, mcrFilePath: string): Promise<void> {
    const data: ResetFwRequest = {
      path: mcrFilePath
    }
    return apiClient.post(`/api/servers/${serverId}/reset_fw`, data)
  },

  focusServer(serverId: string, focus: boolean): Promise<void> {
    return apiClient.patch(`/api/servers/${serverId}/focus`, { focus })
  }
}