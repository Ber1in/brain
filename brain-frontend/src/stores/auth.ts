import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { LoginCredentials, TokenResponse, User } from '@/types/api'
import { authApi } from '@/api/auth'
import router from '@/router'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string>('')
  const refreshTokenValue = ref<string>('')
  const tokenExpiry = ref<number>(0)
  const user = ref<User | null>(null)
  const autoLogin = ref<boolean>(false) // 添加自动登录标志

  const isAuthenticated = computed(() => {
    return !!accessToken.value && Date.now() < tokenExpiry.value
  })

  // 获取当前用户名
  const username = computed(() => {
    return user.value?.username || '用户'
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
    localStorage.setItem('auto_login', autoLogin.value.toString()) // 保存自动登录设置
  }

  // 设置用户信息
  const setUser = (credentials: LoginCredentials) => {
    user.value = {
      username: credentials.username
    }
    localStorage.setItem('user_info', JSON.stringify(user.value))
  }

  // 登录
  const login = async (credentials: LoginCredentials, rememberMe: boolean = false) => {
    try {
      console.log('开始登录...', { rememberMe })
      autoLogin.value = rememberMe // 设置自动登录标志
      
      const response: TokenResponse = await authApi.login(credentials)
      setTokens(response)
      
      // 登录成功后直接记录用户名
      setUser(credentials)
      
      console.log('登录成功')
      return response
    } catch (error: any) {
      console.error('登录失败:', error)
      throw error
    }
  }

  // 刷新 token
  const refreshToken = async (): Promise<boolean> => {
    // 检查是否启用了自动登录
    if (!autoLogin.value) {
      console.log('自动登录未启用，不刷新token')
      throw new Error('自动登录未启用')
    }

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
      console.error('Token刷新失败:', error.response?.data)
      throw error
    }
  }

  // 检查token状态，如果需要则刷新
  const checkAndRefreshToken = async (): Promise<boolean> => {
    if (!accessToken.value) {
      console.log('没有access_token')
      return false
    }

    const timeUntilExpiry = tokenExpiry.value - Date.now()
    console.log('Token状态检查:', {
      剩余时间: Math.round(timeUntilExpiry / 1000) + '秒',
      需要刷新: timeUntilExpiry < 5 * 60 * 1000, // 5分钟内过期就刷新
      自动登录启用: autoLogin.value
    })

    // 如果token在5分钟内过期且启用了自动登录，提前刷新
    if (timeUntilExpiry < 5 * 60 * 1000 && autoLogin.value) {
      try {
        await refreshToken()
        return true
      } catch (error) {
        console.error('自动刷新token失败')
        // 自动刷新失败，但不立即退出，等到真正过期再处理
        return timeUntilExpiry > 0
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
    user.value = null
    autoLogin.value = false // 清除自动登录设置
    
    localStorage.removeItem('auth_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_expiry')
    localStorage.removeItem('user_info')
    localStorage.removeItem('auto_login')
    
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
    const storedUser = localStorage.getItem('user_info')
    const storedAutoLogin = localStorage.getItem('auto_login')
    
    if (storedToken && storedRefreshToken && storedExpiry) {
      accessToken.value = storedToken
      refreshTokenValue.value = storedRefreshToken
      tokenExpiry.value = parseInt(storedExpiry)

      if (storedUser) {
        try {
          user.value = JSON.parse(storedUser)
        } catch (error) {
          console.error('解析用户信息失败:', error)
        }
      }
      
      // 恢复自动登录设置
      if (storedAutoLogin) {
        autoLogin.value = storedAutoLogin === 'true'
      }

    }
  }

  return {
    accessToken,
    refreshToken: refreshTokenValue,
    user,
    autoLogin,
    isAuthenticated,
    username,
    login,
    refreshToken,
    checkAndRefreshToken,
    logout,
    init
  }
})