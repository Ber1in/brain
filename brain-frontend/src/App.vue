<template>
  <div id="app">
    <el-container v-if="$route.path !== '/login'" class="layout-container">
      <el-aside width="200px" class="sidebar">
        <div class="logo">
          <h2>云服务器管理系统</h2>
        </div>
        <el-menu
          router
          :default-active="$route.path"
          class="sidebar-menu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/">
            <el-icon><House /></el-icon>
            <span>仪表板</span>
          </el-menu-item>
          <el-menu-item index="/images">
            <el-icon><Picture /></el-icon>
            <span>镜像管理</span>
          </el-menu-item>
          <el-menu-item index="/bare">
            <el-icon><Monitor /></el-icon>
            <span>裸金属服务器管理</span>
          </el-menu-item>
          <el-menu-item index="/mv200">
            <el-icon><Cpu /></el-icon>
            <span>MV200卡管理</span>
          </el-menu-item>
          <el-menu-item index="/system-disks">
            <el-icon><DataBoard /></el-icon>
            <span>云系统盘管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item>{{ $route.meta.title || $route.name }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <el-dropdown @command="handleCommand">
              <span class="user-info">
                <el-icon><User /></el-icon>
                {{ authStore.username }}
                <el-icon><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>

        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>

    <router-view v-else />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const authStore = useAuthStore()

// 应用启动时初始化认证状态
onMounted(() => {
  authStore.init()
})

const handleCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout()
    ElMessage.success('已退出登录')
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family:
    'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial,
    sans-serif;
}

.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid #1f2d3d;
}

.logo h2 {
  font-size: 18px;
  font-weight: 600;
}

.sidebar-menu {
  border: none;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid #e6e6e6;
  background: #fff;
}

.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
}

.main-content {
  padding: 20px;
  background: #f0f2f5;
  min-height: calc(100vh - 60px);
}
</style>