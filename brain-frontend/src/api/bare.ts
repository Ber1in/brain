import apiClient from './client'
import type { 
  BareMetalServer, 
  BareMetalServerCreate, 
  BareMetalServerUpdate, 
  BootEntriesResponse,
  CredentialsVerifyResponse,
  ServerCredentials 
} from '@/types/api'

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

  // 获取启动项（支持使用保存的凭据）
  getBootEntries(
    serverId: string, 
    useSaved: boolean = false,
    user?: string, 
    pwd?: string
  ): Promise<BootEntriesResponse> {
    const params: any = { use_saved: useSaved }
    if (!useSaved && user && pwd) {
      params.user = user
      params.pwd = pwd
    }
    
    return apiClient.get(`/bare-metals/${serverId}/boot-entries`, { params })
  },

  // 设置启动项（支持使用保存的凭据）
  setBootEntry(
    serverId: string, 
    bootId: string, 
    useSaved: boolean = false,
    setDefault: boolean = false,
    user?: string, 
    pwd?: string
  ): Promise<void> {
    const params: any = { 
      boot_id: bootId,
      use_saved: useSaved,
      set_default: setDefault
    }
    if (!useSaved && user && pwd) {
      params.user = user
      params.pwd = pwd
    }
    
    return apiClient.post(`/bare-metals/${serverId}/set-boot`, null, { params })
  },

  // 验证凭据
  verifyCredentials(
    serverId: string, 
    useSaved: boolean = false,
    user?: string, 
    pwd?: string
  ): Promise<CredentialsVerifyResponse> {
    const params: any = { use_saved: useSaved }
    if (!useSaved && user && pwd) {
      params.user = user
      params.pwd = pwd
    }
    
    return apiClient.post(`/bare-metals/${serverId}/verify-credentials`, null, { params })
  },

  // 更新服务器凭据
  updateServerCredentials(serverId: string, credentials: ServerCredentials): Promise<void> {
    return apiClient.put(`/bare-metals/${serverId}/credentials`, credentials)
  },

  powerCycle(serverId: string): Promise<void> {
    return apiClient.post(`/bare-metals/${serverId}/power-cycle`)
  },

  powerReset(serverId: string): Promise<void> {
    return apiClient.post(`/bare-metals/${serverId}/power-reset`)
  }
}