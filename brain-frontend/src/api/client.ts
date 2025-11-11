import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

let isRefreshing = false
let retryQueue: Array<() => void> = []

// 缓存接口定义
interface CacheItem {
  data: any
  timestamp: number
  etag?: string
  ttl: number // 每个缓存项有自己的TTL
}

interface CacheConfig {
  ttl?: number // 缓存存活时间（毫秒），默认5分钟
  maxSize?: number // 最大缓存数量，默认100条
  enableEtag?: boolean // 是否启用ETag验证，默认true
}

// 扩展axios config类型
interface ExtendedAxiosRequestConfig extends InternalAxiosRequestConfig {
  cache?: boolean | CacheConfig
  cacheKey?: string
  cacheConfig?: CacheConfig
  cachedData?: any
  _retry?: boolean
  _cacheHit?: boolean // 标记是否缓存命中
}

// 默认缓存配置
const DEFAULT_CACHE_CONFIG: Required<CacheConfig> = {
  ttl: 5 * 60 * 1000, // 5分钟
  maxSize: 100,
  enableEtag: true
}

// 缓存存储
class ApiCache {
  private cache = new Map<string, CacheItem>()
  private maxSize: number

  constructor(maxSize: number = 100) {
    this.maxSize = maxSize
  }

  get(key: string): CacheItem | null {
    const item = this.cache.get(key)
    if (!item) return null

    // 检查是否过期，使用缓存项自己的TTL
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key)
      return null
    }

    return item
  }

  set(key: string, data: any, ttl: number, etag?: string): void {
    // 如果超过最大大小，删除最旧的一项
    if (this.cache.size >= this.maxSize) {
      const firstKey = this.cache.keys().next().value
      if (firstKey) {
        this.cache.delete(firstKey)
      }
    }

    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl,
      etag
    })
  }

  delete(key: string): void {
    this.cache.delete(key)
  }

  clear(): void {
    this.cache.clear()
  }

  // 获取缓存大小
  get size(): number {
    return this.cache.size
  }

  // 获取所有缓存键
  keys(): IterableIterator<string> {
    return this.cache.keys()
  }

  // 获取所有缓存条目
  entries(): IterableIterator<[string, CacheItem]> {
    return this.cache.entries()
  }

  // 清理过期缓存
  cleanup(): void {
    const now = Date.now()
    for (const [key, item] of this.cache.entries()) {
      if (now - item.timestamp > item.ttl) {
        this.cache.delete(key)
      }
    }
  }
}

// 创建缓存实例
const apiCache = new ApiCache(DEFAULT_CACHE_CONFIG.maxSize)

// 生成缓存键
function generateCacheKey(config: InternalAxiosRequestConfig): string {
  const { method, url, params, data } = config
  // 使用更简单的缓存键，避免长字符串
  const paramsStr = params ? `?${new URLSearchParams(params).toString()}` : ''
  return `${method}:${url}${paramsStr}`
}

// 定期清理过期缓存（每10分钟一次）
setInterval(() => {
  apiCache.cleanup()
}, 10 * 60 * 1000)

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const extendedConfig = config as ExtendedAxiosRequestConfig
    const authStore = useAuthStore()
    const token = authStore.accessToken
    
    if (token) {
      extendedConfig.headers.Authorization = `Bearer ${token}`
    }

    // 处理GET请求缓存
    if (extendedConfig.method?.toLowerCase() === 'get') {
      // 获取缓存配置
      const cacheOption = extendedConfig.cache
      
      // 如果显式设置为false，跳过缓存
      if (cacheOption === false) {
        return extendedConfig
      }

      // 解析缓存配置
      const cacheConfig: Required<CacheConfig> = {
        ...DEFAULT_CACHE_CONFIG,
        ...(typeof cacheOption === 'object' ? cacheOption : {})
      }

      // 设置缓存配置
      extendedConfig.cacheConfig = cacheConfig

      // 生成缓存键
      const cacheKey = generateCacheKey(extendedConfig)
      extendedConfig.cacheKey = cacheKey

      // 检查缓存
      const cachedItem = apiCache.get(cacheKey)
      if (cachedItem) {
        // 标记为缓存命中
        extendedConfig._cacheHit = true
        extendedConfig.cachedData = cachedItem.data
        
        // 如果有ETag并且启用ETag验证，添加If-None-Match头
        if (cacheConfig.enableEtag && cachedItem.etag) {
          extendedConfig.headers['If-None-Match'] = cachedItem.etag
          // 有ETag时仍然发送请求，但期望返回304
        } else {
          // 没有ETag或禁用ETag验证时，直接返回缓存数据，不发送请求
          return {
            ...extendedConfig,
            adapter: () => {
              return Promise.resolve({
                data: cachedItem.data,
                status: 200,
                statusText: 'OK',
                headers: {},
                config: extendedConfig
              })
            }
          } as any
        }
      }
    }
    
    return extendedConfig
  },
  error => Promise.reject(error)
)

// 响应拦截器 - 自动token续约和缓存处理
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    const config = response.config as ExtendedAxiosRequestConfig

    // 处理GET请求的缓存
    if (config.method?.toLowerCase() === 'get' && config.cacheKey) {
      const cacheConfig = config.cacheConfig || DEFAULT_CACHE_CONFIG
      const etag = response.headers?.['etag'] || response.headers?.['ETag']
      
      // 如果是304 Not Modified，使用缓存数据
      if (response.status === 304 && config.cachedData) {
        return config.cachedData
      }

      // 缓存新数据（只有在不是缓存命中的情况下）
      if (response.status === 200 && !config._cacheHit) {
        apiCache.set(config.cacheKey, response.data, cacheConfig.ttl, etag)
      } else if (response.status === 200 && config._cacheHit) {
        // 缓存命中但数据已更新，刷新缓存
        apiCache.set(config.cacheKey, response.data, cacheConfig.ttl, etag)
      }
    }

    return response.data
  },
  async (error) => {
    const config = error.config as ExtendedAxiosRequestConfig

    // 处理304 Not Modified
    if (error.response?.status === 304 && config.cachedData) {
      return Promise.resolve(config.cachedData)
    }

    const authStore = useAuthStore()
    const originalRequest = error.config

    // 如果是401错误且不是刷新token的请求
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      
      if (isRefreshing) {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve) => {
          retryQueue.push(() => {
            originalRequest._retry = true
            resolve(apiClient(originalRequest))
          })
        })
      }
      
      originalRequest._retry = true
      isRefreshing = true
      
      try {
        // 尝试刷新 token
        await authStore.refreshToken()
        isRefreshing = false
        
        // 执行队列中的请求
        retryQueue.forEach(callback => callback())
        retryQueue = []
        
        // 重试原始请求
        return apiClient(originalRequest)
      } catch (refreshError) {
        // 刷新失败，跳转到登录页
        isRefreshing = false
        retryQueue = []
        authStore.logout('登录已过期，请重新登录')
        return Promise.reject(refreshError)
      }
    }
    
    // 其他错误处理
    if (error.response?.status == 504) {
       //504 only means that there is an offline server, no action is required
    } else if (error.response?.status >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else if (error.response?.status >= 400) {
      const message = error.response?.data?.detail || '请求错误，请检查输入'
      if (typeof message === 'string') {
        ElMessage.error(message)
      } else if (Array.isArray(message)) {
        message.forEach((item: any) => {
          ElMessage.error(item.msg || '请求错误')
        })
      }
    }
    
    return Promise.reject(error)
  }
)

// 缓存工具函数
export const cacheUtils = {
  // 清除特定URL的缓存
  clearCache(urlPattern: string | RegExp): void {
    for (const [key] of apiCache.entries()) {
      if (typeof urlPattern === 'string' && key.includes(urlPattern)) {
        apiCache.delete(key)
      } else if (urlPattern instanceof RegExp && urlPattern.test(key)) {
        apiCache.delete(key)
      }
    }
  },

  // 清除所有缓存
  clearAllCache(): void {
    apiCache.clear()
  },

  // 获取缓存统计信息
  getCacheStats(): { size: number; keys: string[] } {
    return {
      size: apiCache.size,
      keys: Array.from(apiCache.keys())
    }
  }
}

export default apiClient