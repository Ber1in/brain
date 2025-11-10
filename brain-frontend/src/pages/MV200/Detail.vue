<template>
  <div class="mv200-detail">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>MV200详情 - {{ mv200Data.name }}</h2>
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
              编辑MV200
            </el-button>
          </div>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <!-- 基本信息 -->
        <el-descriptions-item label="名称">{{ mv200Data.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="SOC IP">{{ mv200Data.ip_address || '-' }}</el-descriptions-item>
        
        <el-descriptions-item label="MAC地址">{{ mv200Data.mac || '-' }}</el-descriptions-item>
        
        <!-- 网关和网卡序列号 -->
        <el-descriptions-item label="网关">{{ mv200Data.gateway || '-' }}</el-descriptions-item>
        <el-descriptions-item label="网卡序列号">{{ mv200Data.nic_sn || '-' }}</el-descriptions-item>

        <!-- 关联服务器信息 -->
        <el-descriptions-item label="关联服务器" :span="2">
          <div v-if="associatedServer" class="server-info">
            <el-link 
              type="primary" 
              @click="handleServerDetail(associatedServer)"
              class="hostname-link underlined-link"
              :underline="false"
            >
              {{ associatedServer.hostname }} ({{ associatedServer.ip }})
            </el-link>
          </div>
          <el-tag v-else type="info">服务器尚未纳管</el-tag>
        </el-descriptions-item>

        <!-- 云盘启动状态 -->
        <el-descriptions-item label="云盘启动支持">
          <el-tag :type="mv200Data.clouddisk_enable ? 'success' : 'info'">
            {{ mv200Data.clouddisk_enable ? '是' : '否' }}
          </el-tag>
        </el-descriptions-item>

        <!-- 恢复模式 -->
        <el-descriptions-item label="恢复模式">
          <el-tag :type="mv200Data.recovery_mode === 'auto' ? 'success' : 'warning'">
            {{ mv200Data.recovery_mode === 'auto' ? '自动' : '手动' }}
          </el-tag>
        </el-descriptions-item>

        <!-- 描述 -->
        <el-descriptions-item label="描述" :span="2">
          {{ mv200Data.description || '无' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 版本信息 -->
      <el-card header="版本信息" style="margin-top: 20px;" v-if="hasVersionInfo">
        <el-table :data="versionList" v-loading="versionsLoading">
          <el-table-column prop="name" label="组件名称" width="150" />
          <el-table-column prop="version" label="版本号" />
        </el-table>
      </el-card>

      <!-- 如果没有版本信息显示提示 -->
      <el-card v-else style="margin-top: 20px;">
        <el-empty description="暂无版本信息" />
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Refresh, Loading } from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { deviceApi } from '@/api/device'
import type { MVServer, ServerDetailResponse, MCRVersionInfo } from '@/types/api'

const route = useRoute()
const router = useRouter()
const mv200Id = ref<string>('')
const refreshing = ref(false)
const versionsLoading = ref(false)

const mv200Data = ref<MVServer>({
  id: '',
  name: '',
  ip_address: '',
  description: '',
  sn: '',
  mac: '',
  gateway: '',
  nic_sn: '',
  versions: undefined,
  clouddisk_enable: false,
  recovery_mode: 'manual'
})

const allDevices = ref<ServerDetailResponse[]>([])

// 计算关联的服务器信息
const associatedServer = computed(() => {
  if (!mv200Data.value.nic_sn || !allDevices.value.length) return null
  
  for (const device of allDevices.value) {
    if (device.nics && device.nics.length > 0) {
      const matchingNic = device.nics.find(nic => nic.sn === mv200Data.value.nic_sn)
      if (matchingNic) {
        return {
          hostname: device.bmc.hostname,
          ip: device.device.ip,
          deviceId: device.id // 保存设备ID用于跳转
        }
      }
    }
  }
  return null
})

// 计算是否有版本信息
const hasVersionInfo = computed(() => {
  return mv200Data.value.versions && 
         (mv200Data.value.versions.driver || 
          mv200Data.value.versions.firmware || 
          mv200Data.value.versions.dpuagent)
})

// 计算版本信息列表
const versionList = computed(() => {
  const versions = mv200Data.value.versions
  if (!versions) return []

  const list = []
  
  if (versions.driver) {
    list.push({
      name: 'mcr-version',
      version: versions.driver,
      status: versions.driver !== '未知' ? '正常' : '未知'
    })
  }
  
  if (versions.firmware) {
    list.push({
      name: 'firmware-version',
      version: versions.firmware,
      status: versions.firmware !== '未知' ? '正常' : '未知'
    })
  }
  
  if (versions.dpuagent) {
    list.push({
      name: 'dpuagent-version',
      version: versions.dpuagent,
      status: versions.dpuagent !== '未知' ? '正常' : '未知'
    })
  }

  return list
})

// 服务器详情页面跳转
const handleServerDetail = (server: { deviceId?: string }) => {
  if (server.deviceId) {
    router.push(`/devices/detail/${server.deviceId}`)
  } else {
    ElMessage.warning('无法找到服务器详情')
  }
}

// 加载设备列表用于查找关联服务器
const loadAllDevices = async () => {
  try {
    const data = await deviceApi.getAll()
    allDevices.value = data
  } catch (error) {
    console.error('加载设备列表失败:', error)
  }
}

// 加载MV200详情
const loadMV200Detail = async () => {
  try {
    const data = await mv200Api.getById(mv200Id.value)
    mv200Data.value = data
    
    // 加载设备列表用于显示关联服务器
    await loadAllDevices()
  } catch (error) {
    ElMessage.error('加载MV200详情失败')
    router.push('/mv200')
  }
}

// 更新MV200信息
const handleRefresh = async () => {
  try {
    refreshing.value = true
    
    await ElMessageBox.confirm(
      '确定要更新MV200信息吗？这将重新获取MV200的硬件信息以及管理网络信息。',
      '确认更新',
      {
        type: 'warning',
        confirmButtonText: '确定更新',
        cancelButtonText: '取消'
      }
    )

    // 调用自动更新接口，传入IP和auto=true
    await mv200Api.update(mv200Id.value, {
      ip_address: mv200Data.value.ip_address,
      auto: true,
      name: mv200Data.value.name,
      description: mv200Data.value.description,
      clouddisk_enable: mv200Data.value.clouddisk_enable,
      recovery_mode: mv200Data.value.recovery_mode
    })
    
    ElMessage.success('MV200信息更新成功')
    
    // 重新加载详情数据
    await loadMV200Detail()
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      // 用户取消操作，不显示错误信息
      return
    }
    ElMessage.error(error.response?.data?.detail || '更新MV200信息失败')
  } finally {
    refreshing.value = false
  }
}

// 编辑MV200
const handleEdit = () => {
  router.push(`/mv200/edit/${mv200Id.value}`)
}

onMounted(() => {
  mv200Id.value = route.params.id as string
  if (!mv200Id.value) {
    ElMessage.error('MV200 ID不能为空')
    router.push('/mv200')
    return
  }
  loadMV200Detail()
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

/* 关联服务器链接样式 */
.server-info {
  display: flex;
  align-items: center;
}

.server-info :deep(.el-link) {
  display: inline-flex;
  align-items: center;
  line-height: 1.4;
  padding: 0;
  margin: 0;
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

:deep(.el-descriptions) {
  margin-top: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
}

:deep(.el-descriptions__content) {
  font-family: 'Monaco', 'Consolas', monospace;
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

/* 版本信息表格样式 */
.version-table {
  width: 100%;
}

:deep(.el-table .cell) {
  padding: 8px 12px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  :deep(.el-descriptions) {
    :deep(.el-descriptions-item) {
      display: block;
      width: 100%;
    }
    
    :deep(.el-descriptions-item__label) {
      width: 120px;
    }
    
    :deep(.el-descriptions-item__content) {
      display: block;
      width: calc(100% - 120px);
    }
  }
}
</style>