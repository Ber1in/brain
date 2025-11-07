<template>
  <div class="device-detail">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>服务器详情 - {{ deviceData.bmc?.hostname }}</h2>
          <div class="header-actions">
            <el-button 
              type="warning" 
              @click="handleRefresh" 
              :loading="refreshing"
              :disabled="refreshing"
            >
              <el-icon><Refresh /></el-icon>
              {{ refreshing ? '更新中...' : '更新信息' }}
            </el-button>
            <el-button type="primary" @click="handleEdit">
              <el-icon><Edit /></el-icon>
              编辑服务器
            </el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <!-- 基本信息 -->
        <el-descriptions-item label="创建时间">{{ formatTime(deviceData.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(deviceData.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="占用信息" :span="2">
          <div v-if="isDeviceOccupied">
            <el-tag type="success" style="margin-right: 8px;">{{ deviceData.user }}</el-tag>
            <span>占用至 {{ getEndTimeDisplay() }}</span>
          </div>
          <el-tag v-else type="info">未占用</el-tag>
        </el-descriptions-item>

        <!-- BMC信息 -->
        <el-descriptions-item label="服务器名称">{{ deviceData.bmc?.hostname || '-' }}</el-descriptions-item>
        <el-descriptions-item label="BMC IP">{{ deviceData.bmc?.ip || '-' }}</el-descriptions-item>

        <!-- 服务器信息 -->
        <el-descriptions-item label="服务器IP">{{ deviceData.device?.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="服务器序列号">{{ deviceData.device?.sn || '-' }}</el-descriptions-item>
        
        <!-- 新增的管理口信息 -->
        <el-descriptions-item label="管理口MAC地址">{{ deviceData.device?.mac || '-' }}</el-descriptions-item>
        <el-descriptions-item label="管理网网关">{{ deviceData.device?.gateway || '-' }}</el-descriptions-item>

        <!-- 网卡信息 -->
        <el-descriptions-item label="网卡数量" :span="2">
          {{ deviceData.nics?.length || 0 }} 个
        </el-descriptions-item>

        <!-- 操作系统类型 - 修改后的展示方式 -->
        <el-descriptions-item label="操作系统类型" :span="2">
          <div v-if="bootEntriesLoading" class="loading-text">
            <el-icon class="is-loading"><Loading /></el-icon>
            加载启动项信息中...
          </div>
          <div v-else-if="bootEntriesList && bootEntriesList.length > 0">
            <div 
              v-for="os in bootEntriesList" 
              :key="os.key" 
              class="os-item"
              :class="{ 
                'current-os': os.isCurrent,
                'default-os': os.isDefault
              }"
            >
              {{ os.displayText }}
            </div>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>

        <!-- 标签 -->
        <el-descriptions-item label="标签" :span="2">
          <div v-if="deviceData.tags && deviceData.tags.length > 0">
            <el-tag 
              v-for="tag in deviceData.tags" 
              :key="tag" 
              type="info"
              style="margin-right: 8px; margin-bottom: 4px;"
            >
              {{ tag }}
            </el-tag>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>

        <!-- 备注 -->
        <el-descriptions-item label="备注" :span="2">
          {{ deviceData.notes || '无' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 网卡详细信息 -->
      <el-card header="网卡信息" style="margin-top: 20px;" v-if="deviceData.nics && deviceData.nics.length > 0">
        <el-table :data="deviceData.nics">
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="bdf" label="BDF" width="120" />
          <el-table-column prop="sn" label="序列号" width="300"/>
          <!-- SOC IP列调整到MAC地址前面 -->
          <el-table-column label="SOC IP" width="200">
            <template #default="{ row }">
              <div v-if="getMv200ForNic(row.sn)" class="soc-ip-link">
                <el-link 
                  type="primary" 
                  @click="handleMv200Detail(getMv200ForNic(row.sn))"
                  class="underlined-link"
                  :underline="false"
                >
                  {{ getMv200ForNic(row.sn)?.ip_address }}
                </el-link>
              </div>
              <span v-else class="empty-text">-</span>
            </template>
          </el-table-column>
          <el-table-column label="MAC地址">
            <template #default="{ row }">
              <div v-if="row.mac && row.mac.length > 0">
                <div v-for="mac in row.mac" :key="mac" class="mac-address">
                  {{ mac }}
                </div>
              </div>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column v-if="hasAidpuNics" prop="soc_ip" label="SoC IP" />
          <el-table-column v-if="hasAidpuNics" prop="aidpu_sn" label="AIDPU SN" />
          <el-table-column v-if="hasAidpuNics" prop="firmware_version" label="固件版本" />
          <el-table-column v-if="hasAidpuNics" prop="management_ip" label="管理IP" />
        </el-table>
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Refresh, Loading } from '@element-plus/icons-vue'
import { deviceApi } from '@/api/device'
import { mv200Api } from '@/api/mv200'
import type { ServerDetailResponse, AIDPU_Nic, BootEntriesResponse, MVServer } from '@/types/api'

const route = useRoute()
const router = useRouter()
const deviceId = ref<string>('')
const refreshing = ref(false)
const bootEntriesLoading = ref(false)
const bootEntriesData = ref<BootEntriesResponse | null>(null)
const allMv200s = ref<MVServer[]>([])

const deviceData = ref<ServerDetailResponse>({
  bmc: { hostname: '', ip: '' },
  device: { ip: '', username: '' },
  nics: [],
  tags: [],
  notes: '',
  user: '',
  time: '',
  created_at: '',
  updated_at: '',
  id: ''
})

// 计算操作系统类型列表
const bootEntriesList = computed(() => {
  const bootEntries = bootEntriesData.value
  if (!bootEntries || !bootEntries.entries) return []

  const { entries, current, next, default: defaultOs } = bootEntries
  const result = []

  for (const [key, value] of Object.entries(entries)) {
    const statusFlags = []
    if (key === current) statusFlags.push('当前')
    if (key === next) statusFlags.push('下次')
    if (key === defaultOs) statusFlags.push('默认')
    
    let displayText = value
    if (statusFlags.length > 0) {
      displayText += ` (${statusFlags.join(')(')})`
    }

    result.push({
      key,
      value,
      displayText,
      isCurrent: key === current,
      isNext: key === next,
      isDefault: key === defaultOs
    })
  }

  return result
})

// 根据网卡序列号获取对应的MV200信息
const getMv200ForNic = (nicSn: string): MVServer | null => {
  if (!nicSn || !allMv200s.value.length) return null
  
  // 查找nic_sn匹配的MV200
  const matchedMv200 = allMv200s.value.find(mv200 => mv200.nic_sn === nicSn)
  return matchedMv200 || null
}

// MV200详情页面跳转
const handleMv200Detail = (mv200: MVServer | null) => {
  if (mv200 && mv200.id) {
    router.push(`/mv200/detail/${mv200.id}`)
  } else {
    ElMessage.warning('无法找到MV200详情')
  }
}

// 根据剩余秒数计算截止时间
const getEndTimeFromSeconds = (seconds: number): Date => {
  const now = new Date()
  now.setTime(now.getTime() + seconds * 1000)
  return now
}

// 统一的日期时间格式化函数
const formatDateTime = (date: Date): string => {
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  
  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`
}

// 检查服务器是否被占用
const isDeviceOccupied = computed(() => {
  const device = deviceData.value
  // 检查user和time是否有效
  const hasValidUser = device.user && device.user.trim() !== ''
  const hasValidTime = device.time !== undefined && device.time !== null && device.time > 0
  
  // 如果有有效的用户和时间，再检查时间是否过期
  if (hasValidUser && hasValidTime) {
    return device.time > 0 // 剩余时间大于0表示未过期
  }
  
  return false
})

// 根据剩余秒数显示截止时间
const getEndTimeDisplay = () => {
  const device = deviceData.value
  if (!device.time || device.time <= 0) return '-'
  
  const endTime = getEndTimeFromSeconds(device.time)
  return formatDateTime(endTime)
}

// 检查是否有AIDPU网卡
const hasAidpuNics = computed(() => {
  return deviceData.value.nics?.some(nic => 
    'soc_ip' in nic && (nic as AIDPU_Nic).soc_ip
  )
})

// 格式化时间显示
const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  try {
    return new Date(timeStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(/\//g, '/')
  } catch (error) {
    return timeStr // 如果解析失败，返回原始字符串
  }
}

// 加载所有MV200数据
const loadAllMv200s = async () => {
  try {
    const data = await mv200Api.getAll()
    allMv200s.value = data
  } catch (error) {
    console.error('加载MV200列表失败:', error)
  }
}

// 加载启动项信息
const loadBootEntries = async () => {
  try {
    bootEntriesLoading.value = true
    const data = await deviceApi.getBootEntries(deviceId.value)
    bootEntriesData.value = data
  } catch (error) {
    console.error('加载启动项信息失败:', error)
    // 不显示错误信息，因为启动项信息不是必须的
  } finally {
    bootEntriesLoading.value = false
  }
}

// 加载服务器详情
const loadDeviceDetail = async () => {
  try {
    const data = await deviceApi.getById(deviceId.value)
    deviceData.value = data
    
    // 同时加载启动项信息和MV200数据
    await Promise.all([
      loadBootEntries(),
      loadAllMv200s()
    ])
  } catch (error) {
    ElMessage.error('加载服务器详情失败')
    router.push('/devices')
  }
}

// 更新服务器信息
const handleRefresh = async () => {
  try {
    refreshing.value = true
    
    await ElMessageBox.confirm(
      '确定要更新服务器信息吗？这将重新获取服务器的硬件信息和状态。',
      '确认更新',
      {
        type: 'warning',
        confirmButtonText: '确定更新',
        cancelButtonText: '取消'
      }
    )

    // 调用自动更新接口
    await deviceApi.update(deviceId.value, { auto: true })
    
    ElMessage.success('服务器信息更新成功')
    
    // 重新加载详情数据和启动项信息
    await loadDeviceDetail()
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      // 用户取消操作，不显示错误信息
      return
    }
    ElMessage.error(error.response?.data?.detail || '更新服务器信息失败')
  } finally {
    refreshing.value = false
  }
}

// 编辑服务器
const handleEdit = () => {
  router.push(`/devices/edit/${deviceId.value}`)
}

onMounted(() => {
  deviceId.value = route.params.id as string
  if (!deviceId.value) {
    ElMessage.error('服务器ID不能为空')
    router.push('/devices')
    return
  }
  loadDeviceDetail()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.mac-address {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  margin-bottom: 2px;
}

/* SOC IP链接样式 */
.soc-ip-link {
  display: flex;
  align-items: center;
}

.soc-ip-link :deep(.el-link) {
  display: inline-flex;
  align-items: center;
  line-height: 1.4;
  padding: 0;
  margin: 0;
  font-family: 'Monaco', 'Consolas', monospace;
  font-weight: 500;
}

/* 下划线链接样式 */
.underlined-link {
  text-decoration: underline !important;
  text-underline-offset: 3px;
  text-decoration-thickness: 1px;
}

.underlined-link:hover {
  text-decoration-thickness: 2px;
}

.os-item {
  padding: 4px 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.current-os {
  background-color: #e6f7ff;
  border: 1px solid #91d5ff;
  color: #1890ff;
}

.default-os {
  background-color: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #52c41a;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

:deep(.el-descriptions) {
  margin-top: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
}

/* 更新按钮加载状态样式 */
:deep(.el-button--warning) {
  background-color: #e6a23c;
  border-color: #e6a23c;
}

:deep(.el-button--warning:hover) {
  background-color: #e6a23c;
  border-color: #e6a23c;
  opacity: 0.8;
}

:deep(.el-button--warning:focus) {
  background-color: #e6a23c;
  border-color: #e6a23c;
}
</style>