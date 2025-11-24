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
          <el-input :value="associatedServerInfo" disabled />
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
import { QuestionFilled } from '@element-plus/icons-vue'
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

// 计算关联服务器信息
const associatedServerInfo = computed(() => {
  if (!originalData.nic_sn || !allDevices.value.length) return '-'
  
  for (const device of allDevices.value) {
    if (device.nics && device.nics.length > 0) {
      const matchingNic = device.nics.find(nic => nic.sn === originalData.nic_sn)
      if (matchingNic) {
        return `${device.bmc.hostname} (${device.device.ip})`
      }
    }
  }
  return '-'
})

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
.readonly-info {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>