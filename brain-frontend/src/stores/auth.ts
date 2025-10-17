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
  const autoLogin = ref<boolean>(false)
  const isTabActive = ref<boolean>(true)

  const isAuthenticated = computed(() => {
    return !!accessToken.value && Date.now() < tokenExpiry.value
  })

  const username = computed(() => {
    return user.value?.username || '用户'
  })

  // 设置标签页活跃状态
  const setTabActive = (active: boolean) => {
    isTabActive.value = active
    const timestamp = new Date().toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
    console.log(`[${timestamp}] 标签页状态: ${active ? '活跃' : '闲置'}`)
  }

  // 检查是否需要刷新token（只在活跃状态下）
  const shouldRefreshToken = computed(() => {
    if (!isTabActive.value || !autoLogin.value) {
      return false
    }
    
    const timeUntilExpiry = tokenExpiry.value - Date.now()
    // 只在5分钟内过期且标签页活跃时刷新
    return timeUntilExpiry < 5 * 60 * 1000 && timeUntilExpiry > 0
  })

  const setTokens = (response: TokenResponse) => {
    accessToken.value = response.access_token
    refreshTokenValue.value = response.refresh_token
    tokenExpiry.value = Date.now() + (response.expires_in * 1000)
    
    console.log('Token设置成功:', {
      expiresIn: response.expires_in,
      expiryTime: new Date(tokenExpiry.value).toLocaleString()
    })
    
    localStorage.setItem('auth_token', response.access_token)
    localStorage.setItem('refresh_token', response.refresh_token)
    localStorage.setItem('token_expiry', tokenExpiry.value.toString())
    localStorage.setItem('auto_login', autoLogin.value.toString())
  }

  const setUser = (credentials: LoginCredentials) => {
    user.value = {
      username: credentials.username
    }
    localStorage.setItem('user_info', JSON.stringify(user.value))
  }

  const login = async (credentials: LoginCredentials, rememberMe: boolean = false) => {
    try {
      console.log('开始登录...', { rememberMe })
      autoLogin.value = rememberMe
      
      const response: TokenResponse = await authApi.login(credentials)
      setTokens(response)
      setUser(credentials)
      
      console.log('登录成功')
      return response
    } catch (error: any) {
      console.error('登录失败:', error)
      throw error
    }
  }

  const refreshToken = async (): Promise<boolean> => {
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

  // 修改：只在需要时刷新（考虑标签页状态）
  const checkAndRefreshToken = async (force: boolean = false): Promise<boolean> => {
    if (!accessToken.value) {
      console.log('没有access_token')
      return false
    }

    const timeUntilExpiry = tokenExpiry.value - Date.now()
    console.log('Token状态检查:', {
      剩余时间: Math.round(timeUntilExpiry / 1000) + '秒',
      需要刷新: timeUntilExpiry < 5 * 60 * 1000,
      自动登录启用: autoLogin.value,
      标签页活跃: isTabActive.value,
      强制刷新: force
    })

    if (force || shouldRefreshToken.value) {
      try {
        await refreshToken()
        return true
      } catch (error) {
        console.error('刷新token失败')
        return timeUntilExpiry > 0
      }
    }

    return timeUntilExpiry > 0
  }

  // 新增：当标签页从闲置恢复时的检查
  const onTabActivated = async (): Promise<boolean> => {
    if (!accessToken.value) {
      return false
    }

    const timeUntilExpiry = tokenExpiry.value - Date.now()
    console.log('标签页激活，检查token状态:', {
      剩余时间: Math.round(timeUntilExpiry / 1000) + '秒',
      是否过期: timeUntilExpiry <= 0
    })

    // 如果token已经过期，尝试刷新
    if (timeUntilExpiry <= 0 && autoLogin.value) {
      try {
        await refreshToken()
        return true
      } catch (error) {
        console.error('标签页激活时刷新token失败')
        return false
      }
    }

    return timeUntilExpiry > 0
  }

  const logout = (message?: string) => {
    console.log('执行退出登录')
    accessToken.value = ''
    refreshTokenValue.value = ''
    tokenExpiry.value = 0
    user.value = null
    autoLogin.value = false
    isTabActive.value = true
    
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
    
    if (router.currentRoute.value.path !== '/login') {
      router.push('/login')
    }
  }

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
    isTabActive,
    isAuthenticated,
    username,
    shouldRefreshToken,
    login,
    refreshToken,
    checkAndRefreshToken,
    onTabActivated,
    setTabActive,
    logout,
    init
  }
})