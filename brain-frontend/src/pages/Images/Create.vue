<template>
  <div class="image-create">
    <el-card>
      <template #header>
        <h2>录入镜像</h2>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="镜像名称" prop="name">
          <el-input v-model="form.name" placeholder="输入镜像名称" />
        </el-form-item>

        <el-form-item label="镜像源地址" prop="ceph_location">
          <el-input v-model="form.ceph_location" placeholder="格式: pool/rbd" />
        </el-form-item>

        <el-form-item label="Ceph集群IP" prop="mon_host">
          <el-input v-model="form.mon_host" placeholder="输入Ceph集群IP" />
        </el-form-item>

        <el-form-item label="最小容量(GB)" prop="min_size">
          <el-input-number
            v-model="form.min_size"
            :min="1"
            controls-position="right"
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="输入描述信息"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading"> 创建 </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { imagesApi } from '@/api/images'
import type { ImageCreate } from '@/types/api'

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = ref<ImageCreate>({
  name: '',
  ceph_location: '',
  mon_host: '',
  min_size: 1,
  description: '',
})

// 自定义校验规则：检查是否包含且仅包含一个斜杠
const validateCephLocation = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入镜像源地址'))
    return
  }
  
  const slashCount = (value.match(/\//g) || []).length
  if (slashCount === 0) {
    callback(new Error('镜像源地址必须包含一个斜杠(/)，格式: pool/rbd'))
  } else if (slashCount > 1) {
    callback(new Error('镜像源地址只能包含一个斜杠(/)，格式: pool/rbd'))
  } else {
    callback()
  }
}

const validateIP = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入IP地址'))
    return
  }
  
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipPattern.test(value)) {
    callback(new Error('请输入有效的IP地址格式'))
    return
  }
  
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
  name: [{ required: true, message: '请输入镜像名称', trigger: 'blur' }],
  ceph_location: [
    { required: true, message: '请输入镜像源地址', trigger: 'blur' },
    { validator: validateCephLocation, trigger: 'blur' }
  ],
  mon_host: [{ required: true, validator: validateIP, trigger: 'blur' }],
  min_size: [{ required: true, message: '请输入用此镜像创建系统盘时最小容量', trigger: 'blur' }],
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await imagesApi.create(form.value)
    ElMessage.success('创建成功')
    window.location.href = '/images'
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    loading.value = false
  }
}
</script>
