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
          :default-openeds="['mv200-group','more-menu']"
          class="sidebar-menu"
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/">
            <el-icon><House /></el-icon>
            <span>仪表板</span>
          </el-menu-item>
          
          <!-- 1. 云镜像管理 -->
          <el-menu-item index="/images">
            <el-icon><Picture /></el-icon>
            <span>云镜像管理</span>
          </el-menu-item>
          
          <!-- 2. 服务器管理 -->
          <el-menu-item index="/devices">
            <el-icon><Monitor /></el-icon>
            <span>服务器管理</span>
          </el-menu-item>
          
          <!-- 3. MV200管理及其子菜单（自定义实现） -->
          <el-sub-menu 
            index="mv200-group" 
            class="mv200-submenu"
          >
            <template #title>
              <div class="mv200-menu-title" @click.stop="goToMv200">
                <el-icon><Cpu /></el-icon>
                <span>MV200管理</span>
                <el-icon 
                  class="arrow-icon" 
                  :class="{ 'is-active': mv200MenuOpen }"
                  @click.stop="toggleMv200Menu"
                >
                </el-icon>
              </div>
            </template>
            <!-- 云系统盘管理 -->
            <el-menu-item index="/system-disks" @click.stop>
              <el-icon><DataBoard /></el-icon>
              <span>云系统盘管理</span>
            </el-menu-item>
            <!-- XSC网口管理 -->
            <el-menu-item index="/xsc-interface" @click.stop>
              <el-icon><Connection /></el-icon>
              <span>XSC网口管理</span>
            </el-menu-item>
          </el-sub-menu>
          
          <!-- 4. 质量保证平台 -->
          <el-menu-item index="/tester">
            <el-icon><Medal /></el-icon>
            <span>质量保证平台</span>
          </el-menu-item>

          <!-- 5. 更多 -->
          <el-sub-menu index="more-menu">
            <template #title>
              <el-icon><Menu /></el-icon>
              <span>更多</span>
            </template>
            <!-- 系统设置 -->
            <el-menu-item index="/settings">
              <el-icon><Setting /></el-icon>
              <span>系统设置</span>
            </el-menu-item>
            <!-- 操作日志 -->
            <el-menu-item index="/audit">
              <el-icon><Document /></el-icon>
              <span>操作日志</span>
            </el-menu-item>
            <!-- 帮助文档 -->
            <el-menu-item index="/help">
              <el-icon><QuestionFilled /></el-icon>
              <span>帮助文档</span>
            </el-menu-item>
          </el-sub-menu>
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
import { onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const mv200MenuOpen = ref(false)

// 应用启动时初始化认证状态
onMounted(() => {
  authStore.init()
})

// 监听路由变化，更新MV200菜单展开状态
watch(() => route.path, (newPath) => {
  if (newPath.startsWith('/mv200') || 
      newPath.startsWith('/system-disks') || 
      newPath.startsWith('/xsc-interface')) {
    mv200MenuOpen.value = true
  } else {
    mv200MenuOpen.value = false
  }
}, { immediate: true })

// 导航到MV200页面
const goToMv200 = () => {
  router.push('/mv200')
}

// 切换MV200菜单展开状态
const toggleMv200Menu = () => {
  mv200MenuOpen.value = !mv200MenuOpen.value
}

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

/* MV200菜单特殊样式 */
.mv200-submenu :deep(.el-sub-menu__title) {
  padding-right: 30px !important;
}

.mv200-menu-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  cursor: pointer;
}

.mv200-menu-title:hover {
  color: #409EFF;
}

.mv200-menu-title > :first-child {
  display: flex;
  align-items: center;
  flex: 1;
}

.arrow-icon {
  transition: transform 0.3s;
  margin-left: 8px;
  cursor: pointer;
}

.arrow-icon:hover {
  color: #409EFF;
}

.arrow-icon.is-active {
  transform: rotate(180deg);
}

/* 移除默认的箭头样式 */
.mv200-submenu :deep(.el-sub-menu__title .el-sub-menu__icon-arrow) {
  display: none !important;
}

/* 强制子菜单项不继承父级的点击事件 */
.mv200-submenu :deep(.el-menu-item) {
  cursor: pointer !important;
}

/* 确保子菜单项有自己的悬停样式 */
.mv200-submenu :deep(.el-menu-item:hover) {
  background-color: #263445 !important;
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