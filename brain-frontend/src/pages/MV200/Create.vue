<template>
  <div class="mv200-create">
    <el-card>
      <template #header>
        <h2>录入MV200服务器</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="名称" prop="name">
          <el-input 
            v-model="form.name" 
            placeholder="输入名称" 
            clearable
          />
          <div class="form-tip">用于标识MV200的唯一名称</div>
        </el-form-item>

        <el-form-item label="SOC IP地址" prop="ip_address">
          <el-input 
            v-model="form.ip_address" 
            placeholder="输入SOC IP地址" 
            clearable
          />
          <div class="form-tip">MV200的SOC IP地址</div>
        </el-form-item>


        <el-form-item label="裸金属服务器" prop="bare_id">
          <el-select
            v-model="form.bare_id"
            placeholder="确定MV200插在哪台裸金属服务器"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="server in bareServers"
              :key="server.id"
              :label="server.name"
              :value="server.id"
            >
              <span>{{ server.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                {{ server.host_ip }}
              </span>
            </el-option>
          </el-select>
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
            创建
          </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import type { MVServerCreate, BareMetalServer } from '@/types/api'

const bareServers = ref<BareMetalServer[]>([])
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = ref<MVServerCreate>({
  name: '',
  ip_address: '',
  bare_id: '',
  description: ''
})

// IP地址验证函数
const validateIP = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入IP地址'))
    return
  }
  
  // 简单的IP地址格式验证
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipPattern.test(value)) {
    callback(new Error('请输入有效的IP地址格式'))
    return
  }
  
  // 验证每个数字段是否在0-255之间
  const parts = value.split('.')
  for (const part of parts) {
    const num = parseInt(part)
    if (num < 0 || num > 255) {
      callback(new Error('IP地址每个数字段应在0-255之间'))
      return
    }
  }
  
  callback()
}

const rules: FormRules = {
  name: [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 1, max: 50, message: '服务器名称长度应在2-50个字符之间', trigger: 'blur' }
  ],
  ip_address: [
    { required: true, validator: validateIP, trigger: 'blur' }
  ],
  bare_id: [
    { required: true, message: '请选择裸金属服务器', trigger: 'blur' }
  ],
}

const loadResources = async () => {
  try {
    const [serversResponse] = await Promise.all([
      bareApi.getAll(),
    ])

    bareServers.value = serversResponse
  } catch (error) {
    ElMessage.error('加载资源失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    // 验证表单
    const valid = await formRef.value.validate()
    if (!valid) return

    loading.value = true
    
    // 检查IP地址是否相同
    if (form.value.ip_address === form.value.host_ip) {
      await ElMessageBox.confirm(
        'SOCIP和裸金属服务器相同，是否继续创建？',
        'IP地址提示',
        {
          type: 'warning',
          confirmButtonText: '继续创建',
          cancelButtonText: '重新输入'
        }
      )
    }

    await mv200Api.create(form.value)
    ElMessage.success('创建成功')
    window.location.href = '/mv200'
  } catch (error: any) {
    if (error === 'cancel') {
      // 用户取消创建，不做任何操作
      return
    }
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadResources()
})
</script>

