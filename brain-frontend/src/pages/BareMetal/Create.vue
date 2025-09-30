<template>
  <div class="bare-create">
    <el-card>
      <template #header>
        <h2>录入裸金属服务器</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="服务器名称" prop="name">
          <el-input 
            v-model="form.name" 
            placeholder="输入服务器名称" 
            clearable
          />
          <div class="form-tip">用于标识裸金属服务器的唯一名称</div>
        </el-form-item>

        <el-form-item label="服务器管理IP" prop="host_ip">
          <el-input 
            v-model="form.host_ip" 
            placeholder="输入裸金属服务器地址" 
            clearable
          />
          <div class="form-tip">物理主机管理口的IP地址</div>
        </el-form-item>
        
        <el-form-item label="MAC地址" prop="mac">
          <el-input 
            v-model="form.mac" 
            placeholder="输入裸金属服务器管理口MAC地址" 
            clearable
          />
          <div class="form-tip">物理主机管理口的MAC地址</div>
        </el-form-item>

        <el-form-item label="网关地址" prop="gateway">
          <el-input 
            v-model="form.gateway" 
            placeholder="输入裸金属服务器地址" 
            clearable
          />
          <div class="form-tip">物理主机管理口的网关地址</div>
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
import { ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { bareApi } from '@/api/bare'
import type { BareMetalServerCreate } from '@/types/api'

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = ref<BareMetalServerCreate>({
  name: '',
  host_ip: '',
  gateway: '',
  mac: '',
  description: ''
})

const validateMac = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入MAC地址'))
    return
  }

  const macPattern = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/
  if (!macPattern.test(value)) {
    callback(new Error('MAC地址格式必须为：00:11:22:33:44:55'))
    return
  }

  const bytes = value.split(':')
  for (const byte of bytes) {
    const hexValue = parseInt(byte, 16)
    if (isNaN(hexValue) || hexValue < 0 || hexValue > 255) {
      callback(new Error('MAC地址包含无效的十六进制值'))
      return
    }
  }

  const firstByte = parseInt(bytes[0], 16)
  if ((firstByte & 1) === 1) {
    callback(new Error('MAC地址不能是多播或广播地址'))
    return
  }
  
  callback()
}

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
  host_ip: [
    { required: true, validator: validateIP, trigger: 'blur' }
  ],
  gateway: [
    { required: true, validator: validateIP, trigger: 'blur' }
  ],
  mac: [
    { required: true, validator: validateMac, trigger: 'blur' }
  ],
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

    await bareApi.create(form.value)
    ElMessage.success('创建成功')
    window.location.href = '/bare'
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
</script>

