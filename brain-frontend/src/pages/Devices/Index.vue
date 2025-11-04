<template>
  <div class="device-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>服务器管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索服务器名称、IP、标签、占用人"
              clearable
              style="width: 350px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="$router.push('/devices/create')">
              录入服务器
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="filteredDevices" 
        v-loading="loading"
        :default-sort="{ prop: 'device.ip', order: 'ascending' }"
      >
        <el-table-column 
          prop="bmc.hostname" 
          label="服务器名称"
          sortable
          width="180"
        >
          <template #default="{ row }">
            <el-link 
              type="primary" 
              @click="handleDetail(row)"
              class="hostname-link underlined-link"
              :underline="false"
            >
              {{ row.bmc.hostname }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column 
          prop="device.ip" 
          label="服务器管理IP"
          sortable
          :sort-method="ipSortMethod"
          width="150"
        >
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.device.ip }}</span>
          </template>
        </el-table-column>
        <el-table-column 
          prop="bmc.ip" 
          label="BMC IP"
          sortable
          :sort-method="ipSortMethod"
          width="150"
        >
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.bmc.ip }}</span>
          </template>
        </el-table-column>
        <el-table-column 
          label="标签"
          min-width="200"
        >
          <template #default="{ row }">
            <div v-if="row.tags && row.tags.length > 0" class="tags-container">
              <el-tag 
                v-for="tag in row.tags" 
                :key="tag" 
                size="small"
                closable
                @close="(e) => handleRemoveTag(e, tag, row)"
                class="tag-item"
              >
                {{ tag }}
              </el-tag>
              <el-button 
                type="primary" 
                text 
                size="small" 
                @click="showAddTagDialog(row)"
                class="add-tag-btn"
              >
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>
            <div v-else class="no-tags">
              <span class="empty-text">-</span>
              <el-button 
                type="primary" 
                text 
                size="small" 
                @click="showAddTagDialog(row)"
              >
                <el-icon><Plus /></el-icon>
                添加标签
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column 
          prop="notes" 
          label="备注"
          show-overflow-tooltip
          min-width="250"
        >
          <template #default="{ row }">
            <span v-if="row.notes">{{ row.notes }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column 
          prop="user" 
          label="当前占用人"
          sortable
          width="120"
        >
          <template #default="{ row }">
            <el-tag v-if="isDeviceOccupied(row)" type="success" size="small">{{ row.user }}</el-tag>
            <el-tag v-else type="info" size="small">未占用</el-tag>
          </template>
        </el-table-column>
        <el-table-column 
          label="占用截至时间"
          sortable
          :sort-method="timeSortMethod"
          width="180"
        >
          <template #default="{ row }">
            <span v-if="isDeviceOccupied(row) && row.time">{{ getEndTimeDisplay(row) }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button type="primary" link>
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu class="action-dropdown-menu">
                  <el-dropdown-item command="detail" class="dropdown-item">
                    <el-icon><View /></el-icon>
                    <span>详情</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="edit" class="dropdown-item">
                    <el-icon><Edit /></el-icon>
                    <span>编辑</span>
                  </el-dropdown-item>
                  
                  <!-- 占用服务器按钮 -->
                  <el-dropdown-item 
                    command="occupy" 
                    :disabled="isDeviceOccupied(row) && !isCurrentUserOccupier(row)"
                    class="occupy-item occupy-server-item dropdown-item"
                  >
                    <el-icon><Timer /></el-icon>
                    <span>
                      {{ getOccupyButtonText(row) }}
                    </span>
                    <el-tooltip 
                      v-if="isDeviceOccupied(row) && !isCurrentUserOccupier(row)"
                      effect="dark" 
                      content="当前服务器已被占用，请联系占用人"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  
                  <!-- 结束占用按钮 -->
                  <el-dropdown-item 
                    command="release" 
                    :disabled="!isDeviceOccupied(row) || !isCurrentUserOccupier(row)"
                    class="occupy-item end-occupy-item dropdown-item"
                  >
                    <el-icon><Unlock /></el-icon>
                    <span>结束占用</span>
                    <el-tooltip 
                      v-if="!isDeviceOccupied(row)"
                      effect="dark" 
                      content="服务器未被占用"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                    <el-tooltip 
                      v-else-if="isDeviceOccupied(row) && !isCurrentUserOccupier(row)"
                      effect="dark" 
                      content="当前用户不是占用人，请联系占用人"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided class="danger-item dropdown-item">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 占用/修改时间对话框 -->
    <el-dialog
      v-model="occupyDialogVisible"
      :title="occupyDialogTitle"
      width="480px"
      class="occupy-dialog"
      :close-on-click-modal="false"
    >
      <div class="dialog-header">
        <div class="device-info">
          <el-icon class="server-icon"><Monitor /></el-icon>
          <div class="info-content">
            <div class="hostname">{{ currentDevice?.bmc.hostname }}</div>
            <div class="ip-address">{{ currentDevice?.device.ip }}</div>
          </div>
        </div>
        <div class="user-info">
          <el-avatar :size="32" style="background-color: #409eff;">
            {{ currentUser?.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="username">{{ currentUser }}</span>
        </div>
      </div>

      <div v-if="isModifyMode && currentDevice?.time" class="original-time">
        <el-icon><Clock /></el-icon>
        <span>原截止时间：</span>
        <strong>{{ getEndTimeDisplay(currentDevice) }}</strong>
      </div>

      <el-form :model="occupyForm" class="occupy-form" label-width="auto">
        <div class="form-section">
          <div class="section-title">
            <el-icon><Calendar /></el-icon>
            <span>{{ isModifyMode ? '设置新的结束时间' : '设置占用结束时间' }}</span>
          </div>
          
          <el-form-item class="compact-item">
            <template #label>
              <span class="form-label">结束时间</span>
              <span class="required">*</span>
            </template>
            <el-date-picker
              v-model="occupyForm.endTime"
              type="datetime"
              placeholder="选择占用结束时间"
              style="width: 100%"
              :disabled-date="disabledDate"
              :shortcuts="timeShortcuts"
              class="enhanced-picker"
            />
          </el-form-item>

          <el-form-item class="compact-item">
            <template #label>
              <span class="form-label">占用时长</span>
            </template>
            <div class="duration-display">
              <el-tag 
                :type="getDurationType()" 
                class="duration-tag"
                :class="getDurationSize()"
              >
                <el-icon><Watch /></el-icon>
                {{ calculateDuration() }}
              </el-tag>
              <div v-if="occupyForm.endTime" class="duration-detail">
                <span class="end-time">截止: {{ getEndTimeDisplayFromForm() }}</span>
              </div>
            </div>
          </el-form-item>
        </div>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="occupyDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handleOccupy" 
            :loading="occupyLoading"
            :disabled="!occupyForm.endTime"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            {{ isModifyMode ? '确认修改' : '确认占用' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 添加标签对话框 -->
    <el-dialog
      v-model="showAddTagDialogVisible"
      title="管理标签"
      width="500px"
      :before-close="handleTagDialogClose"
    >
      <div class="tag-dialog-content">
        <div class="tag-selection">
          <div class="dialog-tip">选择已有标签或输入新标签</div>
          <el-select
            v-model="selectedTags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入标签"
            style="width: 100%"
            :loading="tagsLoading"
            @blur="handleTagBlur"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag.id"
              :label="tag.name"
              :value="tag.name"
            />
          </el-select>
        </div>
        
        <div class="existing-tags" v-if="availableTags.length > 0">
          <div class="dialog-tip">已有标签</div>
          <div class="tags-list">
            <el-tag
              v-for="tag in availableTags"
              :key="tag.id"
              :type="isTagSelected(tag.name) ? 'primary' : 'info'"
              class="tag-item"
              @click="toggleTag(tag.name)"
            >
              {{ tag.name }}
            </el-tag>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="handleTagDialogClose">取消</el-button>
        <el-button type="primary" @click="handleAddTags" :loading="addingTags">
          确认更新
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  MoreFilled, 
  Edit, 
  Delete, 
  Search, 
  View, 
  Timer, 
  Unlock, 
  InfoFilled, 
  Plus,
  Monitor,
  Clock,
  Calendar,
  Watch,
  Loading
} from '@element-plus/icons-vue'
import { deviceApi } from '@/api/device'
import { tagApi } from '@/api/tag'
import type { ServerDetailResponse, ServerUpdateRequest, TagResponse } from '@/types/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const devices = ref<ServerDetailResponse[]>([])
const searchKeyword = ref('')

// 当前用户信息
const currentUser = computed(() => authStore.username)

// 占用服务器相关
const occupyDialogVisible = ref(false)
const occupyLoading = ref(false)
const currentDevice = ref<ServerDetailResponse | null>(null)
const occupyForm = reactive({
  endTime: null as Date | null
})

// 标签管理相关
const showAddTagDialogVisible = ref(false)
const selectedTags = ref<string[]>([])
const availableTags = ref<TagResponse[]>([])
const tagsLoading = ref(false)
const addingTags = ref(false)
const editingDevice = ref<ServerDetailResponse | null>(null)

// 时间快捷选项
const timeShortcuts = [
  {
    text: '1小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3600 * 1000)
      return date
    }
  },
  {
    text: '2小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 2 * 3600 * 1000)
      return date
    }
  },
  {
    text: '4小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 4 * 3600 * 1000)
      return date
    }
  },
  {
    text: '8小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 8 * 3600 * 1000)
      return date
    }
  },
  {
    text: '1天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 24 * 3600 * 1000)
      return date
    }
  },
  {
    text: '3天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3 * 24 * 3600 * 1000)
      return date
    }
  },
  {
    text: '7天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 7 * 24 * 3600 * 1000)
      return date
    }
  }
]

// 根据剩余秒数计算截止时间
const getEndTimeFromSeconds = (seconds: number): Date => {
  const now = new Date()
  now.setTime(now.getTime() + seconds * 1000)
  return now
}

// 根据截止时间计算剩余秒数
const getSecondsFromEndTime = (endTime: Date): number => {
  const now = new Date()
  return Math.floor((endTime.getTime() - now.getTime()) / 1000)
}

// 检查设备是否被占用（考虑时间过期）
const isDeviceOccupied = (device: ServerDetailResponse) => {
  // 检查user和time是否有效
  const hasValidUser = device.user && device.user.trim() !== ''
  const hasValidTime = device.time !== undefined && device.time !== null && device.time > 0
  
  // 如果有有效的用户和时间，再检查时间是否过期
  if (hasValidUser && hasValidTime) {
    return device.time > 0 // 剩余时间大于0表示未过期
  }
  
  return false
}

// 根据剩余秒数显示截止时间 - 统一使用 YYYY/MM/DD HH:mm:ss 格式
const getEndTimeDisplay = (device: ServerDetailResponse) => {
  if (!device.time || device.time <= 0) return '-'
  
  const endTime = getEndTimeFromSeconds(device.time)
  return formatDateTime(endTime)
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

// 检查当前用户是否是占用人
const isCurrentUserOccupier = (device: ServerDetailResponse) => {
  return device.user === currentUser.value
}

// 获取占用按钮文本
const getOccupyButtonText = (device: ServerDetailResponse) => {
  if (isDeviceOccupied(device) && isCurrentUserOccupier(device)) {
    return '修改占用'
  }
  return '占用服务器'
}

// 检查是否为修改模式
const isModifyMode = computed(() => {
  return currentDevice.value && 
         isDeviceOccupied(currentDevice.value) && 
         isCurrentUserOccupier(currentDevice.value)
})

// 获取对话框标题
const occupyDialogTitle = computed(() => {
  return isModifyMode.value ? '修改占用' : '占用服务器'
})

// 禁用过去的日期
const disabledDate = (time: Date) => {
  return time.getTime() < Date.now() - 24 * 60 * 60 * 1000 // 禁用昨天及之前的日期
}

// 计算占用时长（显示用）
const calculateDuration = () => {
  if (!occupyForm.endTime) return '-'
  
  const now = new Date()
  const endTime = new Date(occupyForm.endTime)
  const durationMs = endTime.getTime() - now.getTime()
  
  if (durationMs <= 0) return '结束时间必须晚于当前时间'
  
  const seconds = Math.floor(durationMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) {
    return `${days}天${hours % 24}小时${minutes % 60}分钟`
  } else if (hours > 0) {
    return `${hours}小时${minutes % 60}分钟`
  } else {
    return `${minutes}分钟`
  }
}

// 获取持续秒数
const getDurationSeconds = () => {
  if (!occupyForm.endTime) return 0
  
  const now = new Date()
  const endTime = new Date(occupyForm.endTime)
  const durationMs = endTime.getTime() - now.getTime()
  
  return Math.floor(durationMs / 1000)
}

// 获取时长类型
const getDurationType = () => {
  if (!occupyForm.endTime) return 'info'
  
  const seconds = getDurationSeconds()
  const hours = seconds / 3600
  
  if (hours <= 1) return 'danger'
  if (hours <= 4) return 'warning'
  return 'success'
}

// 获取时长标签大小
const getDurationSize = () => {
  if (!occupyForm.endTime) return ''
  
  const durationText = calculateDuration()
  if (durationText.length > 10) return 'duration-large'
  return ''
}

// 获取结束时间显示（表单用）- 统一使用 YYYY/MM/DD HH:mm:ss 格式
const getEndTimeDisplayFromForm = () => {
  if (!occupyForm.endTime) return ''
  
  const endTime = new Date(occupyForm.endTime)
  return formatDateTime(endTime)
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

// 检查标签是否已选中
const isTagSelected = (tagName: string) => {
  return selectedTags.value.includes(tagName)
}

// 切换标签选中状态
const toggleTag = (tagName: string) => {
  const index = selectedTags.value.indexOf(tagName)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    selectedTags.value.push(tagName)
  }
}

// 处理标签输入框失去焦点
const handleTagBlur = async (event: FocusEvent) => {
  const input = event.target as HTMLInputElement
  const value = input.value?.trim()
  
  if (value && !selectedTags.value.includes(value) && !availableTags.value.some(tag => tag.name === value)) {
    // 如果有输入值且不是已有标签，创建新标签
    try {
      await tagApi.createTag({ name: value })
      await loadTags() // 重新加载标签列表
      if (!selectedTags.value.includes(value)) {
        selectedTags.value.push(value)
      }
      input.value = '' // 清空输入框
      ElMessage.success(`标签 "${value}" 创建成功`)
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || `创建标签 "${value}" 失败`)
    }
  }
}

// 移除标签
const handleRemoveTag = async (event: Event, tagName: string, device: ServerDetailResponse) => {
  event.stopPropagation() // 阻止事件冒泡
  
  try {
    await ElMessageBox.confirm(`确定要从设备 "${device.bmc.hostname}" 中移除标签 "${tagName}" 吗？`, '提示', {
      type: 'warning'
    })

    const updatedTags = device.tags?.filter(tag => tag !== tagName) || []
    
    await deviceApi.update(device.id!, {
      tags: updatedTags,
      auto: false,
      device: {
        ip: device.device.ip,
        username: device.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: device.bmc.hostname,
        ip: device.bmc.ip
      },
      notes: device.notes || '',
      os_types: device.os_types || []
    })
    
    // 更新本地数据
    const deviceIndex = devices.value.findIndex(d => d.id === device.id)
    if (deviceIndex > -1) {
      devices.value[deviceIndex].tags = updatedTags
    }
    
    ElMessage.success('标签移除成功')
  } catch (error) {
    // 用户取消操作
  }
}

// 显示添加标签对话框
const showAddTagDialog = (device: ServerDetailResponse) => {
  editingDevice.value = device
  selectedTags.value = [...(device.tags || [])]
  showAddTagDialogVisible.value = true
}

// 添加标签
const handleAddTags = async () => {
  if (!editingDevice.value) return

  try {
    addingTags.value = true
    
    await deviceApi.update(editingDevice.value.id!, {
      tags: selectedTags.value,
      auto: false,
      device: {
        ip: editingDevice.value.device.ip,
        username: editingDevice.value.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: editingDevice.value.bmc.hostname,
        ip: editingDevice.value.bmc.ip
      },
      notes: editingDevice.value.notes || '',
      os_types: editingDevice.value.os_types || []
    })
    
    // 更新本地数据
    const deviceIndex = devices.value.findIndex(d => d.id === editingDevice.value!.id)
    if (deviceIndex > -1) {
      devices.value[deviceIndex].tags = selectedTags.value
    }
    
    showAddTagDialogVisible.value = false
    ElMessage.success('标签更新成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新标签失败')
  } finally {
    addingTags.value = false
  }
}

// 处理标签对话框关闭
const handleTagDialogClose = () => {
  showAddTagDialogVisible.value = false
  editingDevice.value = null
}

// IP地址排序函数
const ipSortMethod = (a: ServerDetailResponse, b: ServerDetailResponse) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const ipA = ipToNumber(a.device.ip);
  const ipB = ipToNumber(b.device.ip);
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

// 时间排序函数
const timeSortMethod = (a: ServerDetailResponse, b: ServerDetailResponse) => {
  const timeA = a.time || 0;
  const timeB = b.time || 0;
  return timeA - timeB;
};

// 计算属性：过滤设备列表
const filteredDevices = computed(() => {
  let filtered = devices.value
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = devices.value.filter(device => {
      // 搜索服务器名称
      if (device.bmc.hostname.toLowerCase().includes(keyword)) return true
      
      // 搜索服务器管理IP
      if (device.device.ip.toLowerCase().includes(keyword)) return true
      
      // 搜索BMC IP
      if (device.bmc.ip.toLowerCase().includes(keyword)) return true
      
      // 搜索标签
      if (device.tags && device.tags.some(tag => tag.toLowerCase().includes(keyword))) return true
      
      // 搜索备注
      if (device.notes && device.notes.toLowerCase().includes(keyword)) return true
      
      // 搜索占用人
      if (device.user && device.user.toLowerCase().includes(keyword)) return true
      
      return false
    })
  }
  
  return filtered
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

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const data = await deviceApi.getAll()
    devices.value = data
  } catch (error) {
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理
}

// 下拉菜单命令处理
const handleCommand = (command: string, device: ServerDetailResponse) => {
  switch (command) {
    case 'detail':
      handleDetail(device)
      break
    case 'edit':
      handleEdit(device)
      break
    case 'occupy':
      handleOccupyDialog(device)
      break
    case 'release':
      handleRelease(device)
      break
    case 'delete':
      handleDelete(device)
      break
  }
}

// 查看详情 - 点击服务器名称或详情按钮
const handleDetail = (device: ServerDetailResponse) => {
  router.push(`/devices/detail/${device.id}`)
}

// 编辑
const handleEdit = (device: ServerDetailResponse) => {
  router.push(`/devices/edit/${device.id}`)
}

// 打开占用服务器对话框
const handleOccupyDialog = (device: ServerDetailResponse) => {
  currentDevice.value = device
  
  // 设置默认结束时间
  let defaultEndTime = new Date()
  defaultEndTime.setTime(defaultEndTime.getTime() + 60 * 60 * 1000) // 默认1小时后
  
  // 如果是修改模式，且设备有剩余时间，使用原剩余时间计算新的截止时间
  if (isModifyMode.value && device.time && device.time > 0) {
    defaultEndTime = getEndTimeFromSeconds(device.time)
  }
  
  occupyForm.endTime = defaultEndTime
  occupyDialogVisible.value = true
}

// 占用/修改时间服务器
const handleOccupy = async () => {
  if (!currentDevice.value || !occupyForm.endTime) return
  
  try {
    occupyLoading.value = true
    
    // 计算持续秒数
    const durationSeconds = getDurationSeconds()
    
    const updateData: ServerUpdateRequest = {
      auto: false,
      time: durationSeconds, // 传持续秒数
      // user字段后端会通过token自动获取当前用户
      device: {
        ip: currentDevice.value.device.ip,
        username: currentDevice.value.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: currentDevice.value.bmc.hostname,
        ip: currentDevice.value.bmc.ip
      },
      tags: currentDevice.value.tags || [],
      notes: currentDevice.value.notes || '',
      os_types: currentDevice.value.os_types || []
    }
    
    await deviceApi.update(currentDevice.value.id!, updateData)
    ElMessage.success(`已成功${isModifyMode.value ? '修改占用' : '占用'}服务器 ${currentDevice.value.bmc.hostname}`)
    occupyDialogVisible.value = false
    loadData() // 重新加载数据
  } catch (error) {
    ElMessage.error(`${isModifyMode.value ? '修改占用' : '占用'}服务器失败`)
  } finally {
    occupyLoading.value = false
  }
}

// 结束占用
const handleRelease = async (device: ServerDetailResponse) => {
  if (!isDeviceOccupied(device)) {
    ElMessage.warning('服务器未被占用，无法释放')
    return
  }
  
  if (!isCurrentUserOccupier(device)) {
    ElMessage.warning('您不是当前占用人，无法释放该服务器')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要结束占用 "${device.bmc.hostname}" 吗？`, 
      '确认结束', 
      {
        type: 'warning',
      }
    )

    const updateData: ServerUpdateRequest = {
      auto: false,
      time: 0, // 设置为0表示结束占用
      // user字段后端会自动处理
      device: {
        ip: device.device.ip,
        username: device.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: device.bmc.hostname,
        ip: device.bmc.ip
      },
      tags: device.tags || [],
      notes: device.notes || '',
      os_types: device.os_types || []
    }
    
    await deviceApi.update(device.id!, updateData)
    ElMessage.success('服务器已释放')
    loadData() // 重新加载数据
  } catch (error) {
    // 用户取消释放
  }
}

// 删除
const handleDelete = async (device: ServerDetailResponse) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备 "${device.bmc.hostname}" 吗？`, 
      '确认删除', 
      {
        type: 'warning',
      }
    )

    await deviceApi.delete(device.id!)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    // 用户取消删除
  }
}

onMounted(() => {
  loadData()
  loadTags()
})
</script>

<style scoped>
/* 服务器名称链接样式 - 添加下划线 */
.underlined-link {
  text-decoration: underline !important;
  text-underline-offset: 3px;
  text-decoration-thickness: 1px;
}

.underlined-link:hover {
  text-decoration-thickness: 2px;
}

/* 操作下拉菜单样式优化 */
:deep(.action-dropdown-menu) {
  min-width: 140px;
}

:deep(.dropdown-item) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  text-align: left !important;
}

:deep(.dropdown-item .el-dropdown-menu__item) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  padding: 8px 12px !important;
}

:deep(.dropdown-item .el-icon) {
  margin-right: 8px !important;
  flex-shrink: 0 !important;
}

:deep(.dropdown-item span) {
  flex: 1 !important;
  text-align: left !important;
}

/* 占用相关按钮样式优化 */
:deep(.occupy-item) {
  font-weight: 600 !important;
}

:deep(.occupy-server-item:not(.is-disabled)) {
  color: #409eff !important;
}

:deep(.occupy-server-item:not(.is-disabled):hover) {
  color: #337ecc !important;
  background-color: #f0f7ff !important;
}

:deep(.end-occupy-item:not(.is-disabled)) {
  color: #67c23a !important;
}

:deep(.end-occupy-item:not(.is-disabled):hover) {
  color: #529b2e !important;
  background-color: #f0f9eb !important;
}

:deep(.action-text) {
  font-weight: 600;
  margin-left: 6px;
}

/* 表格列宽优化 */
:deep(.el-table .cell) {
  padding: 0 8px;
}

:deep(.el-table th) {
  padding: 8px 0;
}

:deep(.el-table td) {
  padding: 8px 0;
}

/* 标签容器样式优化 */
.tags-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.tag-item {
  margin: 0 !important;
  flex-shrink: 0;
}

.add-tag-btn {
  margin: 0 !important;
  flex-shrink: 0;
}

/* 对话框样式 */
.occupy-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 20px 0;
    margin-right: 0;
  }
  
  :deep(.el-dialog__body) {
    padding: 16px 20px;
  }
  
  :deep(.el-dialog__footer) {
    padding: 0 20px 20px;
  }
}

/* 对话框头部 */
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #e2e8f0;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.server-icon {
  font-size: 24px;
  color: #409eff;
}

.info-content .hostname {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.info-content .ip-address {
  font-size: 12px;
  color: #6b7280;
  font-family: 'Monaco', 'Consolas', monospace;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.username {
  font-weight: 500;
  color: #374151;
}

/* 原时间显示 */
.original-time {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fffbf0;
  border: 1px solid #fef3c7;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
  color: #92400e;
}

.original-time .el-icon {
  color: #d97706;
}

/* 表单区域 */
.form-section {
  background: white;
  border-radius: 8px;
  padding: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f3f4f6;
}

.section-title .el-icon {
  color: #409eff;
}

/* 紧凑表单项 */
.compact-item {
  margin-bottom: 20px;
  
  :deep(.el-form-item__label) {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;
    color: #374151;
    padding-right: 12px;
  }
}

.form-label {
  font-size: 14px;
}

.required {
  color: #f56c6c;
}

.enhanced-picker {
  :deep(.el-input__wrapper) {
    border-radius: 6px;
    transition: all 0.3s ease;
    
    &:hover {
      border-color: #409eff;
      box-shadow: 0 0 0 1px #409eff;
    }
  }
  
  :deep(.el-input__inner) {
    text-align: center;
    font-weight: 500;
  }
}

/* 时长显示 */
.duration-display {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.duration-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  
  &.duration-large {
    font-size: 15px;
    padding: 10px 16px;
  }
}

.duration-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.end-time {
  color: #6b7280;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 13px;
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.cancel-btn {
  width: 100px;
}

.confirm-btn {
  width: 120px;
  font-weight: 600;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .dialog-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .user-info {
    align-self: flex-end;
  }
}

/* 其他现有样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.hostname-link {
  font-weight: 500;
}

.highlight-ip {
  font-family: 'Monaco', 'Consolas', monospace;
  font-weight: 500;
}

.no-tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-text {
  color: #c0c4cc;
}

.danger-item {
  color: #f56c6c;
}

.danger-item:hover {
  color: #f56c6c;
  background-color: #fef0f0;
}

.occupy-item:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}
</style>