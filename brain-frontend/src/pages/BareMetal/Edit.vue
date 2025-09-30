<template>
  <div class="bare-edit">
    <el-card>
      <template #header>
        <h2>编辑裸金属服务器</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="服务器ID">
          <el-input v-model="serverId" disabled />
        </el-form-item>

        <el-form-item label="服务器管理IP">
          <el-input v-model="originalData.host_ip" disabled />
        </el-form-item>

        <el-form-item label="MAC地址">
          <el-input v-model="originalData.mac" disabled />
        </el-form-item>
        
        <el-form-item label="网关地址">
          <el-input v-model="originalData.gateway" disabled />
        </el-form-item>

        <el-form-item label="服务器名称" prop="name">
          <el-input v-model="form.name" placeholder="输入服务器名称" />
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
          <el-button @click="$router.push('/bare')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { bareApi } from '@/api/bare'
import type { MVServer, MVServerUpdate } from '@/types/api'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const serverId = ref<string>('')
const originalData = reactive({
  name: '',
  ip_address: '',
  host_ip: '',
  description: '',
  clouddisk_enable: false
})

const form = ref<MVServerUpdate>({
  name: '',
  description: '',
  clouddisk_enable: false
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 2, max: 50, message: '服务器名称长度应在2-50个字符之间', trigger: 'blur' }
  ]
}

// 加载服务器数据
const loadServerData = async () => {
  try {
    const server = await bareApi.getById(serverId.value)
    originalData.name = server.name
    originalData.host_ip = server.host_ip || ''
    originalData.mac = server.mac || ''
    originalData.gateway = server.gateway || ''
    originalData.description = server.description || ''
    
    form.value.name = server.name
    form.value.description = server.description || ''
    form.value.gateway = server.gateway
    form.value.mac = server.mac
  } catch (error) {
    ElMessage.error('加载服务器数据失败')
    router.push('/bare')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await bareApi.update(serverId.value, form.value)
    ElMessage.success('更新成功')
    router.push('/bare')
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
    router.push('/bare')
    return
  }
  loadServerData()
})
</script>
