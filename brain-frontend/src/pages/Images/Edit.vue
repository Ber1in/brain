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

        <el-form-item label="最小容量(GB)" prop="min_size">
          <el-input-number
            v-model="form.min_size"
            :min="originalData.min_size"
            :step="1"
            controls-position="right"
            placeholder="输入最小容量"
            style="width: 200px"
          />
          <div class="size-tip" v-if="form.min_size > originalData.min_size">
            <el-icon><Warning /></el-icon>
            <span>当前容量为 {{ originalData.min_size }}GB，修改后不能减小</span>
          </div>
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
import { Warning } from '@element-plus/icons-vue'  // 导入Warning图标
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

// 修改form的类型，添加min_size字段
const form = reactive<ImageUpdate & { min_size: number }>({
  name: '',
  description: '',
  min_size: 0
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入镜像名称', trigger: 'blur' },
    { min: 2, max: 50, message: '镜像名称长度应在2-50个字符之间', trigger: 'blur' }
  ],
  min_size: [
    { required: true, message: '请输入最小容量', trigger: 'blur' },
    { 
      validator: (rule: any, value: number, callback: any) => {
        if (value < originalData.min_size) {
          callback(new Error(`最小容量不能小于当前值(${originalData.min_size}GB)`))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
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
    
    form.name = image.name
    form.description = image.description || ''
    form.min_size = image.min_size  // 初始化form中的min_size
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
    // 构建更新数据，只包含需要更新的字段
    const updateData: ImageUpdate & { min_size: number } = {
      name: form.name,
      description: form.description || ''
    }
    
    // 如果最小容量有变化且比原来大，才包含在更新数据中
    if (form.min_size !== originalData.min_size) {
      if (form.min_size < originalData.min_size) {
        ElMessage.error(`最小容量不能小于当前值(${originalData.min_size}GB)`)
        loading.value = false
        return
      }
      updateData.min_size = form.min_size
    }
    
    await imagesApi.update(imageId.value, updateData)
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
<style scoped>
.size-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background-color: #fffbf0;
  border: 1px solid #faecd8;
  border-radius: 4px;
  color: #e6a23c;
  font-size: 12px;
}

.size-tip .el-icon {
  font-size: 14px;
}
</style>

