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
          <div class="readonly-info">MV200名称: {{ getMv200Name(originalData.mv200_id) }}</div>
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
import type { InterfaceInfo, InterfaceUpdate, MVServer } from '@/types/api'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const interfaceId = ref<string>('')
const mv200Servers = ref<MVServer[]>([])
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

// 加载网口数据
const loadInterfaceData = async () => {
  try {
    const intf = await networkApi.getById(interfaceId.value)
    originalData.mv200_id = intf.mv200_id
    originalData.ip = intf.ip
    originalData.gateway = intf.gateway
    originalData.vlan_tag = intf.vlan_tag
    originalData.mtu = intf.mtu || 1500
    originalData.mac = intf.mac || ''
    originalData.dns = intf.dns || []
    originalData.description = intf.description || ''
    
    form.value.description = intf.description || ''
  } catch (error) {
    ElMessage.error('加载网口数据失败')
    router.push('/xsc-interface')
  }
}

// 加载MV200服务器列表
const loadMv200Servers = async () => {
  try {
    const servers = await mv200Api.getAll()
    mv200Servers.value = servers
  } catch (error) {
    console.error('加载MV200列表失败')
  }
}

// 根据ID获取MV200服务器名称
const getMv200Name = (mv200Id: string) => {
  const server = mv200Servers.value.find(s => s.id === mv200Id)
  return server ? `${server.name} (${server.ip_address})` : mv200Id
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await networkApi.update(form.value)
    ElMessage.success('更新成功')
    router.push('/xsc-interface')
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  interfaceId.value = route.params.id as string
  if (!interfaceId.value) {
    ElMessage.error('网口ID不能为空')
    router.push('/xsc-interface')
    return
  }
  
  loadMv200Servers()
  loadInterfaceData()
})
</script>

<style scoped>
.readonly-info {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>