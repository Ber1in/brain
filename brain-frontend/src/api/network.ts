import apiClient from './client'
import type { 
  InterfaceInfo, 
  InterfaceCreate, 
  InterfaceUpdate,
  InterfaceDelete 
} from '@/types/api'

export const networkApi = {
  // 获取所有网口
  getAll(): Promise<InterfaceInfo[]> {
    return apiClient.get('/networks')
  },

  // 根据ID获取单个网口
  getById(id: string): Promise<InterfaceInfo> {
    return apiClient.get(`/networks/${id}`)
  },

  // 创建网口
  create(data: InterfaceCreate): Promise<InterfaceInfo> {
    return apiClient.post('/networks', data)
  },

  // 更新网口（只更新描述）
  update(data: InterfaceUpdate): Promise<InterfaceInfo> {
    return apiClient.put('/networks', data)
  },

  // 删除网口
  delete(id: string, mv200Id: string): Promise<void> {
    return apiClient.delete('/networks', {
      data: {
        id,
        mv200_id: mv200Id
      }
    })
  },
}