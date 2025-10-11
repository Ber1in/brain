<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>云服务器管理系统</h2>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" size="large" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        
        <!-- 添加7天内自动登录选项 -->
        <el-form-item>
          <el-checkbox v-model="form.rememberMe" label="3天内自动登录" size="large" />
        </el-form-item>
        
        <el-button
          type="primary"
          native-type="submit"
          :loading="loading"
          size="large"
          style="width: 100%"
        >
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = ref({
  username: '',
  password: '',
  rememberMe: false, // 添加记住我选项
})

// 页面加载时检查是否有保存的用户名
onMounted(() => {
  const savedUser = localStorage.getItem('user_info')
  if (savedUser) {
    try {
      const userInfo = JSON.parse(savedUser)
      form.value.username = userInfo.username || ''
    } catch (error) {
      console.error('解析保存的用户信息失败:', error)
    }
  }
})

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    // 传递 rememberMe 参数
    await authStore.login(form.value, form.value.rememberMe)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 20px;
}

.login-card h2 {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

/* 调整复选框样式 */
:deep(.el-checkbox) {
  width: 100%;
}

:deep(.el-checkbox__label) {
  font-size: 14px;
  color: #606266;
}
</style>