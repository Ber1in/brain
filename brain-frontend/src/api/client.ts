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

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()
    const token = authStore.accessToken
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器 - 自动token续约
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  async (error) => {
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
    if (error.response?.status >= 500) {
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

export default apiClient