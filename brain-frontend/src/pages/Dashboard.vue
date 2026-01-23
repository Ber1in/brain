<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card" @click="goToPage('images')" style="cursor: pointer;">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff">
              <el-icon><Picture /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ imageCount }}</div>
              <div class="stat-label">镜像数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" @click="goToPage('mv200')" style="cursor: pointer;">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon><Cpu /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ mv200Count }}</div>
              <div class="stat-label">MV200数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" @click="goToPage('devices')" style="cursor: pointer;">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ deviceCount }}</div>
              <div class="stat-label">服务器数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>系统状态</span>
          </template>
          <div class="system-status">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="API服务">
                <el-tag :type="apiStatusType">{{ apiStatusText }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="认证服务">
                <el-tag type="success">正常</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="最后更新">
                {{ new Date().toLocaleString() }}
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { imagesApi } from '@/api/images'
import { mv200Api } from '@/api/mv200'
import { deviceApi } from '@/api/device'
import { useRouter } from 'vue-router'
import { networkApi } from '@/api/network'
import type { Image, MVServer, SystemDisk, InterfaceInfo, ServerDetailResponse } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const images = ref<Image[]>([])
const mv200Servers = ref<MVServer[]>([])
const devices = ref<ServerDetailResponse[]>([])
const loadError = ref(false)

const imageCount = computed(() => images.value.length)
const mv200Count = computed(() => mv200Servers.value.length)
const deviceCount = computed(() => devices.value.length)

// API服务状态计算属性
const apiStatusType = computed(() => {
  return loadError.value ? 'danger' : 'success'
})

const apiStatusText = computed(() => {
  return loadError.value ? '异常' : '正常'
})

const getImageName = (row: SystemDisk) => {
  const image = images.value.find((img) => img.id === row.image_id)
  return image?.name || row.image_id
}

const getMV200Name = (row: SystemDisk) => {
  const server = mv200Servers.value.find((s) => s.id === row.mv200_id)
  return server?.name || row.mv200_id
}

const goToPage = (pageType: string) => {
  switch (pageType) {
    case 'images':
      router.push('/images')
      break
    case 'mv200':
      router.push('/mv200')
      break
    case 'devices':
      router.push('/devices')
      break
    case 'xsc-interface':
      router.push('/xsc-interface')
      break
    default:
      console.warn('未知的页面类型:', pageType)
  }
}

const loadData = async () => {
  loading.value = true
  loadError.value = false
  try {
    const [imagesResponse, serversResponse, devicesResponse] = await Promise.all([
      imagesApi.getAll(),
      mv200Api.getAll(),
      deviceApi.getAll(),
    ])

    images.value = imagesResponse
    mv200Servers.value = serversResponse
    devices.value = devicesResponse
  } catch (error) {
    console.error('加载数据失败:', error)
    loadError.value = true
    // 清空数据，避免显示旧数据
    images.value = []
    mv200Servers.value = []
    devices.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.stat-icon .el-icon {
  font-size: 30px;
  color: white;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.system-status {
  padding: 10px;
}
</style>