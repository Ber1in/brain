<template>
  <div class="operational-audit-page">
    <el-card class="main-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-icon size="20" class="header-icon"><Document /></el-icon>
            <span class="header-title">操作审计</span>
          </div>
          <div class="header-right">
            <span class="record-count" v-if="total > 0">共 {{ total }} 条记录</span>
          </div>
        </div>
      </template>

      <!-- 筛选条件 -->
      <div class="filter-section">
        <el-form :inline="true" :model="filterForm" class="filter-form">
          <!-- 用户筛选 -->
          <el-form-item label="用户">
            <el-select
              v-model="filterForm.user"
              placeholder="选择用户"
              clearable
              style="width: 180px"
              class="user-select"
            >
              <el-option
                v-for="user in userList"
                :key="user"
                :label="user"
                :value="user"
              />
            </el-select>
          </el-form-item>

          <!-- 时间范围筛选 -->
          <el-form-item label="时间范围">
            <el-select
              v-model="selectedTimeRange"
              placeholder="选择时间范围"
              style="width: 150px"
              @change="handleTimeRangeChange"
              class="time-range-select"
            >
              <el-option label="今天" value="today" />
              <el-option label="近3天" value="3days" />
              <el-option label="近7天" value="7days" />
              <el-option label="近30天" value="30days" />
              <el-option label="自定义" value="custom" />
            </el-select>
          </el-form-item>

          <!-- 自定义日期范围（当选择自定义时显示） -->
          <el-form-item v-if="selectedTimeRange === 'custom'">
            <el-date-picker
              v-model="customDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              format="YYYY-MM-DD"
              @change="handleCustomDateChange"
              class="custom-date-picker"
            />
          </el-form-item>

          <!-- 操作按钮 -->
          <el-form-item class="action-buttons">
            <el-button 
              type="primary" 
              @click="handleSearch" 
              :loading="loading"
              class="search-btn"
            >
              <el-icon><Search /></el-icon>
              查询
            </el-button>
            <el-button 
              @click="handleReset"
              class="reset-btn"
            >
              <el-icon><Refresh /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 操作日志表格 -->
      <div class="audit-table-container">
        <div class="table-wrapper">
          <el-table
            :data="displayedData"
            v-loading="loading"
            style="width: 100%"
            :default-sort="{ prop: 'date', order: 'descending' }"
            stripe
            size="medium"
            class="audit-table"
            :header-cell-style="headerCellStyle"
            :cell-style="cellStyle"
          >
            <!-- 用户列 -->
            <el-table-column prop="user" label="用户" width="130" sortable>
              <template #default="{ row }">
                <div class="user-cell">
                  <el-avatar 
                    v-if="row.user"
                    :size="28" 
                    :style="{ backgroundColor: stringToColor(row.user) }"
                    class="user-avatar"
                  >
                    {{ row.user.charAt(0).toUpperCase() }}
                  </el-avatar>
                  <span class="user-name">{{ row.user || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            
            <!-- 操作列 -->
            <el-table-column prop="operation" label="操作" min-width="280">
                <template #default="{ row }">
                <div class="operation-cell">
                    <span class="operation-text">{{ getOperationText(row) }}</span>
                    <span v-if="getServerName(row)" 
                            :class="getServerNameClass(row)"
                            class="server-name">
                        {{ getServerName(row) }}
                    </span>
                </div>
                </template>
            </el-table-column>
            
            <!-- 时间列 -->
            <el-table-column prop="date" label="时间" width="180" sortable>
              <template #default="{ row }">
                <span class="date-full">{{ row.date }}</span>
              </template>
            </el-table-column>
            
            <!-- 请求ID列 -->
            <el-table-column prop="request_id" label="请求ID" width="400">
              <template #default="{ row }">
                <div class="request-id-cell">
                  <span class="request-id-text" :title="row.request_id">
                    {{ row.request_id || '-' }}
                  </span>
                  <el-tooltip 
                    v-if="row.status"
                    :content="getStatusTooltip(row.status)"
                    placement="top"
                  >
                    <el-tag 
                      :type="getStatusTagType(row.status)" 
                      size="small"
                      class="status-tag"
                      :class="getStatusTagClass(row.status)"
                    >
                      {{ row.status }}
                    </el-tag>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-section" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 15, 30, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
          class="audit-pagination"
        />
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-if="!loading && auditData.length === 0">
        <el-empty description="暂无操作记录" :image-size="100" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Search, Refresh, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { operationApi } from '@/api/common'
import { deviceApi } from '@/api/device'
import { mv200Api } from '@/api/mv200'
import type { OperationFilterRequest, OperationResponse, ServerDetailResponse } from '@/types/api'

// 定义UUID正则
const UUID_REGEX = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

// 资源类型枚举
enum ResourceType {
  SERVER = 'server',          // 普通服务器
  MV200 = 'mv200',            // MV200服务器
  SYSTEM_SETTINGS = 'settings', // 系统设置
  XSC_NETWORK = 'network',     // XSC网口
  CLOUD_DISK = 'cloud-disk',  // 云系统盘
  CLOUD_IMAGE = 'cloud-image' // 云镜像
}

// 筛选表单
const filterForm = ref<OperationFilterRequest>({
  user: '',
  start: '',
  end: ''
})

// 时间范围选择
const selectedTimeRange = ref('7days')
const customDateRange = ref<[string, string]>(['', ''])

// 表格数据
const auditData = ref<OperationResponse[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(15)
const total = ref(0)

// 用户列表（从数据中提取）
const userList = ref<string[]>([])

const servers = ref<ServerDetailResponse[]>([])
const serversLoading = ref(false)

const mv200List = ref<MVServer[]>([])

const loadMv200List = async () => {
  try {
    mv200List.value = await mv200Api.getAll()
  } catch (error) {
    console.error('获取MV200列表失败:', error)
  }
}

// 添加获取服务器列表的函数
const loadServers = async () => {
  try {
    serversLoading.value = true
    const response = await deviceApi.getAll()
    servers.value = response
  } catch (error) {
    console.error('加载服务器列表失败:', error)
    servers.value = []
  } finally {
    serversLoading.value = false
  }
}

// 在初始化时加载服务器列表
onMounted(async () => {
  setDateRangeByType('7days')
  await Promise.all([
    handleSearch(),
    loadServers(),
    loadMv200List()
  ])
})

// ========== 新增：资源ID提取函数 ==========
const extractResourceId = (path: string, type: ResourceType): string | null => {
  const patterns: Record<ResourceType, RegExp[]> = {
    [ResourceType.SERVER]: [/\/servers\/([^\/]+)/],
    [ResourceType.MV200]: [/\/mv-servers\/([^\/]+)/],
    [ResourceType.XSC_NETWORK]: [/\/networks\/([^\/]+)/],
    [ResourceType.CLOUD_DISK]: [/\/system-disks\/([^\/]+)/],
    [ResourceType.CLOUD_IMAGE]: [/\/images\/([^\/]+)/],
    [ResourceType.SYSTEM_SETTINGS]: []
  }
  
  const typePatterns = patterns[type] || []
  for (const pattern of typePatterns) {
    const match = path.match(pattern)
    if (match && match[1]) {
      return match[1]
    }
  }
  return null
}

// ========== 新增：判断路径对应的资源类型 ==========
const getResourceType = (path: string): ResourceType | null => {
  if (path.includes('/servers/')) {
    return path.includes('/mv-servers/') ? ResourceType.MV200 : ResourceType.SERVER
  }
  if (path.includes('/settings')) {
    return ResourceType.SYSTEM_SETTINGS
  }
  if (path.includes('/networks/')) {
    return ResourceType.XSC_NETWORK
  }
  if (path.includes('/system-disks/')) {
    return ResourceType.CLOUD_DISK
  }
  if (path.includes('/images/')) {
    return ResourceType.CLOUD_IMAGE
  }
  return null
}

// ========== 更新：getOperationText 函数 ==========
const getOperationText = (audit: OperationResponse): string => {
  const { path, method } = audit
  
  // 系统设置
  if (path.endsWith('/settings') && method === 'PUT') {
    return '更新系统设置'
  }
  
  // XSC网口相关
  if (path.endsWith('/networks') && method === 'POST') {
    return '创建XSC网口'
  }
  if (path.includes('/networks/')) {
    const resourceId = extractResourceId(path, ResourceType.XSC_NETWORK)
    if (resourceId) {
      if (method === 'PUT') return '更新XSC网口信息'
      if (method === 'DELETE') return '删除XSC网口'
    }
  }
  
  // 云系统盘相关
  if (path.endsWith('/system-disks') && method === 'POST') {
    return '创建云系统盘'
  }
  if (path.includes('/system-disks/')) {
    const resourceId = extractResourceId(path, ResourceType.CLOUD_DISK)
    if (resourceId) {
      if (method === 'PUT') return '更新云系统盘信息'
      if (method === 'DELETE') return '删除云系统盘'
      if (path.endsWith('/flatten')) return '云系统盘做Flatten'
      if (path.endsWith('/upload')) return '将云系统盘保存为新云镜像'
      if (path.endsWith('/rebuild')) return '重置云系统盘'
    }
  }
  
  // 云镜像相关
  if (path.endsWith('/images') && method === 'POST') {
    return '纳管云镜像'
  }
  if (path.includes('/images/')) {
    const resourceId = extractResourceId(path, ResourceType.CLOUD_IMAGE)
    if (resourceId) {
      if (method === 'PUT') return '更新云镜像信息'
      if (method === 'DELETE') return '删除云镜像'
    }
  }
  
  // 服务器相关（原有逻辑）
  if (path.endsWith('/servers') && method === 'POST') {
    return '纳管服务器'
  }
  
  if (path.endsWith('/mv-servers') && method === 'POST') {
    return '纳管MV200'
  }
  
  const server = findServerByPath(path)
  const mv200 = findMv200ByPath(path)
  
  if (server) {
    if (method === 'PUT') return '更新服务器'
    if (method === 'DELETE') return '删除服务器'
    if (path.endsWith('/occupy')) return '占用服务器'
    if (path.endsWith('/release')) return '释放服务器'
    if (path.endsWith('/follow')) return '关注服务器'
    if (path.endsWith('/unfollow')) return '取消关注服务器'
    if (path.endsWith('/set-boot')) return '更新服务器启动项'
    if (path.endsWith('/power-cycle')) return '冷重启服务器'
    if (path.endsWith('/power-reset')) return '热重启服务器'
    if (path.endsWith('/update_mcr')) return '更新服务器的MCR包'
  }
  
  if (mv200) {
    if (method === 'PUT') return '更新MV200信息'
    if (method === 'DELETE') return '删除MV200'
    if (path.endsWith('/update_mcr')) return '更新MV200的MCR包'
  }
  
  // 默认返回路径（简化显示）
  const shortPath = path.length > 30 ? path.substring(0, 30) + '...' : path
  return `${method} ${shortPath}`
}

// ========== 更新：getServerName 函数 ==========
const getServerName = (audit: OperationResponse): string | null => {
  const { path } = audit
  const resourceType = getResourceType(path)
  
  switch (resourceType) {
    case ResourceType.SERVER:
      const server = findServerByPath(path)
      return server ? getServerDisplayName(server) : null
      
    case ResourceType.MV200:
      const mv200 = findMv200ByPath(path)
      return mv200 ? getMv200DisplayName(mv200) : null
      
    case ResourceType.XSC_NETWORK:
      const networkId = extractResourceId(path, ResourceType.XSC_NETWORK)
      return networkId ? networkId.substring(0, 8) + '...' : null
      
    case ResourceType.CLOUD_DISK:
      const diskId = extractResourceId(path, ResourceType.CLOUD_DISK)
      return diskId ? diskId.substring(0, 8) + '...' : null
      
    case ResourceType.CLOUD_IMAGE:
      const imageId = extractResourceId(path, ResourceType.CLOUD_IMAGE)
      return imageId ? imageId.substring(0, 8) + '...' : null
      
    case ResourceType.SYSTEM_SETTINGS:
      return '系统设置'
      
    default:
      return null
  }
}

// ========== 更新：getServerNameClass 函数 ==========
const getServerNameClass = (audit: OperationResponse): string => {
  const { path } = audit
  const resourceType = getResourceType(path)
  
  switch (resourceType) {
    case ResourceType.SERVER:
      return 'resource-name--server'
      
    case ResourceType.MV200:
      return 'resource-name--mv200'
      
    case ResourceType.XSC_NETWORK:
      return 'resource-name--xsc-network'
      
    case ResourceType.CLOUD_DISK:
      return 'resource-name--cloud-disk'
      
    case ResourceType.CLOUD_IMAGE:
      return 'resource-name--cloud-image'
      
    case ResourceType.SYSTEM_SETTINGS:
      return 'resource-name--system-settings'
      
    default:
      return ''
  }
}

// ========== 原有辅助函数保持不变 ==========

// 根据路径查找对应的服务器信息
const findServerByPath = (path: string): ServerDetailResponse | null => {
  const serverId = extractResourceId(path, ResourceType.SERVER)
  if (!serverId) return null
  
  return servers.value.find(server => server.id === serverId) || null
}

// 根据路径查找对应的MV200信息
const findMv200ByPath = (path: string): MVServer | null => {
  const mv200Id = extractResourceId(path, ResourceType.MV200)
  if (!mv200Id) return null
  
  return mv200List.value.find(mv200 => mv200.id === mv200Id) || null
}

// 获取服务器显示名称
const getServerDisplayName = (server: ServerDetailResponse): string => {
  const { bmc, device } = server
  if (bmc?.hostname && device?.ip) {
    return `${bmc.hostname}(${device.ip})`
  } else if (bmc?.hostname) {
    return bmc.hostname
  } else if (device?.ip) {
    return device.ip
  } else {
    return '未知服务器'
  }
}

// 获取MV200显示名称
const getMv200DisplayName = (mv200: MVServer): string => {
  const { name, ip_address } = mv200
  if (name && ip_address) {
    return `${name}(${ip_address})`
  } else if (name) {
    return name
  } else if (ip_address) {
    return ip_address
  } else {
    return '未知MV200'
  }
}

// 表格样式
const headerCellStyle = () => {
  return {
    backgroundColor: '#f8fafc',
    color: '#374151',
    fontWeight: '600',
    fontSize: '14px',
    borderBottom: '1px solid #e5e7eb',
    padding: '12px 16px'
  }
}

const cellStyle = () => {
  return {
    padding: '14px 16px',
    fontSize: '13px',
    borderBottom: '1px solid #f3f4f6'
  }
}

// 生成用户头像颜色
const stringToColor = (str: string): string => {
  if (!str) return '#6b7280'
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const colors = [
    '#3b82f6', // blue
    '#10b981', // emerald
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // violet
    '#06b6d4', // cyan
    '#ec4899', // pink
    '#f97316', // orange
  ]
  return colors[Math.abs(hash) % colors.length]
}

// 获取状态标签类型
const getStatusTagType = (status: string): string => {
  if (!status) return 'info'
  const statusNum = parseInt(status)
  if (statusNum >= 200 && statusNum < 300) return 'success'
  if (statusNum >= 300 && statusNum < 400) return 'warning'
  if (statusNum >= 400 && statusNum < 500) return 'danger'
  if (statusNum >= 500) return 'danger'
  return 'info'
}

// 获取状态标签样式类
const getStatusTagClass = (status: string): string => {
  if (!status) return ''
  const statusNum = parseInt(status)
  if (statusNum >= 200 && statusNum < 300) return 'status-success'
  if (statusNum >= 300 && statusNum < 400) return 'status-warning'
  if (statusNum >= 400 && statusNum < 500) return 'status-error'
  if (statusNum >= 500) return 'status-error'
  return ''
}

// 获取状态码提示
const getStatusTooltip = (status: string): string => {
  const statusNum = parseInt(status)
  if (statusNum >= 200 && statusNum < 300) return '请求成功'
  if (statusNum === 304) return '未修改'
  if (statusNum >= 400 && statusNum < 500) return '客户端错误'
  if (statusNum >= 500) return '服务器错误'
  return '状态码'
}

// 处理时间范围选择
const handleTimeRangeChange = (value: string) => {
  if (value !== 'custom') {
    setDateRangeByType(value)
  } else {
    // 选择自定义时，清空日期
    filterForm.value.start = ''
    filterForm.value.end = ''
  }
}

// 根据类型设置日期范围
const setDateRangeByType = (type: string) => {
  const now = new Date()
  let startDate = new Date()
  
  switch (type) {
    case 'today':
      // 今天 00:00:00 - 23:59:59
      startDate.setHours(0, 0, 0, 0)
      const endDate = new Date(startDate)
      endDate.setDate(endDate.getDate() + 1)
      endDate.setSeconds(endDate.getSeconds() - 1)
      
      filterForm.value.start = formatDateTimeString(startDate)
      filterForm.value.end = formatDateTimeString(endDate)
      break
      
    case '3days':
      startDate.setDate(now.getDate() - 3)
      startDate.setHours(0, 0, 0, 0)
      filterForm.value.start = formatDateTimeString(startDate)
      filterForm.value.end = formatDateTimeString(now)
      break
      
    case '7days':
      startDate.setDate(now.getDate() - 7)
      startDate.setHours(0, 0, 0, 0)
      filterForm.value.start = formatDateTimeString(startDate)
      filterForm.value.end = formatDateTimeString(now)
      break
      
    case '30days':
      startDate.setDate(now.getDate() - 30)
      startDate.setHours(0, 0, 0, 0)
      filterForm.value.start = formatDateTimeString(startDate)
      filterForm.value.end = formatDateTimeString(now)
      break
  }
}

// 格式化日期时间为 YYYY-MM-DD HH:mm:ss
const formatDateTimeString = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  const seconds = String(date.getSeconds()).padStart(2, '0')
  
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

// 处理自定义日期选择
const handleCustomDateChange = (dates: [string, string]) => {
  if (dates && dates.length === 2) {
    const [start, end] = dates
    filterForm.value.start = start ? `${start} 00:00:00` : ''
    filterForm.value.end = end ? `${end} 23:59:59` : ''
  }
}

// 搜索操作
const handleSearch = async () => {
  try {
    loading.value = true
    
    // 准备查询参数
    const params: OperationFilterRequest = {}
    
    if (filterForm.value.user) {
      params.user = filterForm.value.user
    }
    
    if (filterForm.value.start) {
      params.start = filterForm.value.start
    }
    
    if (filterForm.value.end) {
      params.end = filterForm.value.end
    }
    
    // 调用API
    const response = await operationApi.getOperationalAudit(params)
    
    // 更新数据
    auditData.value = response
    
    // 提取用户列表（去重）
    const users = new Set<string>()
    response.forEach(item => {
      if (item.user) {
        users.add(item.user)
      }
    })
    userList.value = Array.from(users).sort()
    
    // 更新总数
    total.value = response.length
    
    // 重置到第一页
    currentPage.value = 1
    
  } catch (error: any) {
    ElMessage.error(`查询失败: ${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

// 重置筛选条件
const handleReset = () => {
  filterForm.value = {
    user: '',
    start: '',
    end: ''
  }
  selectedTimeRange.value = '7days'
  customDateRange.value = ['', '']
  setDateRangeByType('7days')
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

// 页码变化
const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

// 计算当前页显示的数据
const displayedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return auditData.value.slice(start, end)
})
</script>

<style scoped>
.operational-audit-page {
  padding: 20px;
  background-color: #f9fafb;
  min-height: 100vh;
}

.main-card {
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  overflow: hidden;
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e5e7eb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  color: #3b82f6;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.header-right {
  display: flex;
  align-items: center;
}

.record-count {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
  padding: 4px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

/* 筛选区域 */
.filter-section {
  margin-bottom: 16px;
  padding: 20px 24px;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
}

.filter-form {
  display: flex;
  align-items: center;
  gap: 20px;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.filter-form :deep(.el-form-item__label) {
  font-weight: 500;
  color: #374151;
}

/* 表格容器 */
.audit-table-container {
  min-height: 400px;
}

.table-wrapper {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

/* 表格样式 */
.audit-table {
  --el-table-border-color: #e5e7eb;
  --el-table-header-bg-color: #f8fafc;
  --el-table-row-hover-bg-color: #f9fafb;
}

.audit-table :deep(.el-table__header-wrapper th) {
  font-weight: 600;
  color: #374151;
}

.audit-table :deep(.el-table__body tr:hover) {
  background-color: #f9fafb !important;
}

/* 用户单元格 */
.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  flex-shrink: 0;
  font-weight: 500;
  color: white;
}

.user-name {
  font-weight: 500;
  color: #1f2937;
  font-size: 13px;
}

/* 操作单元格 */
.operation-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  line-height: 1.6;
  color: #1f2937;
  font-weight: 500;
  flex-wrap: wrap;
}

.operation-text {
  color: #1f2937;
}

/* 资源名称基础样式 */
.server-name {
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 12px;
  margin-left: 8px;
  border: 1px solid;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

/* 普通服务器 - 蓝色主题 */
.resource-name--server {
  color: #2563eb;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: #93c5fd;
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.1);
}

/* MV200服务器 - 绿色主题 */
.resource-name--mv200 {
  color: #059669;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border-color: #6ee7b7;
  box-shadow: 0 1px 2px rgba(5, 150, 105, 0.1);
}

/* XSC网口 - 紫色主题 */
.resource-name--xsc-network {
  color: #7c3aed;
  background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
  border-color: #c4b5fd;
  box-shadow: 0 1px 2px rgba(124, 58, 237, 0.1);
}

/* 云系统盘 - 橙色主题 */
.resource-name--cloud-disk {
  color: #ea580c;
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border-color: #fdba74;
  box-shadow: 0 1px 2px rgba(234, 88, 12, 0.1);
}

/* 云镜像 - 粉红色主题 */
.resource-name--cloud-image {
  color: #be185d;
  background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%);
  border-color: #f9a8d4;
  box-shadow: 0 1px 2px rgba(190, 24, 93, 0.1);
}

/* 系统设置 - 灰色主题 */
.resource-name--system-settings {
  color: #4b5563;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-color: #d1d5db;
  box-shadow: 0 1px 2px rgba(75, 85, 99, 0.1);
}

/* 时间单元格 */
.time-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
}

.date-full {
  font-size: 13px;
  color: #1f2937;
  font-weight: 500;
  white-space: nowrap;
}

/* 请求ID单元格 */
.request-id-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.request-id-wrapper {
  flex: 1;
  min-width: 0;
}

.request-id-text {
  display: inline-block;
  font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 11px;
  color: #4b5563;
  background: #f9fafb;
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  word-break: break-all;
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
}

.status-tag {
  min-width: 42px;
  height: 24px;
  font-size: 11px;
  font-weight: 600;
  border: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.status-success {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  color: #065f46;
}

.status-warning {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
}

.status-error {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: #991b1b;
}

/* 分页 */
.pagination-section {
  padding: 20px 24px;
  border-top: 1px solid #e5e7eb;
}

.audit-pagination {
  justify-content: center;
}

/* 空状态 */
.empty-state {
  padding: 60px 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-form {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }
  
  .filter-form :deep(.el-form-item) {
    width: 100%;
    margin-bottom: 8px;
  }
  
  .filter-form :deep(.el-select),
  .filter-form :deep(.el-date-picker) {
    width: 100% !important;
  }
  
  .action-buttons {
    display: flex;
    gap: 12px;
    width: 100%;
  }
  
  .search-btn,
  .reset-btn {
    flex: 1;
  }
  
  .audit-table-container {
    padding: 0 12px;
    overflow-x: auto;
  }
  
  .request-id-cell {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .status-tag {
    align-self: flex-start;
  }
  
  .request-id-text {
    max-width: 200px;
  }
}
</style>