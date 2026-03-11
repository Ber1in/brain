<template>
  <div>
    <GenericForm
      :title="formTitle"
      :fields="fields"
      :loading="loading"
      :initial-data="initialData"
      :on-submit="handleSubmit"
      :on-cancel="handleCancel"
      submit-button-text="创建"
      cancel-button-text="取消"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import GenericForm from '@/components/form/GenericForm.vue'
import { createIPRule } from '@/utils/validators'
import { mv200Api } from '@/api/mv200'
import type { MVServerCreate } from '@/types/api'
import type { FormField } from '@/components/form/GenericForm.vue'

const router = useRouter()
const loading = ref(false)

const formTitle = '录入MV200'

const initialData: MVServerCreate = {
  name: '',
  ip_address: '',
  description: ''
}

// 表单字段配置
const fields: FormField[] = [
  {
    type: 'text',
    name: 'name',
    label: '名称',
    placeholder: '输入名称',
    required: true,
    rules: [
      { required: true, message: '请输入服务器名称', trigger: 'blur' },
      { min: 1, max: 50, message: '服务器名称长度应在1-50个字符之间', trigger: 'blur' }
    ],
    tips: '用于标识MV200的唯一名称'
  },
  {
    type: 'text',
    name: 'ip_address',
    label: 'SOC IP地址',
    placeholder: '输入SOC IP地址',
    required: true,
    rules: [
      { required: true, message: '请输入IP地址', trigger: 'blur' },
      createIPRule()
    ],
    tips: 'MV200的SOC IP地址'
  },
  {
    type: 'textarea',
    name: 'description',
    label: '描述',
    placeholder: '输入描述信息',
    rows: 3,
    maxlength: 200,
    showWordLimit: true
  }
]

const handleSubmit = async (formData: MVServerCreate) => {
  try {
    loading.value = true
    await mv200Api.create(formData)
    ElMessage.success('创建成功')
    router.push('/mv200')
    return true
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
    return false
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  router.back()
}
</script>

<style scoped>
/* 样式可以保持原样，GenericForm 组件会处理大部分样式 */
</style>