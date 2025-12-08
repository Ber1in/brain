<template>
  <div class="mv200-edit">
    <el-card>
      <template #header>
        <h2>编辑MV200</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="ID">
          <el-input v-model="serverId" disabled />
        </el-form-item>

        <el-form-item label="SOC IP">
          <el-input v-model="originalData.ip_address" disabled />
        </el-form-item>

        <el-form-item label="关联服务器">
          <!-- 关联服务器状态显示 -->
          <div v-if="associatedServer && associatedServer.status">
            <!-- 未纳管状态 - warning级别 -->
            <div v-if="associatedServer.status === 'not_managed'" class="server-status warning-status">
              <el-alert 
                type="warning" 
                :title="associatedServer.message"
                :closable="false"
                show-icon
                class="status-alert"
              />
            </div>
            
            <!-- 正确匹配状态 -->
            <div v-else-if="associatedServer.status === 'matched'" class="server-status success-status">
              <el-input 
                :value="getServerInfo(associatedServer.data)" 
                disabled 
                class="matched-server-info"
              >
                <template #prefix>
                  <el-icon class="success-icon"><Check /></el-icon>
                </template>
              </el-input>
            </div>
            
            <!-- 多匹配异常状态 - error级别 -->
            <div v-else-if="associatedServer.status === 'multiple_matched'" class="server-status error-status">
              <el-alert 
                type="error" 
                :title="getMultipleMatchTitle(associatedServer)"
                :closable="false"
                show-icon
                :description="getMultipleMatchDescription(associatedServer)"
                class="status-alert"
              />
            </div>
            
            <!-- 未知状态 -->
            <div v-else class="server-status info-status">
              <el-alert 
                type="info" 
                title="未知状态"
                :closable="false"
                show-icon
                class="status-alert"
              />
            </div>
          </div>
          
          <!-- 没有服务器信息 -->
          <div v-else class="server-status info-status">
            <el-alert 
              type="info" 
              title="服务器尚未纳管"
              :closable="false"
              show-icon
              class="status-alert"
            />
          </div>
        </el-form-item>

        <el-form-item label="支持云盘启动">
          <template #label>
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
          <el-input :value="originalData.clouddisk_enable ? '是' : '否'" disabled />
        </el-form-item>

        <!-- 恢复模式显示 -->
        <el-form-item label="恢复模式">
          <template #label>
            <span>恢复模式</span>
            <el-tooltip 
              effect="dark" 
              content="自动模式：重启后系统会自动执行资源恢复操作；手动模式：重启后不自动执行恢复，可手动执行"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <el-input :value="getRecoveryModeText(originalData.recovery_mode)" disabled />
        </el-form-item>

        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="输入名称" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="3" 
            placeholder="输入描述信息"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            保存
          </el-button>
          <el-button @click="$router.push('/mv200')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { QuestionFilled, Check, Warning, CircleClose } from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { deviceApi } from '@/api/device'
import type { MVServer, MVServerUpdate, ServerDetailResponse } from '@/types/api'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const serverId = ref<string>('')
const allDevices = ref<ServerDetailResponse[]>([])

const originalData = reactive({
  name: '',
  ip_address: '',
  description: '',
  clouddisk_enable: false,
  recovery_mode: '' as string | null,
  nic_sn: ''
})

const form = ref<MVServerUpdate>({
  name: '',
  description: '',
  clouddisk_enable: false,
  recovery_mode: null,
  auto: false
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '服务器名称长度应在2-50个字符之间', trigger: 'blur' }
  ]
}

// 查找关联的服务器（支持多种状态）
const findAssociatedServer = (mv200: MVServer, devices: ServerDetailResponse[]) => { 
  if (!mv200.nic_sn) {
    return {
      status: 'not_managed',
      message: '服务器尚未纳管',
      severity: 'warning' // warning级别
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
      message: '服务器尚未纳管',
      severity: 'warning' // warning级别
    }
  } else if (matchingDevices.length === 1) {
    return {
      status: 'matched',
      data: matchingDevices[0],
      message: null,
      severity: 'success'
    }
  } else {
    // 匹配到多台服务器的情况
    return {
      status: 'multiple_matched',
      devices: matchingDevices,
      message: `匹配异常：网卡SN(${mv200.nic_sn})关联到多台服务器`,
      severity: 'error' // error级别
    }
  }
}

// 计算关联的服务器信息
const associatedServer = computed(() => {
  if (!originalData.nic_sn || !allDevices.value.length) {
    return {
      status: 'not_managed',
      message: '服务器尚未纳管',
      severity: 'warning'
    }
  }
  
  return findAssociatedServer({
    nic_sn: originalData.nic_sn,
    // 其他字段暂时为空
  } as MVServer, allDevices.value)
})

// 获取服务器信息文本
const getServerInfo = (server: any) => {
  return `${server.hostname} (${server.ip})`
}

// 获取多匹配标题
const getMultipleMatchTitle = (serverInfo: any) => {
  if (serverInfo.status !== 'multiple_matched') return ''
  return `匹配异常：匹配到${serverInfo.devices.length}台服务器`
}

// 获取多匹配描述
const getMultipleMatchDescription = (serverInfo: any) => {
  if (serverInfo.status !== 'multiple_matched') return ''
  
  const devicesList = serverInfo.devices.map((device: any, index: number) => 
    `${index + 1}. ${device.hostname} (${device.ip})`
  ).join('，')
  
  return `网卡SN: ${originalData.nic_sn} 关联到以下服务器：${devicesList}`
}

// 获取恢复模式显示文本
const getRecoveryModeText = (mode: string | null | undefined) => {
  if (!mode || mode === 'None') return '未知';
  if (mode === 'auto') return '自动模式';
  if (mode === 'manual') return '手动模式';
  return mode;
};

// 加载设备列表用于查找关联服务器
const loadAllDevices = async () => {
  try {
    const data = await deviceApi.getAll()
    allDevices.value = data
  } catch (error) {
    console.error('加载设备列表失败:', error)
  }
}

// 加载服务器数据
const loadServerData = async () => {
  try {
    const server = await mv200Api.getById(serverId.value)
    originalData.name = server.name
    originalData.ip_address = server.ip_address
    originalData.description = server.description || ''
    originalData.clouddisk_enable = server.clouddisk_enable || false
    originalData.recovery_mode = server.recovery_mode || null
    originalData.nic_sn = server.nic_sn || ''
    
    // 加载设备列表用于显示关联服务器
    await loadAllDevices()

    form.value.name = server.name
    form.value.description = server.description || ''
    form.value.clouddisk_enable = server.clouddisk_enable || false
    form.value.recovery_mode = server.recovery_mode || null
    form.value.auto = false
  } catch (error) {
    ElMessage.error('加载服务器数据失败')
    router.push('/mv200')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await mv200Api.update(serverId.value, {
      name: form.value.name,
      ip_address: originalData.ip_address,
      description: form.value.description,
      clouddisk_enable: originalData.clouddisk_enable,
      recovery_mode: originalData.recovery_mode,
      auto: false
    })
    ElMessage.success('更新成功')
    router.push('/mv200')
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  serverId.value = route.params.id as string
  if (!serverId.value) {
    ElMessage.error('服务器ID不能为空')
    router.push('/mv200')
    return
  }
  loadServerData()
})
</script>

<style scoped>
/* 服务器状态样式 */
.server-status {
  margin: 8px 0;
}

/* 成功匹配状态 */
.success-status {
  margin-top: 8px;
}

.matched-server-info :deep(.el-input__inner) {
  background-color: #f0f9ff;
  border-color: #d1e9ff;
  color: #1f2937;
}

.success-icon {
  color: #67c23a;
}

/* 警告状态 */
.warning-status :deep(.el-alert) {
  background-color: #fdf6ec;
  border: 1px solid #faecd8;
}

.warning-status :deep(.el-alert__title) {
  color: #e6a23c;
  font-weight: 600;
}

/* 错误状态 */
.error-status :deep(.el-alert) {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
}

.error-status :deep(.el-alert__title) {
  color: #f56c6c;
  font-weight: 600;
}

.error-status :deep(.el-alert__description) {
  color: #606266;
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.4;
}

/* 信息状态 */
.info-status :deep(.el-alert) {
  background-color: #f4f4f5;
  border: 1px solid #e9e9eb;
}

.info-status :deep(.el-alert__title) {
  color: #909399;
  font-weight: 600;
}

/* 状态提示框样式 */
.status-alert {
  margin: 0;
  padding: 8px 12px;
}

:deep(.el-alert__icon) {
  margin-right: 8px;
}

/* 表单整体样式 */
:deep(.el-form-item__label) {
  font-weight: 600;
  color: #1f2937;
}

:deep(.el-input.is-disabled .el-input__inner) {
  background-color: #f5f7fa;
  color: #606266;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 768px) {
  :deep(.el-form) {
    padding: 16px;
  }
  
  .server-status {
    margin: 4px 0;
  }
  
  .error-status :deep(.el-alert__description) {
    font-size: 12px;
  }
}
</style>