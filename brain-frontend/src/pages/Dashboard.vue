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
        <el-card class="stat-card" @click="goToPage('baremetal')" style="cursor: pointer;">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ bareCount }}</div>
              <div class="stat-label">裸金属服务器数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" @click="goToPage('blocks')" style="cursor: pointer;">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon><DataBoard /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ diskCount }}</div>
              <div class="stat-label">云系统盘数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>最近创建的系统磁盘</span>
          </template>
          <el-table :data="recentDisks" v-loading="loading">
            <el-table-column label="ID" prop="id" width="200" />
            <el-table-column label="镜像" :formatter="getImageName" />
            <el-table-column label="MV200服务器" :formatter="getMV200Name" />
            <el-table-column label="大小(GB)" prop="size_gb" width="100" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>系统状态</span>
          </template>
          <div class="system-status">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="API服务状态">
                <el-tag type="success">正常</el-tag>
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
import { bareApi } from '@/api/bare'
import { useRouter } from 'vue-router'
import { systemDisksApi } from '@/api/system-disks'
import type { Image, MVServer, SystemDisk } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const images = ref<Image[]>([])
const mv200Servers = ref<MVServer[]>([])
const bareServers = ref<BareMetalServer[]>([])
const disks = ref<SystemDisk[]>([])

const imageCount = computed(() => images.value.length)
const mv200Count = computed(() => mv200Servers.value.length)
const bareCount = computed(() => bareServers.value.length)
const diskCount = computed(() => disks.value.length)
const recentDisks = computed(() => disks.value.slice(0, 5))

const getImageName = (row: SystemDisk) => {
  const image = images.value.find((img) => img.id === row.image_id)
  return image?.name || row.image_id
}

const getMV200Name = (row: SystemDisk) => {
  const server = mv200Servers.value.find((s) => s.id === row.mv200_id)
  return server?.name || row.mv200_id
}

const goToPage = (pageType) => {
  switch (pageType) {
    case 'images':
      router.push('/images')
      break
    case 'mv200':
      router.push('/mv200')
      break
    case 'baremetal':
      router.push('/bare') // 如果没有裸金属页面，可以用 '/mv200' 或其他
      break
    case 'blocks':
      router.push('/system-disks')
      break
    default:
      console.warn('未知的页面类型:', pageType)
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const [imagesResponse, serversResponse, disksResponse, bareResponse] = await Promise.all([
      imagesApi.getAll(),
      mv200Api.getAll(),
      systemDisksApi.getAll(),
      bareApi.getAll(),
    ])

    images.value = imagesResponse
    mv200Servers.value = serversResponse
    disks.value = disksResponse
    bareServers.value = bareResponse
  } catch (error) {
    console.error('加载数据失败:', error)
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
