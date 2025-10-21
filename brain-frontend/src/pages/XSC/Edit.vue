<template>
  <div class="xsc-interface-edit">
    <el-card>
      <template #header>
        <h2>编辑XSC网口</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="ID">
          <el-input v-model="interfaceId" disabled />
        </el-form-item>

        <el-form-item label="MV200">
          <el-input :value="originalData.mv200_id" disabled />
          <div class="readonly-info">
            MV200名称: {{ getMv200DisplayInfo() }} 
            <span v-if="loadingMv200" class="loading-text">(加载中...)</span>
            <span v-else-if="mv200Error" class="error-text">(加载失败)</span>
          </div>
          <div class="readonly-info">
            裸金属服务器: {{ getBareMetalDisplayInfo() }}
            <span v-if="loadingBareMetal" class="loading-text">(加载中...)</span>
            <span v-else-if="bareMetalError" class="error-text">(加载失败)</span>
          </div>
        </el-form-item>

        <el-form-item label="IP地址/掩码">
          <el-input :value="originalData.ip" disabled />
        </el-form-item>

        <el-form-item label="网关">
          <el-input :value="originalData.gateway" disabled />
        </el-form-item>

        <el-form-item label="VLAN ID">
          <el-input :value="originalData.vlan_tag" disabled />
        </el-form-item>

        <el-form-item label="MTU">
          <el-input :value="originalData.mtu || 1500" disabled />
        </el-form-item>

        <el-form-item label="MAC地址">
          <el-input :value="originalData.mac || '-'" disabled />
        </el-form-item>

        <el-form-item label="DNS服务器">
          <el-input 
            :value="originalData.dns ? originalData.dns.join(', ') : '-'" 
            disabled 
          />
        </el-form-item>

        <el-form-item label="描述" prop="description">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="3" 
            placeholder="输入网口描述信息"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            保存
          </el-button>
          <el-button @click="$router.push('/xsc-interface')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { networkApi } from '@/api/network'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import type { InterfaceInfo, InterfaceUpdate, MVServer, BareMetalServer } from '@/types/api'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const interfaceId = ref<string>('')

// 服务器信息加载状态
const loadingMv200 = ref(false)
const loadingBareMetal = ref(false)
const mv200Error = ref(false)
const bareMetalError = ref(false)

// 只需要存储当前相关的服务器信息
const currentMv200 = ref<MVServer | null>(null)
const currentBareMetal = ref<BareMetalServer | null>(null)

const originalData = reactive({
  mv200_id: '',
  ip: '',
  gateway: '',
  vlan_tag: 0,
  mtu: 1500,
  mac: '',
  dns: [] as string[],
  description: ''
})

const form = ref<InterfaceUpdate>({
  description: ''
})

const rules: FormRules = {
  description: [
    { max: 200, message: '描述长度不能超过200个字符', trigger: 'blur' }
  ]
}

// 加载网口数据及相关服务器信息
const loadInterfaceData = async () => {
  try {
    // 1. 加载网口基本信息
    const intf = await networkApi.getById(interfaceId.value)
    
    // 设置原始数据
    originalData.mv200_id = intf.mv200_id
    originalData.ip = intf.ip
    originalData.gateway = intf.gateway
    originalData.vlan_tag = intf.vlan_tag
    originalData.mtu = intf.mtu || 1500
    originalData.mac = intf.mac || ''
    originalData.dns = intf.dns || []
    originalData.description = intf.description || ''
    
    form.value.description = intf.description || ''
    
    // 2. 异步加载关联的MV200信息（不阻塞其他数据展示）
    loadMv200Info(intf.mv200_id)
    
  } catch (error) {
    ElMessage.error('加载网口数据失败')
    router.push('/xsc-interface')
  }
}

// 加载MV200信息
const loadMv200Info = async (mv200Id: string) => {
  loadingMv200.value = true
  mv200Error.value = false
  
  try {
    const mv200 = await mv200Api.getById(mv200Id)
    currentMv200.value = mv200
    
    // 3. 异步加载关联的裸金属服务器信息
    if (mv200.bare_id) {
      loadBareMetalInfo(mv200.bare_id)
    }
  } catch (error) {
    console.error('加载MV200信息失败:', error)
    mv200Error.value = true
    ElMessage.warning('无法加载关联的MV200服务器信息')
  } finally {
    loadingMv200.value = false
  }
}

// 加载裸金属服务器信息
const loadBareMetalInfo = async (bareId: string) => {
  loadingBareMetal.value = true
  bareMetalError.value = false
  
  try {
    const bareMetal = await bareApi.getById(bareId)
    currentBareMetal.value = bareMetal
  } catch (error) {
    console.error('加载裸金属服务器信息失败:', error)
    bareMetalError.value = true
    ElMessage.warning('无法加载关联的裸金属服务器信息')
  } finally {
    loadingBareMetal.value = false
  }
}

// 获取MV200显示信息
const getMv200DisplayInfo = () => {
  if (loadingMv200.value) return ''
  if (mv200Error.value || !currentMv200.value) return '未知'
  return `${currentMv200.value.name} (${currentMv200.value.ip_address})`
}

// 获取裸金属服务器显示信息
const getBareMetalDisplayInfo = () => {
  if (loadingBareMetal.value) return ''
  if (bareMetalError.value || !currentBareMetal.value) return '未知'
  return currentBareMetal.value.host_ip
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await networkApi.update(interfaceId.value, form.value)
    ElMessage.success('更新成功')
    router.push('/xsc-interface')
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    loading.value = false
  }
}

// 页面加载
onMounted(() => {
  interfaceId.value = route.params.id as string
  if (!interfaceId.value) {
    ElMessage.error('网口ID不能为空')
    router.push('/xsc-interface')
    return
  }
  
  loadInterfaceData()
})
</script>

<style scoped>
.xsc-interface-edit {
  padding: 20px;
}

.readonly-info {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.loading-text {
  color: #409eff;
  font-style: italic;
}

.error-text {
  color: #f56c6c;
  font-style: italic;
}

.el-card {
  max-width: 800px;
  margin: 0 auto;
}

.el-form {
  margin-top: 20px;
}
</style>