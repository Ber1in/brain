import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { LoginCredentials, TokenResponse } from '@/types/api'
import { authApi } from '@/api/auth'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string>('')
  const refreshTokenValue = ref<string>('')
  const tokenExpiry = ref<number>(0)

  const isAuthenticated = computed(() => {
    return !!accessToken.value && Date.now() < tokenExpiry.value
  })

  // 设置token信息
  const setTokens = (response: TokenResponse) => {
    accessToken.value = response.access_token
    refreshTokenValue.value = response.refresh_token
    
    // access_token 30分钟过期 (1800秒)
    tokenExpiry.value = Date.now() + (response.expires_in * 1000)
    
    console.log('Token设置成功:', {
      expiresIn: response.expires_in,
      expiryTime: new Date(tokenExpiry.value).toLocaleString()
    })
    
    // 存储到 localStorage
    localStorage.setItem('auth_token', response.access_token)
    localStorage.setItem('refresh_token', response.refresh_token)
    localStorage.setItem('token_expiry', tokenExpiry.value.toString())
  }

  // 登录
  const login = async (credentials: LoginCredentials) => {
    try {
      console.log('开始登录...')
      const response: TokenResponse = await authApi.login(credentials)
      setTokens(response)
      console.log('登录成功')
      return response
    } catch (error: any) {
      console.error('登录失败:', error)
      throw error
    }
  }

  // 刷新 token - 简化版本
  const refreshToken = async (): Promise<boolean> => {
    const storedRefreshToken = localStorage.getItem('refresh_token')
    if (!storedRefreshToken) {
      throw new Error('没有可用的refresh_token')
    }

    console.log('开始刷新token...')
    try {
      const response: TokenResponse = await authApi.refreshToken(storedRefreshToken)
      setTokens(response)
      console.log('Token刷新成功')
      return true
    } catch (error: any) {
      console.error('Token刷新失败:', error.response.data)
      // 只是抛出错误，不调用 logout
      throw error
    }
  }

  // 检查token状态，如果需要则刷新
  const checkAndRefreshToken = async (): Promise<boolean> => {
    if (!accessToken.value) {
      logout('请重新登录')
      return false
    }

    const timeUntilExpiry = tokenExpiry.value - Date.now()
    console.log('Token状态检查:', {
      剩余时间: Math.round(timeUntilExpiry / 1000) + '秒',
      需要刷新: timeUntilExpiry < 2 * 60 * 1000 // 10分钟内过期就刷新
    })

    // 如果token在10分钟内过期，提前刷新
    if (timeUntilExpiry < 2 * 60 * 1000) {
      try {
        await refreshToken()
        return true
      } catch (error) {
        console.error('自动刷新token失败')
        logout('登录已过期，请重新登录')
        return false
      }
    }

    return timeUntilExpiry > 0
  }

  // 退出登录
  const logout = (message?: string) => {
    console.log('执行退出登录')
    accessToken.value = ''
    refreshTokenValue.value = ''
    tokenExpiry.value = 0
    
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_expiry')
    
    if (message) {
      setTimeout(() => {
        ElMessage.error(message)
      }, 100)
    }
    
    router.push('/login')
  }

  // 初始化时从 localStorage 恢复状态
  const init = () => {
    const storedToken = localStorage.getItem('auth_token')
    const storedRefreshToken = localStorage.getItem('refresh_token')
    const storedExpiry = localStorage.getItem('token_expiry')
    
    if (storedToken && storedRefreshToken && storedExpiry) {
      accessToken.value = storedToken
      refreshTokenValue.value = storedRefreshToken
      tokenExpiry.value = parseInt(storedExpiry)
      
      console.log('从localStorage恢复Token状态:', {
        expiryTime: new Date(parseInt(storedExpiry)).toLocaleString()
      })
    }
  }

  return {
    accessToken,
    refreshToken: refreshTokenValue,
    isAuthenticated,
    login,
    refreshToken,
    checkAndRefreshToken,
    logout,
    init
  }
})