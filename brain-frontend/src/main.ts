import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(pinia)
app.use(router)
app.use(ElementPlus)

// 初始化认证状态
const authStore = useAuthStore()
authStore.init()

const setupPageVisibility = () => {
  const handleVisibilityChange = () => {
    const isVisible = !document.hidden
    authStore.setTabActive(isVisible)
    
    if (isVisible && authStore.accessToken) {
      console.log('页面变为可见，检查token状态')
      authStore.onTabActivated().then(isValid => {
        if (!isValid && authStore.autoLogin) {
          authStore.logout('登录已过期，请重新登录')
        }
      })
    }
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)
  
  // 页面加载时设置初始状态
  authStore.setTabActive(!document.hidden)
}

// 设置定时token检查（只在活跃状态下检查）
const setupTokenRefreshInterval = () => {
  setInterval(async () => {
    if (authStore.accessToken && authStore.isTabActive) {
      try {
        await authStore.checkAndRefreshToken()
      } catch (error) {
        console.error('定时token检查失败:', error)
      }
    }
  }, 5 * 60 * 1000) // 5分钟
}

// 初始化
setupPageVisibility()
setupTokenRefreshInterval()

app.mount('#app')