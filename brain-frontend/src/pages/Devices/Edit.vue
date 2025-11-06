<template>
  <div class="device-edit">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>编辑服务器 - {{ deviceData.bmc?.hostname }}</h2>
          <div class="header-actions">
            <el-button 
              type="warning" 
              @click="handleAutoUpdate" 
              :loading="autoUpdateLoading"
              :disabled="autoUpdateLoading"
            >
              <el-icon><Refresh /></el-icon>
              {{ autoUpdateLoading ? '更新中...' : '更新信息' }}
            </el-button>
            <el-button type="primary" @click="handleSubmit" :loading="loading">
              <el-icon><Check /></el-icon>
              保存
            </el-button>
            <el-button @click="$router.push('/devices')">取消</el-button>
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

        <!-- BMC信息 -->
        <el-descriptions-item label="服务器名称">
          <el-input 
            v-model="form.bmc.hostname" 
            placeholder="输入服务器名称"
          />
        </el-descriptions-item>
        <!-- 标签 -->
        <el-descriptions-item label="标签" :span="2">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入标签"
            style="width: 100%"
            :loading="tagsLoading"
            @blur="handleTagBlur"
            @change="handleTagChange"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag.id"
              :label="tag.name"
              :value="tag.name"
            />
          </el-select>
        </el-descriptions-item>
        <el-descriptions-item label="OS用户名">
          <el-input 
            v-model="form.device.username" 
            placeholder="输入操作系统用户名"
          />
        </el-descriptions-item>
        <el-descriptions-item label="OS密码">
          <el-input 
            v-model="form.device.password" 
            type="password"
            placeholder="如需修改密码，请在此输入新密码"
            show-password
            class="password-input"
          />
        </el-descriptions-item>
        <!-- 备注 -->
        <el-descriptions-item label="备注" :span="2">
          <el-input 
            v-model="form.notes" 
            type="textarea" 
            :rows="3" 
            placeholder="输入备注信息"
            maxlength="500"
            show-word-limit
          />
        </el-descriptions-item>
      </el-descriptions>

      <!-- 网卡详细信息 -->
      <el-card header="网卡信息" style="margin-top: 20px;" v-if="deviceData.nics && deviceData.nics.length > 0">
        <el-table :data="deviceData.nics">
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="bdf" label="BDF" width="120" />
          <el-table-column prop="sn" label="序列号" />
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
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Check, Loading } from '@element-plus/icons-vue'
import { deviceApi } from '@/api/device'
import { tagApi } from '@/api/tag'
import type { ServerDetailResponse, ServerUpdateRequest, AIDPU_Nic, TagResponse, BootEntriesResponse } from '@/types/api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const autoUpdateLoading = ref(false)
const tagsLoading = ref(false)
const bootEntriesLoading = ref(false)
const deviceId = ref<string>('')

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

const form = reactive<ServerUpdateRequest>({
  auto: false,
  bmc: {
    hostname: '',
    ip: ''
  },
  device: {
    ip: '',
    username: '',
    password: '',
    sn: ''
  },
  nics: [],
  tags: [],
  notes: '',
  time: ''
})

const availableTags = ref<TagResponse[]>([])
const bootEntriesData = ref<BootEntriesResponse | null>(null)

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

// 获取标签名称列表（用于快速查找）
const getTagNames = (): string[] => {
  return availableTags.value.map(tag => tag.name)
}

// 加载标签列表
const loadTags = async () => {
  try {
    tagsLoading.value = true
    const response = await tagApi.getTags()
    availableTags.value = response.tags || []
  } catch (error) {
    console.error('加载标签失败:', error)
    ElMessage.error('加载标签列表失败')
  } finally {
    tagsLoading.value = false
  }
}

// 创建新标签
const createTag = async (tagName: string) => {
  try {
    await tagApi.createTag({ name: tagName })
    // 创建成功后重新加载标签列表
    await loadTags()
    ElMessage.success(`标签 "${tagName}" 创建成功`)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || `创建标签 "${tagName}" 失败`)
    throw error // 重新抛出错误，让调用者处理
  }
}

// 处理标签变化
const handleTagChange = async (selectedTags: string[]) => {
  // 检查是否有新创建的标签（不在 availableTags 中）
  const tagNames = getTagNames()
  const newTags = selectedTags.filter(tag => !tagNames.includes(tag))
  
  for (const newTag of newTags) {
    if (newTag.trim()) {
      try {
        await createTag(newTag.trim())
      } catch (error) {
        // 如果创建失败，从当前选中中移除该标签
        const index = form.tags.indexOf(newTag)
        if (index > -1) {
          form.tags.splice(index, 1)
        }
      }
    }
  }
}

// 处理标签输入框失去焦点
const handleTagBlur = (event: FocusEvent) => {
  const input = event.target as HTMLInputElement
  const value = input.value?.trim()
  
  if (value && !form.tags.includes(value) && !getTagNames().includes(value)) {
    // 如果有输入值且不是已有标签，创建新标签
    createTag(value).then(() => {
      // 创建成功后添加到当前选中
      if (!form.tags.includes(value)) {
        form.tags.push(value)
      }
      input.value = '' // 清空输入框
    }).catch(() => {
      // 创建失败，不清空输入框，让用户重新输入
    })
  }
}

// 加载服务器数据
const loadDeviceData = async () => {
  try {
    const data = await deviceApi.getById(deviceId.value)
    deviceData.value = data
    
    // 填充表单数据，确保包含所有必要信息
    form.bmc.hostname = data.bmc.hostname
    form.bmc.ip = data.bmc.ip
    form.device.ip = data.device.ip
    form.device.username = data.device.username
    form.device.sn = data.device.sn || ''
    form.device.password = '' // 密码不显示，需要重新输入
    form.nics = data.nics || []
    form.tags = data.tags || []
    form.notes = data.notes || ''
    form.time = data.time || ''
    
    // 同时加载启动项信息
    await loadBootEntries()
  } catch (error) {
    ElMessage.error('加载服务器数据失败')
    router.push('/devices')
  }
}

// 自动更新 - 只传 auto: true
const handleAutoUpdate = async () => {
  try {
    // 显示确认对话框
    await ElMessageBox.confirm(
      '确定要自动更新服务器信息吗？这将重新获取服务器的硬件信息和状态。',
      '确认自动更新',
      {
        type: 'warning',
        confirmButtonText: '确定更新',
        cancelButtonText: '取消',
        confirmButtonClass: 'confirm-update-btn',
        cancelButtonClass: 'cancel-update-btn'
      }
    )

    autoUpdateLoading.value = true
    ElMessage.info('正在自动更新服务器信息...')
    
    // 只传 auto: true，不传其他服务器信息
    const updateData = {
      auto: true
    }
    
    const result = await deviceApi.update(deviceId.value, updateData)
    
    // 使用返回的数据更新表单和服务器数据
    deviceData.value = result
    form.bmc.hostname = result.bmc.hostname
    form.bmc.ip = result.bmc.ip
    form.device.ip = result.device.ip
    form.device.username = result.device.username
    form.device.sn = result.device.sn || ''
    form.nics = result.nics || []
    form.tags = result.tags || []
    form.notes = result.notes || ''
    
    // 重新加载启动项信息
    await loadBootEntries()
    
    ElMessage.success('自动更新成功')
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      // 用户取消操作，不显示错误信息
      return
    }
    ElMessage.error('自动更新失败')
  } finally {
    autoUpdateLoading.value = false
  }
}

// 手动提交
const handleSubmit = async () => {
  loading.value = true
  try {
    const submitData = {
      ...form,
      auto: false // 手动更新
    }
    
    // 确保提交的数据包含所有必要的服务器信息
    if (!submitData.device.ip) {
      submitData.device.ip = deviceData.value.device.ip
    }
    if (!submitData.device.sn) {
      submitData.device.sn = deviceData.value.device.sn || ''
    }
    if (!submitData.nics || submitData.nics.length === 0) {
      submitData.nics = deviceData.value.nics || []
    }
    
    await deviceApi.update(deviceId.value, submitData)
    ElMessage.success('更新成功')
    router.push('/devices')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  deviceId.value = route.params.id as string
  if (!deviceId.value) {
    ElMessage.error('服务器ID不能为空')
    router.push('/devices')
    return
  }
  loadDeviceData()
  loadTags()
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

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

/* 操作系统类型样式 */
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

/* 修复密码输入框样式 - 强制显示眼睛图标 */
.password-input {
  :deep(.el-input__wrapper) {
    padding-right: 40px; /* 为图标预留固定空间 */
  }
  
  :deep(.el-input__suffix) {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    width: 32px;
  }
  
  :deep(.el-input__suffix-inner) {
    display: flex !important;
    align-items: center;
    justify-content: center;
  }
  
  /* 当没有内容时，显示一个透明的占位图标 */
  :deep(.el-input__suffix .el-icon:first-child) {
    visibility: visible !important;
    opacity: 0.3; /* 半透明显示，表示不可用状态 */
  }
  
  /* 当有内容时，正常显示 */
  :deep(.el-input--suffix .el-input__wrapper:not(.is-focus):hover .el-input__suffix .el-icon:first-child),
  :deep(.el-input--suffix .el-input__wrapper.is-focus .el-input__suffix .el-icon:first-child) {
    opacity: 1;
  }
}

:deep(.el-descriptions) {
  margin-top: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
}

:deep(.el-descriptions__content) {
  align-items: center;
}

/* 确保所有输入框宽度一致 */
:deep(.el-input) {
  width: 100%;
}

/* 修复密码输入框与其他输入框的对齐 */
:deep(.el-descriptions__cell) {
  vertical-align: middle;
}

/* 自动更新按钮样式 */
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

:deep(.el-button--warning.is-disabled) {
  background-color: #fabf78;
  border-color: #fabf78;
  opacity: 0.6;
}
</style>