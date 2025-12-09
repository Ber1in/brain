<template>
  <div class="mv200-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>MV200管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索名称、SOC IP、关联服务器或描述"
              clearable
              style="width: 350px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            
            <!-- 批量删除按钮 -->
            <el-button 
              type="danger" 
              @click="handleBatchDelete" 
              :disabled="selectedServers.length === 0"
              style="margin-right: 12px;"
            >
              批量删除
            </el-button>
            
            <el-button type="primary" @click="$router.push('/mv200/create')">
              纳管MV200
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="filteredServers" 
        v-loading="loading"
        :default-sort="{ prop: 'ip_address', order: 'ascending' }"
        @selection-change="handleSelectionChange"
      >
        <!-- 多选列 -->
        <el-table-column type="selection" width="35" />

        <el-table-column 
          prop="name" 
          label="名称"
          sortable
          width="120"
        >
          <template #default="{ row }">
            <el-link 
              type="primary" 
              @click="handleDetail(row)"
              class="hostname-link underlined-link"
              :underline="false"
            >
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column 
          prop="ip_address" 
          label="SOC IP"
          sortable
          :sort-method="ipSortMethod"
          width="130"
        >
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.ip_address }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联服务器" width="150">
          <template #default="{ row }">
            <div class="associated-server-cell">
              <template v-if="!row.associatedServer">
                <span class="empty-text">-</span>
              </template>
              <template v-else>
                <!-- 正常匹配状态 -->
                <div v-if="row.associatedServer.status === 'matched'" class="matched-info">
                  <el-link 
                    type="primary" 
                    @click="handleServerDetail(row.associatedServer.data)"
                    class="server-link underlined-link"
                    :underline="false"
                  >
                    {{ row.associatedServer.data.ip }}
                  </el-link>
                </div>
                
                <!-- 服务器未纳管状态 - 使用el-tag -->
                <div v-else-if="row.associatedServer.status === 'not_managed'" class="not-managed-info">
                  <el-tooltip 
                    effect="dark" 
                    content="该MV200所在的服务器尚未纳管，去纳管" 
                    placement="top"
                  >
                    <el-tag 
                      size="small"
                      type="primary"
                      effect="plain"
                      class="create-device-tag"
                      @click="navigateToCreateDevice(row.nic_sn)"
                      style="cursor: pointer;"
                    >
                      <el-icon><Plus /></el-icon>
                      去纳管
                    </el-tag>
                  </el-tooltip>
                </div>
                
                <!-- 匹配异常状态 - 使用el-tag -->
                <div v-else-if="row.associatedServer.status === 'multiple_matched'" class="error-info">
                  <el-tooltip 
                    effect="dark" 
                    placement="top"
                    :content="getMultipleMatchTooltip(row.associatedServer)"
                  >
                    <el-tag 
                      size="small"
                      type="danger"
                      effect="plain"
                      class="error-tag"
                      style="cursor: help;"
                    >
                      <el-icon><Warning /></el-icon>
                      匹配异常
                    </el-tag>
                  </el-tooltip>
                </div>
                
                <!-- 默认状态 -->
                <span v-else class="empty-text">-</span>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="MCR版本" width="200">
          <template #default="{ row }">
            <div class="mcr-version">
              <template v-if="row.mcrVersionLoading">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <span class="status-text">查询中...</span>
              </template>
              <template v-else-if="row.mcrVersionError">
                <el-tooltip effect="dark" content="无法获取MCR版本，设备可能离线" placement="top">
                  <el-icon class="error-icon"><Warning /></el-icon>
                </el-tooltip>
                <span class="status-text">离线</span>
              </template>
              <template v-else>
                <span class="version-text">{{ row.versions?.driver || '未知' }}</span>
              </template>
            </div>
          </template>
        </el-table-column>
        <!-- 新增：MCR状态列 -->
        <el-table-column 
          label="MCR状态"
          width="110"
        >
          <template #default="{ row }">
            <div v-if="row.task_id" class="mcr-status">
              <template v-if="!taskStatusMap[row.task_id]">
                <!-- 状态查询中 -->
                <el-icon class="loading-spinner"><Loading /></el-icon>
                <span class="status-text">查询中...</span>
              </template>
              <template v-else>
                <el-tooltip
                  placement="top"
                  popper-class="mcr-status-tooltip"
                >
                  <template #content>
                    <div class="mcr-tooltip-content">
                      <div>步骤: {{ getStageText(getTaskStage(row)) }}</div>
                      <div>MCR: {{ getMcrPackage(row) }}</div>
                      <div v-if="getTaskDetail(row)" class="detail-section">
                        <div>详情:</div>
                        <pre class="detail-text">{{ cleanAnsiCodes(getTaskDetail(row)) }}</pre>
                      </div>
                    </div>
                  </template>
                  <el-tag 
                    :type="getMcrStatusType(row)" 
                    size="small"
                    class="mcr-status-tag"
                  >
                    {{ getMcrStatusText(row) }}
                  </el-tag>
                </el-tooltip>
                <el-icon 
                  v-if="getMcrStatus(row) === 'running'" 
                  class="loading-spinner"
                >
                  <Loading />
                </el-icon>
              </template>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="clouddisk_enable" label="支持云盘启动" width="140">
          <template #header>
            <span>支持云盘启动</span>
            <el-tooltip 
              effect="dark" 
              content="当支持云盘启动时，在主机启动阶段会一直等待dpu ready，直到准备好云系统盘"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <div class="clouddisk-status">
              <template v-if="row.clouddiskStatusLoading">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <span class="status-text">查询中...</span>
              </template>
              <template v-else-if="row.clouddiskStatusError">
                <el-tooltip effect="dark" content="无法获取状态，设备可能离线，请稍后刷新重试" placement="top">
                  <el-icon class="error-icon"><Warning /></el-icon>
                </el-tooltip>
                <span class="status-text">离线</span>
              </template>
              <template v-else>
                <el-switch
                  v-model="row.clouddisk_enable"
                  :loading="row.switchLoading"
                  active-text="是"
                  inactive-text="否"
                  @change="(value) => handleSwitchChange(value, row)"
                />
              </template>
            </div>
          </template>
        </el-table-column>
        <!-- 修改恢复模式列为开关形式 -->
        <el-table-column label="恢复模式" width="140">
          <template #header>
            <span>恢复模式</span>
            <el-tooltip 
              effect="dark" 
              content="手动模式：重启后不自动执行恢复，可手动执行；自动模式：重启后系统会自动执行资源恢复操作"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <div class="recovery-mode">
              <template v-if="row.recoveryModeLoading">
                <el-icon class="loading-icon"><Loading /></el-icon>
                <span class="status-text">查询中...</span>
              </template>
              <template v-else-if="row.recoveryModeError">
                <el-tooltip effect="dark" content="无法获取恢复模式，设备可能离线" placement="top">
                  <el-icon class="error-icon"><Warning /></el-icon>
                </el-tooltip>
                <span class="status-text">离线</span>
              </template>
              <template v-else>
                <el-switch
                  v-model="row.recovery_mode"
                  :loading="row.recoveryModeSwitching"
                  active-value="auto"
                  inactive-value="manual"
                  active-text="自动"
                  inactive-text="手动"
                  @change="(value) => handleRecoveryModeChange(value, row)"
                />
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
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
                  <el-dropdown-item 
                    command="edit" 
                    class="dropdown-item"
                    :disabled="row.clouddiskStatusLoading || row.clouddiskStatusError"
                  >
                    <el-tooltip
                      v-if="row.clouddiskStatusLoading"
                      effect="dark"
                      content="设备状态查询中，请稍候..."
                      placement="left"
                    >
                      <div class="dropdown-item-content">
                        <el-icon><Edit /></el-icon>
                        <span>编辑</span>
                      </div>
                    </el-tooltip>
                    <el-tooltip
                      v-else-if="row.clouddiskStatusError"
                      effect="dark"
                      content="设备离线，无法编辑，设备在线后刷新重试"
                      placement="left"
                    >
                      <div class="dropdown-item-content">
                        <el-icon><Edit /></el-icon>
                        <span>编辑</span>
                      </div>
                    </el-tooltip>
                    <div v-else class="dropdown-item-content">
                      <el-icon><Edit /></el-icon>
                      <span>编辑</span>
                    </div>
                  </el-dropdown-item>
                  
                  <!-- 新增：更新MCR包 -->
                  <el-dropdown-item 
                    command="updateMcr" 
                    class="dropdown-item update-mcr-item"
                    @click="handleUpdateMcrDialog(row)"
                  >
                    <el-icon><Upload /></el-icon>
                    <span>更新MCR包</span>
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

    <!-- 新增：更新MCR包对话框 -->
    <el-dialog
      v-model="updateMcrDialogVisible"
      title="更新MCR包"
      width="800px"
      class="update-mcr-dialog"
      :close-on-click-modal="false"
    >
      <div class="update-mcr-content" v-loading="mcrLoading">
        <div class="dialog-header">
          <div class="device-info">
            <el-icon class="server-icon"><Monitor /></el-icon>
            <div class="info-content">
              <div class="hostname">{{ currentServer?.name }}</div>
              <div class="ip-address">{{ currentServer?.ip_address }}</div>
            </div>
          </div>
          <div class="current-path">
            <el-input
              v-model="currentPathInput"
              @keyup.enter="handlePathInputEnter"
              @blur="handlePathInputBlur"
              class="path-input"
            />
          </div>
        </div>

        <div class="file-browser">
          <div class="section-title">
            <div class="title-left">
              <el-icon><Folder /></el-icon>
              <span>选择MCR包文件</span>
              <el-input
                v-model="fileFilterText"
                placeholder="筛选文件或文件夹..."
                clearable
                style="width: 150px; margin-left: 16px;"
                size="small"
                :prefix-icon="Search"
              />
              <el-tag v-if="selectedMcrFile" type="success" size="small" style="margin-left: 16px;">
                已选择: {{ getFileName(selectedMcrFile) }}
              </el-tag>
            </div>
          </div>

          <div class="file-list">
            <div 
              v-for="item in filteredFileList" 
              :key="item.name"
              class="file-item"
              :class="{
                'directory-item': item.type === 'directory',
                'file-item-selected': item.type === 'file' && selectedMcrFile === getFullPath(item.name),
                'mcr-file': item.type === 'file' && isMcrFile(item.name)
              }"
              @click="handleFileItemClick(item)"
            >
              <div class="file-icon">
                <el-icon v-if="item.type === 'directory'">
                  <Folder />
                </el-icon>
                <el-icon v-else-if="isMcrFile(item.name)" class="mcr-file-icon">
                  <Document />
                </el-icon>
                <el-icon v-else>
                  <Document />
                </el-icon>
              </div>
              <div class="file-info">
                <div class="file-name" :class="{ 'mcr-file-name': isMcrFile(item.name) }">
                  {{ item.name }}
                  <el-tag v-if="isMcrFile(item.name)" type="warning" size="small" class="mcr-tag">
                    MCR
                  </el-tag>
                </div>
              </div>
              <div class="file-action" v-if="item.type === 'directory'">
                <el-icon><ArrowRight /></el-icon>
              </div>
            </div>

            <div v-if="fileList.length === 0" class="empty-files">
              <el-empty description="该目录为空" />
            </div>
          </div>
  
          <div v-if="filteredFileList.length === 0" class="empty-files">
            <el-empty :description="fileFilterText ? '未找到匹配的文件' : '该目录为空'" />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <!-- 右侧按钮 -->
          <div class="footer-buttons">
            <el-button 
              @click="updateMcrDialogVisible = false" 
              size="large"
              class="cancel-btn"
            >
              取消
            </el-button>
            <el-button 
              type="primary" 
              @click="handleResetMcr" 
              :loading="upgradeMcrLoading"
              :disabled="!selectedMcrFile"
              size="large"
              class="confirm-btn"
            >
              <el-tooltip
                v-if="!selectedMcrFile"
                effect="dark"
                content="请选择MCR包"
                placement="top"
              >
                <span>确认更新</span>
              </el-tooltip>
              <span v-else>确认更新</span>
              
              <template #loading>
                <el-icon class="is-loading"><Loading /></el-icon>
              </template>
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  MoreFilled, 
  Edit, 
  Delete, 
  Search, 
  View, 
  Warning, 
  Loading,
  Upload,
  Folder,
  Document,
  ArrowRight,
  QuestionFilled,
  Monitor,
  Plus
} from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { deviceApi } from '@/api/device'
import { remotefsApi, tasksApi } from '@/api/common'
import type { MVServer, ServerDetailResponse, TaskStatusResponse } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const servers = ref<(MVServer & { 
  switchLoading?: boolean; 
  clouddiskStatusLoading?: boolean;
  clouddiskStatusError?: boolean;
  recoveryModeLoading?: boolean;
  recoveryModeError?: boolean;
  recoveryModeSwitching?: boolean;
  recovery_mode?: string | null;
  mcrVersionLoading?: boolean;
  mcrVersionError?: boolean;
  // 新增字段，用于存储关联的服务器信息
  associatedServer?: {
    hostname: string;
    ip: string;
    deviceId?: string; // 新增设备ID字段
  };
  // 新增：MCR任务相关字段
  task_id?: string;
})[]>([])
const allDevices = ref<ServerDetailResponse[]>([])
const searchKeyword = ref('')
const selectedServers = ref<MVServer[]>([])

// MCR包更新相关
const updateMcrDialogVisible = ref(false)
const mcrLoading = ref(false)
const upgradeMcrLoading = ref(false)
const fileList = ref<any[]>([])
const currentPath = ref('/auto/asic-dump/meta_release')
const selectedMcrFile = ref('')
const fileFilterText = ref('')
const directoryCache = ref<Record<string, any[]>>({})
const currentPathInput = ref('')
const taskStatusMap = ref<Record<string, TaskStatusResponse>>({})
const taskStatusTimers = ref<Record<string, number>>({})
const currentServer = ref<(MVServer & { 
  associatedServer?: {
    hostname: string;
    ip: string;
    deviceId?: string;
  };
}) | null>(null)

// MCR状态相关方法
const getMcrStatus = (server: MVServer): string => {
  if (!server.task_id || !taskStatusMap.value[server.task_id]) return ''
  return taskStatusMap.value[server.task_id]?.status || ''
}

const getMcrStatusText = (server: MVServer) => {
  const status = getMcrStatus(server)
  if (!status) return '查询中...'
  
  const stage = taskStatusMap.value[server.task_id!]?.stage || ''
  
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': getStageText(stage),
    'finished': '更新完成',
    'failed': '更新失败'
  }
  console.log(statusMap[status])
  return statusMap[status] || status
}

// 获取 MCR 包信息
const getMcrPackage = (server: MVServer): string => {
  if (!server.task_id || !taskStatusMap.value[server.task_id]) return '-'
  return taskStatusMap.value[server.task_id]?.mcr || '-'
}

const getStageText = (stage: string) => {
  const stageMap: Record<string, string> = {
    'getting_mcr': '下载MCR包',
    'uninstalling_mcr': '卸载旧MCR',
    'installing_mcr': '安装新MCR',
    'waiting': '等待中'
  }
  return stageMap[stage] || stage
}

const getMcrStatusType = (server: MVServer) => {
  const status = getMcrStatus(server)
  if (!status) return 'info' // 查询中显示info类型
  
  const typeMap: Record<string, any> = {
    'pending': 'info',
    'running': 'warning',
    'finished': 'success',
    'failed': 'danger'
  }
  return typeMap[status] || 'info'
}

const navigateToCreateDevice = (nicSn: string) => {
  router.push('/devices/create')
}

const getTaskStage = (server: MVServer): string => {
  if (!server.task_id || !taskStatusMap.value[server.task_id]) return ''
  return taskStatusMap.value[server.task_id]?.stage || ''
}

// 获取任务详情
const getTaskDetail = (server: MVServer): string => {
  if (!server.task_id || !taskStatusMap.value[server.task_id]) return ''
  return taskStatusMap.value[server.task_id]?.detail || ''
}

// 清理ANSI颜色代码和处理转义字符
const cleanAnsiCodes = (text: string): string => {
  try {
    // 使用JSON.parse来处理所有转义字符
    let cleaned = JSON.parse(`"${text}"`)
    
    // 移除ANSI颜色代码
    cleaned = cleaned.replace(/\u001b\[\d+(;\d+)*m/g, '')
    
    // 清理多余的换行
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
    
    return cleaned.trim()
  } catch (error) {
    // 如果JSON解析失败，回退到简单处理
    return text
      .replace(/\\n/g, '\n')
      .replace(/\u001b\[\d+(;\d+)*m/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  }
}

// 查询任务状态
const queryTaskStatus = async (server: MVServer) => {
  if (!server.task_id) return
  
  try {
    const taskStatus: TaskStatusResponse = await tasksApi.getTaskStatus(server.task_id)
    
    // 更新状态映射
    taskStatusMap.value[server.task_id] = taskStatus
    
    // 检查任务是否超时（超过1小时）
    const taskStartTime = new Date(taskStatus.timestamp).getTime()
    const currentTime = new Date().getTime()
    const taskDuration = currentTime - taskStartTime
    const oneHour = 60 * 60 * 1000 // 1小时的毫秒数
    
    if (taskDuration > oneHour && taskStatus.status === 'running') {
      console.warn(`任务 ${server.task_id} 已运行超过1小时，停止轮询`)
      // 更新状态为超时
      taskStatusMap.value[server.task_id] = {
        ...taskStatus,
        status: 'failed',
        detail: '任务执行超时（超过1小时）'
      }
      
      // 清除定时器
      if (taskStatusTimers.value[server.id]) {
        clearTimeout(taskStatusTimers.value[server.id])
        delete taskStatusTimers.value[server.id]
      }
      return
    }
    
    // 如果状态是running，根据阶段设置不同的轮询间隔
    if (taskStatus.status === 'running') {
      let queryInterval = 5000 // 默认5秒
      
      if (taskStatus.stage === 'getting_mcr') {
        // 对于getting_mcr阶段，前5秒使用1秒间隔，之后使用5秒间隔
        const gettingMcrDuration = currentTime - taskStartTime
        queryInterval = gettingMcrDuration < 5000 ? 1000 : 5000
      } else if (taskStatus.stage === 'uninstalling_mcr' || taskStatus.stage === 'installing_mcr') {
        // 对于卸载和安装阶段，使用15秒间隔
        queryInterval = 15000
      }
      
      // 清除之前的定时器
      if (taskStatusTimers.value[server.id]) {
        clearTimeout(taskStatusTimers.value[server.id])
      }
      
      // 设置新的定时器
      taskStatusTimers.value[server.id] = setTimeout(() => {
        queryTaskStatus(server)
      }, queryInterval)
    } else {
      // 状态不是running，清除定时器
      if (taskStatusTimers.value[server.id]) {
        clearTimeout(taskStatusTimers.value[server.id])
        delete taskStatusTimers.value[server.id]
      }
    }
  } catch (error) {
    console.error(`查询任务状态失败: ${server.task_id}`, error)
    
    // 查询失败时，根据当前阶段设置重试间隔
    let retryInterval = 5000 // 默认5秒
    
    const currentStatus = taskStatusMap.value[server.task_id]
    if (currentStatus) {
      if (currentStatus.stage === 'getting_mcr') {
        const taskStartTime = new Date(currentStatus.timestamp).getTime()
        const currentTime = new Date().getTime()
        const gettingMcrDuration = currentTime - taskStartTime
        retryInterval = gettingMcrDuration < 5000 ? 1000 : 5000
      } else if (currentStatus.stage === 'uninstalling_mcr' || currentStatus.stage === 'installing_mcr') {
        retryInterval = 15000
      }
    }
    
    // 查询失败也清除之前的定时器
    if (taskStatusTimers.value[server.id]) {
      clearTimeout(taskStatusTimers.value[server.id])
    }
    
    // 设置重试
    taskStatusTimers.value[server.id] = setTimeout(() => {
      queryTaskStatus(server)
    }, retryInterval)
  }
}

// MCR包更新相关方法
// 添加监听，当 currentPath 变化时更新输入框
watch(currentPath, (newPath) => {
  currentPathInput.value = newPath
}, { immediate: true })

// 方法：处理路径输入框回车
const handlePathInputEnter = async () => {
  const newPath = currentPathInput.value.trim()
  
  // 如果路径没有变化，不做任何操作
  if (newPath === currentPath.value) {
    return
  }
  
  try {
    // 检查输入的是否是MCR文件路径
    const fileName = newPath.split('/').pop() || ''
    if (isMcrFile(fileName)) {
      // 如果是MCR文件路径，加载其父目录并选中该文件
      const parentPath = newPath.substring(0, newPath.lastIndexOf('/')) || '/'
      
      // 先检查父目录是否存在
      await loadDirectory(parentPath)
      
      // 检查该文件是否存在于当前目录中
      const fileExists = fileList.value.some(item => 
        item.type === 'file' && item.name === fileName
      )
      
      if (fileExists) {
        currentPath.value = parentPath
        fileFilterText.value = '' // 清空筛选
        selectedMcrFile.value = newPath // 选中该MCR文件
        
        // 滚动到选中的文件（可选）
        nextTick(() => {
          const selectedElement = document.querySelector('.file-item-selected')
          if (selectedElement) {
            selectedElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        })
      } else {
        throw new Error('MCR文件不存在')
      }
    } else {
      // 如果是目录路径，正常加载
      await loadDirectory(newPath)
      currentPath.value = newPath
      fileFilterText.value = '' // 清空筛选
      selectedMcrFile.value = '' // 清理已选择的MCR包
    }
  } catch (error: any) {
    // 如果加载失败，恢复原来的路径
    currentPathInput.value = currentPath.value
    ElMessage.error(error.message || '路径不存在或无法访问')
  }
}

// 方法：处理输入框失去焦点
const handlePathInputBlur = () => {
  // 失去焦点时恢复当前路径
  currentPathInput.value = currentPath.value
}

// 计算属性：筛选后的文件列表
const filteredFileList = computed(() => {
  if (!fileFilterText.value) {
    return fileList.value
  }
  
  const keyword = fileFilterText.value.toLowerCase()
  return fileList.value.filter(item => 
    item.name.toLowerCase().includes(keyword)
  )
})

// 添加获取完整路径的方法
const getFullPath = (fileName: string) => {
  return currentPath.value === '/' ? `/${fileName}` : `${currentPath.value}/${fileName}`
}

// 方法：检查是否为MCR文件
const isMcrFile = (fileName: string) => {
  return fileName.startsWith('mcr_') && fileName.endsWith('.tar.gz')
}

// 方法：获取文件名（从完整路径中提取）
const getFileName = (filePath: string) => {
  return filePath.split('/').pop() || filePath
}

// 方法：处理更新MCR包对话框
const handleUpdateMcrDialog = async (server: MVServer) => {
  currentServer.value = server
  currentPath.value = '/auto/asic-dump/meta_release'
  selectedMcrFile.value = ''
  updateMcrDialogVisible.value = true
  
  // 加载初始目录
  await loadDirectory(currentPath.value)
}

// 方法：加载目录
const loadDirectory = async (path: string) => {
  // 检查缓存
  if (directoryCache.value[path]) {
    fileList.value = directoryCache.value[path]
    return
  }

  try {
    mcrLoading.value = true
    const response = await remotefsApi.listRemoteDir(path)
    
    // 如果不是根目录，添加返回上一级选项
    if (path !== '/auto') {
      response.unshift({
        name: '..',
        type: 'directory',
      })
    }
    
    fileList.value = response
    
    // 存入缓存
    directoryCache.value[path] = response
    
    fileList.value.sort((a, b) => {
      // .. 始终在最前面
      if (a.name === '..') return -1
      if (b.name === '..') return 1
      
      if (a.type !== b.type) {
        return a.type === 'directory' ? -1 : 1
      }
      return a.name.localeCompare(b.name)
    })
  } catch (error: any) {
    ElMessage.error(`加载目录失败: ${error.response?.data?.detail || '网络错误'}`)
    fileList.value = []
  } finally {
    mcrLoading.value = false
  }
}

watch(updateMcrDialogVisible, (visible) => {
  if (!visible) {
    fileFilterText.value = ''
  }
})

// 方法：处理文件/目录点击
const handleFileItemClick = async (item: any) => {
  if (item.name === '..') {
    // 返回上一级时清理已选择的MCR包
    selectedMcrFile.value = ''
    const pathParts = currentPath.value.split('/').filter(part => part !== '')
    if (pathParts.length > 1) {
      pathParts.pop()
      const parentPath = '/' + pathParts.join('/')
      currentPath.value = parentPath
      fileFilterText.value = '' // 清空筛选
      await loadDirectory(parentPath)
    }
    return
  }
  
  if (item.type === 'directory') {
    // 进入子目录时清理已选择的MCR包
    selectedMcrFile.value = ''
    const newPath = getFullPath(item.name)
    currentPath.value = newPath
    fileFilterText.value = '' // 清空筛选
    await loadDirectory(newPath)
  } else if (item.type === 'file' && isMcrFile(item.name)) {
    // 选择MCR文件
    selectedMcrFile.value = getFullPath(item.name)
  } else {
    // 点击非MCR文件时清理已选择的MCR包
    selectedMcrFile.value = ''
  }
}

// 方法：重置MCR包
const handleResetMcr = async () => {
  if (!currentServer.value || !selectedMcrFile.value) return

  try {
    upgradeMcrLoading.value = true
    
    await ElMessageBox.confirm(
      `确定要使用 MCR 包 "${getFileName(selectedMcrFile.value)}" 更新MV200 "${currentServer.value.name}" 吗？`,
      '确认更新MCR包',
      {
        type: 'warning',
        confirmButtonText: '确定更新',
        cancelButtonText: '取消'
      }
    )

    // 调用MV200的重置MCR接口，去掉updateOption参数
    const response = await mv200Api.upgradeMcr(currentServer.value.id, selectedMcrFile.value)
    
    // 更新当前设备的task_id
    const serverIndex = servers.value.findIndex(s => s.id === currentServer.value!.id)
    if (serverIndex > -1) {
      servers.value[serverIndex].task_id = response.task_id
      // 设置初始状态
      taskStatusMap.value[response.task_id] = {
        id: response.task_id,
        server_id: currentServer.value.id,
        status: 'pending',
        stage: 'waiting',
        detail: '任务已创建，等待执行',
        timestamp: new Date().toISOString()
      }
      // 启动状态查询
      setTimeout(() => {
        queryTaskStatus(servers.value[serverIndex])
      }, 1000) // 1秒后开始查询
    }
    
    ElMessage.success('MCR包更新任务已开始')
    updateMcrDialogVisible.value = false
    
    // 重置状态
    selectedMcrFile.value = ''
    currentPath.value = '/auto'
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error(error.response?.data?.detail || '更新MCR包失败')
  } finally {
    upgradeMcrLoading.value = false
  }
}

// 组件卸载时清除所有定时器
onUnmounted(() => {
  Object.values(taskStatusTimers.value).forEach(timer => {
    clearTimeout(timer)
  })
  taskStatusTimers.value = {}
  taskStatusMap.value = {}
})

// IP地址排序函数 - 正确的数值比较
const ipSortMethod = (a: MVServer, b: MVServer) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const ipA = ipToNumber(a.ip_address);
  const ipB = ipToNumber(b.ip_address);
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

// 辅助函数：用于数据加载时的排序
const ipSort = (ipA: string, ipB: string) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  return ipToNumber(ipA) - ipToNumber(ipB);
};

// 新增：根据nic_sn查找关联的服务器
const findAssociatedServer = (mv200: MVServer, devices: ServerDetailResponse[]) => { 
  if (!mv200.nic_sn) {
    return {
      status: 'not_managed',
      message: '该MV200所在的服务器尚未纳管'
    }
  }
  
  const matchingDevices: Array<{
    hostname: string;
    ip: string;
    deviceId?: string;
  }> = []
  
  for (const device of devices) {
    if (device.nics && device.nics.length > 0) {
      const matchingNic = device.nics.find(nic => nic.sn === mv200.nic_sn)
      if (matchingNic) {
        matchingDevices.push({
          hostname: device.bmc.hostname,
          ip: device.device.ip,
          deviceId: device.id
        })
      }
    }
  }
  
  // 根据匹配到的服务器数量返回不同状态
  if (matchingDevices.length === 0) {
    return {
      status: 'not_managed',
      message: '该MV200所在的服务器尚未纳管'
    }
  } else if (matchingDevices.length === 1) {
    return {
      status: 'matched',
      data: matchingDevices[0],
      message: null
    }
  } else {
    // 匹配到多台服务器的情况
    return {
      status: 'multiple_matched',
      devices: matchingDevices,
      message: `匹配到 ${matchingDevices.length} 台服务器`
    }
  }
}

const getMultipleMatchTooltip = (serverInfo: any) => {
  if (serverInfo.status !== 'multiple_matched') return ''
  
  const devicesList = serverInfo.devices.map((device: any, index: number) => 
    `${index + 1}. ${device.hostname} (${device.ip})`
  ).join('\n')
  
  return `${serverInfo.message}\n\n:\n${devicesList}`
}

// 处理选择变化
const handleSelectionChange = (selection: MVServer[]) => {
  selectedServers.value = selection
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedServers.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedServers.value.length} 台MV200吗？此操作不可恢复！`,
      '确认批量删除',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }
    )

    const promises = selectedServers.value.map(server => 
      mv200Api.delete(server.id)
    )

    await Promise.all(promises)
    ElMessage.success(`成功删除 ${selectedServers.value.length} 台MV200`)
    selectedServers.value = []
    loadData()
  } catch (error) {
    // 用户取消删除
  }
}

// MV200详情页面跳转
const handleDetail = (server: MVServer) => {
  router.push(`/mv200/detail/${server.id}`)
}

// 服务器详情页面跳转
const handleServerDetail = (server: { deviceId?: string }) => {
  if (server.deviceId) {
    router.push(`/devices/detail/${server.deviceId}`)
  } else {
    ElMessage.warning('无法找到服务器详情')
  }
}

// 加载基础列表数据
const loadData = async () => {
  loading.value = true
  try {
    const [serversResponse, devicesResponse] = await Promise.all([
      mv200Api.getAll(),
      deviceApi.getAll()
    ])
    
    // 如果没有MV200服务器数据，直接返回
    if (!serversResponse || serversResponse.length === 0) {
      servers.value = []
      allDevices.value = []
      loading.value = false
      return
    }
    
    allDevices.value = devicesResponse
    
    // 为每个MV200服务器查找关联的服务器
    const serversWithAssociation = serversResponse.map(server => {
      // 查找关联的服务器
      const associatedServer = findAssociatedServer(server, devicesResponse)
      
      return {
        ...server,
        switchLoading: false,
        clouddiskStatusLoading: true,
        clouddiskStatusError: false,
        recoveryModeLoading: true,
        recoveryModeError: false,
        recoveryModeSwitching: false,
        mcrVersionLoading: true,
        mcrVersionError: false,
        recovery_mode: null,
        associatedServer,  // 存储关联的服务器信息
        task_id: server.task_id // 保留task_id
      }
    })
    
    // 按SOC IP排序
    servers.value = serversWithAssociation
      .sort((a, b) => ipSort(a.ip_address, b.ip_address))
    
    loading.value = false
    loadServerDetails()
    
    // 为有task_id的MV200启动状态查询
    servers.value.forEach(server => {
      if (server.task_id) {
        // 启动状态查询
        queryTaskStatus(server)
      }
    })
    
  } catch (error) {
    ElMessage.error('加载MV200列表失败')
    loading.value = false
  }
}

// 异步加载服务器详情（云盘启动状态和恢复模式）
const loadServerDetails = async () => {
  const promises = servers.value.map(async (server, index) => {
    try {
      // 调用单个服务器详情接口获取详细信息
      const serverDetail = await mv200Api.getById(server.id)
      
      // 更新该服务器的云盘启动状态和恢复模式
      servers.value[index] = {
        ...servers.value[index],
        clouddisk_enable: serverDetail.clouddisk_enable || false,
        clouddiskStatusLoading: false,
        clouddiskStatusError: false,
        recovery_mode: serverDetail.recovery_mode || 'manual', // 默认为手动模式
        recoveryModeLoading: false,
        recoveryModeError: false,
        mcrVersionLoading: false,
        mcrVersionError: false,
        versions: serverDetail.versions, // 保存版本信息
        task_id: serverDetail.task_id // 更新task_id
      }

      // 如果有task_id，启动状态查询
      if (serverDetail.task_id) {
        queryTaskStatus(servers.value[index])
      }
    } catch (error) {
      console.error(`获取服务器 ${server.name} 的详情失败:`, error)
      // 更新状态为错误
      servers.value[index] = {
        ...servers.value[index],
        clouddiskStatusLoading: false,
        clouddiskStatusError: true,
        clouddisk_enable: false,
        recoveryModeLoading: false,
        recoveryModeError: true,
        mcrVersionLoading: false,
        mcrVersionError: true
      }
    }
  })
  
  // 并行加载所有服务器的状态，不阻塞界面
  Promise.allSettled(promises).then(() => {
    console.log('所有服务器的详情加载完成')
  })
}

// 计算属性：过滤并排序服务器列表
const filteredServers = computed(() => {
  let filtered = servers.value
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = servers.value.filter(server => {
      // 搜索MV200名称
      if (server.name.toLowerCase().includes(keyword)) return true
      
      // 搜索SOC IP
      if (server.ip_address.toLowerCase().includes(keyword)) return true
      
      // 搜索关联服务器信息
      if (server.associatedServer) {
        if (server.associatedServer.hostname.toLowerCase().includes(keyword)) return true
        if (server.associatedServer.ip.toLowerCase().includes(keyword)) return true
      }
      
      // 搜索描述
      if (server.description && server.description.toLowerCase().includes(keyword)) return true
      
      return false
    })
  }
  
  // 返回过滤后的数据，el-table会处理排序
  return filtered
})

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理，这里可以留空或添加其他逻辑
}

// 处理开关状态变化
const handleSwitchChange = async (value: boolean, server: MVServer & { 
  switchLoading?: boolean; 
  clouddiskStatusError?: boolean;
}) => {
  if (server.switchLoading) return
  
  server.switchLoading = true
  try {
    await mv200Api.update(server.id, {
      name: server.name,
      ip_address: server.ip_address,
      description: server.description,
      clouddisk_enable: value,
      recovery_mode: server.recovery_mode || 'manual'
    })
    server.clouddisk_enable = value
    ElMessage.success(`已${value ? '启用' : '禁用'}云盘启动支持`)
  } catch (error) {
    // 更新失败，恢复原来的状态
    server.clouddisk_enable = !value
    ElMessage.error('状态更新失败，设备可能离线')
  } finally {
    server.switchLoading = false
  }
}

// 处理恢复模式切换
const handleRecoveryModeChange = async (value: string, server: MVServer & { 
  recoveryModeSwitching?: boolean;
  recoveryModeError?: boolean;
}) => {
  if (server.recoveryModeSwitching) return
  
  // 检查设备状态
  if (server.recoveryModeError) {
    ElMessage.warning('设备离线，无法切换恢复模式')
    // 恢复原来的值
    server.recovery_mode = server.recovery_mode === 'auto' ? 'manual' : 'auto'
    return
  }
  
  server.recoveryModeSwitching = true
  
  try {
    await mv200Api.update(server.id, {
      name: server.name,
      ip_address: server.ip_address,
      description: server.description,
      clouddisk_enable: server.clouddisk_enable,
      recovery_mode: value
    })
    
    ElMessage.success(`恢复模式已切换为 ${value === 'auto' ? '自动' : '手动'}`)
  } catch (error) {
    // 更新失败，恢复原来的值
    server.recovery_mode = server.recovery_mode === 'auto' ? 'manual' : 'auto'
    ElMessage.error('切换恢复模式失败，设备可能离线')
  } finally {
    server.recoveryModeSwitching = false
  }
}

// 下拉菜单命令处理
const handleCommand = (command: string, server: MVServer & { 
  clouddiskStatusLoading?: boolean; 
  clouddiskStatusError?: boolean;
}) => {
  switch (command) {
    case 'detail':
      handleDetail(server)
      break
    case 'edit':
      handleEdit(server)
      break
    case 'updateMcr':
      // 这个命令现在通过 @click 直接处理，不在这里处理
      break
    case 'delete':
      handleDelete(server)
      break
  }
}

const handleEdit = (server: MVServer & { 
  clouddiskStatusLoading?: boolean; 
  clouddiskStatusError?: boolean;
}) => {
  // 检查设备状态
  if (server.clouddiskStatusLoading) {
    ElMessage.warning('设备状态查询中，请稍候...')
    return
  }
  if (server.clouddiskStatusError) {
    ElMessage.warning('设备离线，无法编辑')
    return
  }
  router.push(`/mv200/edit/${server.id}`)
}

const handleDelete = async (server: MVServer) => {
  try {
    await ElMessageBox.confirm(`确定要删除MV200 "${server.name}" 吗？`, '确认删除', {
      type: 'warning',
    })

    await mv200Api.delete(server.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    // 用户取消删除
  }
}

onMounted(() => {
  loadData()
})
</script>


<style scoped>
/* MCR状态样式 */
.mcr-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mcr-status-tag {
  cursor: help;
}

.mcr-tooltip-content {
  text-align: left;
}

.detail-text {
  margin: 4px 0 0 0;
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.detail-section {
  margin-top: 8px;
}

.mcr-status-tooltip :deep(.el-tooltip__popper) {
  white-space: pre-line;
  max-width: 300px;
}

.loading-spinner {
  animation: spin 1s linear infinite;
  color: #e6a23c;
}

/* 关键修复：关联服务器单元格样式 */
.associated-server-cell {
  display: flex;
  justify-content: flex-start !important;
  align-items: center;
  width: 100%;
}

/* 覆盖el-table单元格的默认样式 */
:deep(.el-table__body-wrapper .el-table__cell) {
  text-align: left !important;
}

/* 特别针对关联服务器列（第4列） */
:deep(.el-table__body-wrapper tr td:nth-child(4) .cell) {
  display: flex !important;
  justify-content: flex-start !important;
  padding-left: 12px !important;
  text-align: left !important;
}

/* 确保所有状态容器都左对齐 */
.error-info, .not-managed-info, .matched-info {
  display: flex;
  justify-content: flex-start !important;
  align-items: center;
  width: 100%;
}

/* 移除el-tag的默认样式 */
:deep(.error-tag),
:deep(.create-device-tag) {
  margin: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
}

.error-message, .warning-message {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.error-message {
  color: #f56c6c;
}

.warning-message {
  color: #e6a23c;
}

.error-message .el-icon, .warning-message .el-icon {
  font-size: 14px;
}

:deep(.el-tooltip__popper) {
  white-space: pre-line;
  max-width: 400px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.4;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 更新MCR包对话框样式 */
.update-mcr-dialog {
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

.update-mcr-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.current-path {
  margin-bottom: 16px;
  padding: 8px 0;
  width: 100%;
}

.path-input {
  width: 100%;
}

/* 输入框聚焦样式 */
:deep(.path-input .el-input__wrapper) {
  transition: all 0.3s ease;
  font-family: 'Monaco', 'Consolas', monospace;
}

:deep(.path-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.file-browser {
  background: white;
  border-radius: 8px;
  padding: 0;
}

.file-list {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  max-height: 400px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.file-item:last-child {
  border-bottom: none;
}

.file-item:hover {
  background-color: #f5f7fa;
}

.file-item-selected {
  background-color: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.directory-item:hover {
  background-color: #f0f9ff;
}

.file-icon {
  margin-right: 12px;
  font-size: 20px;
  color: #909399;
}

.directory-item .file-icon {
  color: #409eff;
}

.mcr-file-icon {
  color: #e6a23c !important;
}

.file-info {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mcr-file-name {
  color: #e6a23c;
  font-weight: 600;
}

.file-action {
  color: #c0c4cc;
}

.mcr-tag {
  font-size: 10px;
  padding: 0 4px;
  height: 18px;
  line-height: 18px;
}

.empty-files {
  padding: 40px 0;
}

/* 服务器链接样式 */
.server-link {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  height: 24px;
  text-decoration: underline !important;
  text-underline-offset: 2px;
  text-decoration-thickness: 1px;
}

.server-link:hover {
  text-decoration-thickness: 2px;
}

/* 空文本也左对齐 */
.empty-text {
  color: #c0c4cc;
  font-style: italic;
  font-size: 12px;
  width: 100%;
  text-align: left !important;
  display: flex;
  align-items: center;
  justify-content: flex-start !important;
}

/* 更新MCR包按钮样式 */
:deep(.update-mcr-item:not(.is-disabled)) {
  color: #7239ea !important;
}

:deep(.update-mcr-item:not(.is-disabled):hover) {
  color: #5f2bc3 !important;
  background-color: #f8f5ff !important;
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
  width: 300px;
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

/* 对话框底部 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  width: 100%;
}

.footer-buttons {
  display: flex;
  gap: 12px;
}

.cancel-btn {
  width: 100px;
}

.confirm-btn {
  width: 120px;
  font-weight: 600;
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

/* 主机名链接样式 */
.hostname-link {
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

/* MCR版本样式 */
.mcr-version {
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-text {
  font-family: 'Monaco', 'Consolas', monospace;
  font-weight: 500;
}

/* IP地址高亮样式 */
.highlight-ip {
  font-family: 'Monaco', 'Consolas', monospace;
  font-weight: 500;
}

/* 关联服务器信息样式 */
.server-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* 确保el-link与普通文本对齐 */
.server-info :deep(.el-link) {
  display: inline-block;
  line-height: 1.4;
  padding: 0;
  margin: 0;
}

/* 云盘状态样式 */
.clouddisk-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 恢复模式样式 */
.recovery-mode {
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-icon {
  color: #409eff;
  animation: spin 1s linear infinite;
}

.error-icon {
  color: #f56c6c;
}

.status-text {
  font-size: 12px;
  color: #909399;
}

:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  color: #f56c6c;
  background-color: #fef0f0;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 下拉菜单项样式 */
.dropdown-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

:deep(.el-dropdown-menu__item.is-disabled) {
  color: #c0c4cc;
  cursor: not-allowed;
}

:deep(.el-dropdown-menu__item.is-disabled:hover) {
  background-color: transparent;
}

/* 恢复模式开关样式 */
:deep(.el-switch__label) {
  color: #909399;
}

:deep(.el-switch__label.is-active) {
  color: #409eff;
}

/* 操作下拉菜单样式优化 */
:deep(.action-dropdown-menu) {
  min-width: 160px;
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

/* 确保批量删除按钮使用危险色 */
:deep(.danger-item:not(.is-disabled)) {
  color: #f56c6c !important;
}

:deep(.danger-item:not(.is-disabled):hover) {
  color: #dd6161 !important;
  background-color: #fef0f0 !important;
}
</style>