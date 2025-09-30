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

// 设置定时token检查（每5分钟检查一次）
setInterval(async () => {
  if (authStore.accessToken) {
    try {
      await authStore.checkAndRefreshToken()
    } catch (error) {
      console.error('定时token检查失败:', error)
    }
  }
}, 5 * 60 * 1000) // 5分钟

app.mount('#app')