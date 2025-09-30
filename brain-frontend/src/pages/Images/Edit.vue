<template>
  <div class="image-edit">
    <el-card>
      <template #header>
        <h2>编辑镜像</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="镜像ID">
          <el-input v-model="imageId" disabled />
        </el-form-item>

        <el-form-item label="Ceph位置">
          <el-input v-model="originalData.ceph_location" disabled />
        </el-form-item>

        <el-form-item label="监控主机">
          <el-input v-model="originalData.mon_host" disabled />
        </el-form-item>

        <el-form-item label="最小容量(GB)">
          <el-input v-model="originalData.min_size" disabled />
        </el-form-item>

        <el-form-item label="镜像名称" prop="name">
          <el-input v-model="form.name" placeholder="输入镜像名称" />
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
          <el-button @click="$router.push('/images')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { imagesApi } from '@/api/images'
import type { Image, ImageUpdate } from '@/types/api'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const imageId = ref<string>('')
const originalData = reactive({
  name: '',
  ceph_location: '',
  mon_host: '',
  min_size: 0,
  description: ''
})

const form = ref<ImageUpdate>({
  name: '',
  description: ''
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入镜像名称', trigger: 'blur' },
    { min: 2, max: 50, message: '镜像名称长度应在2-50个字符之间', trigger: 'blur' }
  ]
}

// 加载镜像数据
const loadImageData = async () => {
  try {
    const image = await imagesApi.getById(imageId.value)
    originalData.name = image.name
    originalData.ceph_location = image.ceph_location
    originalData.mon_host = image.mon_host
    originalData.min_size = image.min_size
    originalData.description = image.description || ''
    
    form.value.name = image.name
    form.value.description = image.description || ''
  } catch (error) {
    ElMessage.error('加载镜像数据失败')
    router.push('/images')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await imagesApi.update(imageId.value, form.value)
    ElMessage.success('更新成功')
    router.push('/images')
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  imageId.value = route.params.id as string
  if (!imageId.value) {
    ElMessage.error('镜像ID不能为空')
    router.push('/images')
    return
  }
  loadImageData()
})
</script>

