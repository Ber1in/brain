import apiClient from './client'
import type { ServerRequest, ServerDetailResponse, ServerUpdateRequest, BootEntriesResponse, MCRRequest, ResetFwRequest, NicResponse, DeviceResponse, GrubConfig } from '@/types/api'

export const deviceApi = {
  getAllWithPagination(params?: {
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    filter_conditions?: {
      [key: string]: any;
    };
  }): Promise<{
    data: ServerDetailResponse[];
    pagination?: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
      has_next: boolean;
      has_prev: boolean;
    };
  }> {
    const requestParams: any = { ...params }
    
    if (params?.filter_conditions) {
      requestParams.filter_conditions = JSON.stringify(params.filter_conditions)
    }
    
    if (params?.sort_by) {
      requestParams.sort_by = params.sort_by
    }
    if (params?.sort_order) {
      requestParams.sort_order = params.sort_order
    }
    
    return apiClient.get('/api/servers', { 
      params: requestParams,
      // 确保返回完整响应
      transformResponse: (data, headers) => {
        // 返回一个对象，包含数据和 headers
        return {
          data: JSON.parse(data),
          headers: headers
        }
      }
    }).then((response: any) => {
      
      // 处理 transformResponse 返回的结构
      if (response && response.data && response.headers) {
        const data = response.data
        const headers = response.headers
        
        // 提取分页信息
        const totalCount = headers['x-total-count'] || headers['X-Total-Count']
        const pageHeader = headers['x-page'] || headers['X-Page']
        const pageSize = headers['x-page-size'] || headers['X-Page-Size']
        const totalPages = headers['x-total-pages'] || headers['X-Total-Pages']
        const hasNext = headers['x-has-next'] || headers['X-Has-Next']
        const hasPrev = headers['x-has-prev'] || headers['X-Has-Prev']
        
        const result: any = {
          data: data
        }
        
        if (totalCount || pageHeader || pageSize) {
          result.pagination = {
            page: parseInt(pageHeader || (params?.page?.toString() || '1')),
            page_size: parseInt(pageSize || (params?.page_size?.toString() || '5')),
            total: parseInt(totalCount || '0'),
            total_pages: parseInt(totalPages || '1'),
            has_next: (hasNext?.toString().toLowerCase() === 'true') || false,
            has_prev: (hasPrev?.toString().toLowerCase() === 'true') || false
          }
        }
        
        return result
      }
      
      // 如果 transformResponse 没有工作，返回原始数据
      return {
        data: response || []
      }
    })
  },

  getAll(params?: {
    filter_conditions?: {
      [key: string]: any;
    };
  }): Promise<ServerDetailResponse[]> {
    const requestParams: any = {}
    
    // Convert filter conditions to JSON string if exists
    if (params?.filter_conditions) {
      requestParams.filter_conditions = JSON.stringify(params.filter_conditions)
    }
    
    return apiClient.get('/api/servers', { 
      params: requestParams
    })
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

  getNics(serverId: string): Promise<NicResponse> {
    return apiClient.get(`/api/servers/${serverId}/nics`)
  },

  getHws(serverId: string): Promise<DeviceResponse> {
    return apiClient.get(`/api/servers/${serverId}/hw`)
  },

  getGrubConfig(serverId: string): Promise<GrubConfig> {
    return apiClient.get(`/api/servers/${serverId}/grub`)
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

  followServer(serverId: string): Promise<void> {
    return apiClient.patch(`/api/servers/${serverId}/follow`)
  },
  
  unfollowServer(serverId: string): Promise<void> {
    return apiClient.patch(`/api/servers/${serverId}/unfollow`)
  },

  lockServer(serverId: string, lock: number): Promise<void> {
    return apiClient.patch(`/api/servers/${serverId}/lock`, { lock })
  },

  occupyServer(serverId: string, time: number): Promise<ServerDetailResponse> {
    return apiClient.patch(`/api/servers/${serverId}/occupy`, { time })
  },

  releaseServer(serverId: string): Promise<ServerDetailResponse> {
    return apiClient.patch(`/api/servers/${serverId}/release`)
  },

  getAllNicTypes(): Promise<string[]> {
    return apiClient.get('/api/servers/nic_types')
  },
}