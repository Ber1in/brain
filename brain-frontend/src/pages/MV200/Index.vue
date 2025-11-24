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
          width="150"
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
          width="150"
        >
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.ip_address }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联服务器">
          <template #default="{ row }">
            <div v-if="row.associatedServer" class="server-info">
              <el-link 
                type="primary" 
                @click="handleServerDetail(row.associatedServer)"
                class="hostname-link underlined-link"
                :underline="false"
              >
                {{ row.associatedServer.ip }}
              </el-link>
            </div>
            <span v-else class="empty-text">服务器尚未纳管</span>
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button type="primary" link>
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item 
                    command="edit" 
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
                  <el-dropdown-item command="delete" divided class="danger-item">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled, MoreFilled, Edit, Delete, Search, Warning, Loading } from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { deviceApi } from '@/api/device'
import type { MVServer, ServerDetailResponse } from '@/types/api'

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
  }
})[]>([])
const allDevices = ref<ServerDetailResponse[]>([])
const searchKeyword = ref('')
const selectedServers = ref<MVServer[]>([])

// IP地址排序函数 - 正确的数值比较
const ipSortMethod = (a: MVServer, b: MVServer) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    // 将IP地址转换为一个可比较的数字
    // 每段数字占8位，从高位到低位依次是第1段、第2段、第3段、第4段
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
  if (!mv200.nic_sn) return undefined
  
  for (const device of devices) {
    if (device.nics && device.nics.length > 0) {
      const matchingNic = device.nics.find(nic => nic.sn === mv200.nic_sn)
      if (matchingNic) {
        return {
          hostname: device.bmc.hostname,
          ip: device.device.ip,
          deviceId: device.id // 保存设备ID用于跳转
        }
      }
    }
  }
  return undefined
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
        associatedServer  // 存储关联的服务器信息
      }
    })
    
    // 按SOC IP排序
    servers.value = serversWithAssociation
      .sort((a, b) => ipSort(a.ip_address, b.ip_address))
    
    loading.value = false
    loadServerDetails()
    
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
        versions: serverDetail.versions // 保存版本信息
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
    case 'edit':
      handleEdit(server)
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

.server-info .hostname {
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
}

/* 确保el-link与普通文本对齐 */
.server-info :deep(.el-link) {
  display: inline-block;
  line-height: 1.4;
  padding: 0;
  margin: 0;
}

.server-info .ip {
  font-size: 12px;
  color: #909399;
  font-family: 'Courier New', monospace;
  line-height: 1.2;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
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

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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
</style>