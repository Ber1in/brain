import apiClient from './client'
import type { ServerRequest, ServerDetailResponse, ServerUpdateRequest, BootEntriesResponse, MCRRequest, ResetFwRequest, NicResponse, DeviceResponse, GrubConfig } from '@/types/api'

export const deviceApi = {
  getAllWithPagination(params?: {
    page?: number;
    page_size?: number;
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
    
    // Convert filter conditions to JSON string if exists
    if (params?.filter_conditions) {
      requestParams.filter_conditions = JSON.stringify(params.filter_conditions)
    }
    
    // 确保 apiClient.get 返回完整的响应对象
    return apiClient.get('/api/servers', { 
      params: requestParams,
      // 如果需要，添加配置以确保返回完整响应
      // transformResponse: (res) => res, // 不自动解析响应
      // headers: { 'Accept': 'application/json' }
    }).then((response: any) => {
      // 调试日志：查看响应结构
      console.log('API Response:', response)
      console.log('Response headers:', response.headers)
      
      const result: any = {
        data: response.data || response // 兼容不同格式
      }
      
      // 安全地从响应头中提取分页信息
      const headers = response.headers || {}
      
      // 检查是否有分页头信息（处理大小写不敏感）
      const getHeader = (key: string): string | undefined => {
        const lowerKey = key.toLowerCase()
        for (const [headerKey, value] of Object.entries(headers)) {
          if (headerKey.toLowerCase() === lowerKey) {
            return value as string
          }
        }
        return undefined
      }
      
      const totalCount = getHeader('x-total-count')
      const pageHeader = getHeader('x-page')
      const pageSize = getHeader('x-page-size')
      const totalPages = getHeader('x-total-pages')
      const hasNext = getHeader('x-has-next')
      const hasPrev = getHeader('x-has-prev')
      
      // 如果存在任何分页头信息，就设置分页
      if (totalCount || pageHeader || pageSize) {
        result.pagination = {
          page: parseInt(pageHeader || (params?.page?.toString() || '1')),
          page_size: parseInt(pageSize || (params?.page_size?.toString() || '20')),
          total: parseInt(totalCount || '0'),
          total_pages: parseInt(totalPages || '1'),
          has_next: hasNext?.toLowerCase() === 'true' || false,
          has_prev: hasPrev?.toLowerCase() === 'true' || false
        }
      }
      
      return result
    }).catch((error: any) => {
      console.error('API Error:', error)
      throw error
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

  focusServer(serverId: string, focus: boolean): Promise<void> {
    return apiClient.patch(`/api/servers/${serverId}/focus`, { focus })
  },

  occupyServer(serverId: string, time: number): Promise<ServerDetailResponse> {
    return apiClient.patch(`/api/servers/${serverId}/occupy`, { time })
  },

  getAllNicTypes(): Promise<string[]> {
    return apiClient.get('/api/servers/nic_types')
  },
}