import apiClient from './client'
import type { 
  InterfaceInfo, 
  InterfaceCreate, 
  InterfaceUpdate,
  XscnetInfo
} from '@/types/api'

export const networkApi = {
  // 创建网口
  create(data: InterfaceCreate): Promise<InterfaceInfo> {
    return apiClient.post('/networks', data)
  },

  // 更新网口（只更新描述）
  update(id: string, data: InterfaceUpdate): Promise<InterfaceInfo> {
    return apiClient.put(`/networks/${id}`, data)
  },

  // 删除网口
  delete(id: string): Promise<void> {
    return apiClient.delete(`/networks/${id}`, )
  },
}