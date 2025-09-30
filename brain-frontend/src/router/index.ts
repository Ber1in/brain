import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/pages/Login.vue'),
      meta: { title: '登录' },
    },
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('@/pages/Dashboard.vue'),
      meta: {
        title: '仪表板',
        requiresAuth: true,
      },
    },
    {
      path: '/images',
      name: 'Images',
      component: () => import('@/pages/Images/Index.vue'),
      meta: {
        title: '镜像管理',
        requiresAuth: true,
      },
    },
    {
      path: '/images/create',
      name: 'ImageCreate',
      component: () => import('@/pages/Images/Create.vue'),
      meta: {
        title: '录入镜像',
        requiresAuth: true,
      },
    },
    {
      path: '/mv200',
      name: 'MV200',
      component: () => import('@/pages/MV200/Index.vue'),
      meta: {
        title: 'MV200卡管理',
        requiresAuth: true,
      },
    },
    {
      path: '/mv200/create',
      name: 'MV200Create',
      component: () => import('@/pages/MV200/Create.vue'),
      meta: {
        title: '录入MV200服务器',
        requiresAuth: true,
      },
    },
    {
      path: '/bare',
      name: 'BareMetal',
      component: () => import('@/pages/BareMetal/Index.vue'),
      meta: {
        title: '裸金属管理',
        requiresAuth: true,
      },
    },
    {
      path: '/bare/create',
      name: 'BareMetalCreate',
      component: () => import('@/pages/BareMetal/Create.vue'),
      meta: {
        title: '录入裸金属服务器',
        requiresAuth: true,
      },
    },
    {
      path: '/bare/edit/:id',
      name: 'BareMetalEdit',
      component: () => import('@/pages/BareMetal/Edit.vue'),
      meta: {
        title: '编辑裸金属服务器',
        requiresAuth: true,
      },
    },
    {
      path: '/system-disks',
      name: 'SystemDisks',
      component: () => import('@/pages/SystemDisks/Index.vue'),
      meta: {
        title: '裸金属云系统磁盘',
        requiresAuth: true,
      },
    },
    {
      path: '/system-disks/create',
      name: 'SystemDiskCreate',
      component: () => import('@/pages/SystemDisks/Create.vue'),
      meta: {
        title: '创建系统磁盘',
        requiresAuth: true,
      },
    },
    {
      path: '/images/edit/:id',
      name: 'ImageEdit',
      component: () => import('@/pages/Images/Edit.vue'),
      meta: {
        title: '编辑镜像',
        requiresAuth: true
      }
    },
    {
      path: '/mv200/edit/:id',
      name: 'MV200Edit',
      component: () => import('@/pages/MV200/Edit.vue'),
      meta: {
        title: '编辑MV200服务器',
        requiresAuth: true,
      },
    },
    {
      path: '/system-disks/edit/:id',
      name: 'SystemDiskEdit',
      component: () => import('@/pages/SystemDisks/Edit.vue'),
      meta: {
        title: '编辑系统磁盘',
        requiresAuth: true,
      },
    },
  ],
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth) {
    if (authStore.isAuthenticated) {
      next()
    } else {
      // 检查是否可以刷新token
      const canRefresh = await authStore.checkAndRefreshToken()
      if (canRefresh) {
        next()
      } else {
        next('/login')
      }
    }
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
