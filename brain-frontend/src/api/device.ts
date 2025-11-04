import apiClient from './client'
import type { ServerRequest, ServerDetailResponse, ServerUpdateRequest, TagsRequest, TagsResponse } from '@/types/api'

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

}