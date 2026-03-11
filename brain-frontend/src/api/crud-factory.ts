/**
 * 通用 CRUD API 工厂函数
 * 用于生成标准化的 CRUD API 接口，减少重复代码
 */

import apiClient from './client'

/**
 * CRUD API 配置选项
 */
export interface CrudApiOptions<T, TCreate, TUpdate> {
  /**
   * 端点路径，例如 'images'、'mv-servers'、'bare-metals' 等
   */
  endpoint: string
  
  /**
   * 自定义响应转换函数
   */
  transformResponse?: (data: any) => T | T[]
  
  /**
   * 自定义请求配置
   */
  requestConfig?: {
    timeout?: number
    headers?: Record<string, string>
  }
  
  /**
   * 是否禁用缓存（对于频繁变动的数据）
   */
  disableCache?: boolean
}

/**
 * 创建标准的 CRUD API 接口
 * @param options CRUD API 配置
 * @returns 包含标准 CRUD 方法的对象
 */
export function createCrudApi<T, TCreate = Partial<T>, TUpdate = Partial<T>>(
  options: CrudApiOptions<T, TCreate, TUpdate>
) {
  const { endpoint, transformResponse, requestConfig, disableCache } = options
  
  /**
   * 获取所有记录
   */
  const getAll = (params?: Record<string, any>): Promise<T[]> => {
    const config = { 
      ...requestConfig,
      params,
      ...(disableCache ? { cache: false } : {})
    }
    
    return apiClient.get(`/${endpoint}`, config).then(data => {
      if (transformResponse) {
        return transformResponse(data) as T[]
      }
      return data
    })
  }

  /**
   * 根据ID获取单条记录
   */
  const getById = (id: string, params?: Record<string, any>): Promise<T> => {
    const config = { 
      ...requestConfig,
      params,
      ...(disableCache ? { cache: false } : {})
    }
    
    return apiClient.get(`/${endpoint}/${id}`, config).then(data => {
      if (transformResponse) {
        return transformResponse(data) as T
      }
      return data
    })
  }

  /**
   * 创建新记录
   */
  const create = (data: TCreate): Promise<T> => {
    return apiClient.post(`/${endpoint}`, data, requestConfig).then(data => {
      if (transformResponse) {
        return transformResponse(data) as T
      }
      return data
    })
  }

  /**
   * 更新记录
   */
  const update = (id: string, data: TUpdate): Promise<T> => {
    return apiClient.put(`/${endpoint}/${id}`, data, requestConfig).then(data => {
      if (transformResponse) {
        return transformResponse(data) as T
      }
      return data
    })
  }

  /**
   * 删除记录
   */
  const deleteById = (id: string): Promise<void> => {
    return apiClient.delete(`/${endpoint}/${id}`, requestConfig)
  }

  /**
   * 分页查询（如果需要）
   */
  const getPaginated = (
    page: number = 1,
    pageSize: number = 10,
    params?: Record<string, any>
  ): Promise<{ data: T[]; total: number; page: number; pageSize: number }> => {
    const queryParams = {
      page,
      page_size: pageSize,
      ...params
    }
    
    return apiClient.get(`/${endpoint}`, { 
      ...requestConfig,
      params: queryParams 
    }).then((response: any) => {
      // 假设后端返回标准的分页结构
      // 可以根据实际响应格式调整
      if (transformResponse) {
        const transformed = transformResponse(response.data || response)
        return {
          data: Array.isArray(transformed) ? transformed : [transformed],
          total: response.total || response.count || 0,
          page: response.page || page,
          pageSize: response.pageSize || pageSize
        }
      }
      
      return {
        data: response.data || response,
        total: response.total || response.count || 0,
        page: response.page || page,
        pageSize: response.pageSize || pageSize
      }
    })
  }

  return {
    getAll,
    getById,
    create,
    update,
    delete: deleteById,
    getPaginated
  }
}

/**
 * 创建带分页的 CRUD API（针对需要复杂分页的场景）
 */
export function createPaginatedCrudApi<T, TCreate = Partial<T>, TUpdate = Partial<T>>(
  options: CrudApiOptions<T, TCreate, TUpdate> & {
    /**
     * 分页响应转换函数
     */
    transformPaginatedResponse?: (response: any) => {
      data: T[]
      pagination: {
        page: number
        pageSize: number
        total: number
        totalPages: number
        hasNext: boolean
        hasPrev: boolean
      }
    }
  }
) {
  const { transformPaginatedResponse, ...crudOptions } = options
  const baseCrud = createCrudApi<T, TCreate, TUpdate>(crudOptions)

  /**
   * 获取分页数据（支持复杂分页场景）
   */
  const getPaginated = (params?: {
    page?: number
    page_size?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
    filter_conditions?: Record<string, any>
  }): Promise<{
    data: T[]
    pagination?: {
      page: number
      page_size: number
      total: number
      total_pages: number
      has_next: boolean
      has_prev: boolean
    }
  }> => {
    const requestParams: Record<string, any> = { ...params }
    
    // 处理筛选条件（如果需要序列化）
    if (params?.filter_conditions) {
      requestParams.filter_conditions = JSON.stringify(params.filter_conditions)
    }
    
    return apiClient.get(`/${options.endpoint}`, { 
      ...options.requestConfig,
      params: requestParams,
      // 确保返回完整响应以获取 headers 中的分页信息
      transformResponse: (data, headers) => ({ data, headers })
    }).then((response: any) => {
      if (transformPaginatedResponse) {
        return transformPaginatedResponse(response)
      }
      
      // 默认处理：从 headers 提取分页信息
      const data = response.data
      const headers = response.headers || {}
      
      const result: any = {
        data: data || []
      }
      
      // 提取分页信息（假设后端通过 headers 传递）
      const totalCount = headers['x-total-count'] || headers['X-Total-Count']
      const pageHeader = headers['x-page'] || headers['X-Page']
      const pageSize = headers['x-page-size'] || headers['X-Page-Size']
      const totalPages = headers['x-total-pages'] || headers['X-Total-Pages']
      const hasNext = headers['x-has-next'] || headers['X-Has-Next']
      const hasPrev = headers['x-has-prev'] || headers['X-Has-Prev']
      
      if (totalCount || pageHeader || pageSize) {
        result.pagination = {
          page: parseInt(pageHeader || (params?.page?.toString() || '1')),
          page_size: parseInt(pageSize || (params?.page_size?.toString() || '10')),
          total: parseInt(totalCount || '0'),
          total_pages: parseInt(totalPages || '1'),
          has_next: (hasNext?.toString().toLowerCase() === 'true') || false,
          has_prev: (hasPrev?.toString().toLowerCase() === 'true') || false
        }
      }
      
      return result
    })
  }

  return {
    ...baseCrud,
    getPaginated
  }
}