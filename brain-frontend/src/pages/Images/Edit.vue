<template>
  <div class="image-edit">
    <GenericForm
      :title="'编辑镜像'"
      :fields="formFields"
      :initial-data="formData"
      :loading="loading"
      :on-submit="handleSubmit"
      submit-text="保存"
      cancel-text="取消"
      :redirect-to="'/images'"
      :extra-rules="extraRules"
      ref="formRef"
    >
      <!-- 只读信息插槽 -->
      <template #header-left>
        <div class="readonly-info">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="镜像ID">{{ imageId }}</el-descriptions-item>
            <el-descriptions-item label="Ceph位置">{{ originalData.ceph_location }}</el-descriptions-item>
            <el-descriptions-item label="监控主机">{{ originalData.mon_host }}</el-descriptions-item>
            <el-descriptions-item label="当前最小容量">{{ originalData.min_size }} GB</el-descriptions-item>
          </el-descriptions>
        </div>
      </template>
      
      <!-- 最小容量特殊提示 -->
      <template #field-min_size="{ field, value, update }">
        <div class="min-size-field">
          <el-input-number
            :model-value="value"
            @update:model-value="update"
            :min="originalData.min_size"
            :step="1"
            controls-position="right"
            placeholder="输入最小容量"
            style="width: 200px"
          />
          <div v-if="value > originalData.min_size" class="size-tip">
            <el-icon><Warning /></el-icon>
            <span>当前容量为 {{ originalData.min_size }}GB，修改后不能减小</span>
          </div>
        </div>
      </template>
    </GenericForm>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormRules } from 'element-plus'
import { Warning } from '@element-plus/icons-vue'
import { imagesApi } from '@/api/images'
import { GenericForm } from '@/components'
import { createRequiredRule, createLengthRule } from '@/utils/validators'
import type { Image, ImageUpdate } from '@/types/api'
import type { FormField } from '@/components/form/GenericForm.vue'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const loading = ref(false)
const imageId = ref<string>('')

// 原始数据（只读）
const originalData = reactive({
  name: '',
  ceph_location: '',
  mon_host: '',
  min_size: 0,
  description: ''
})

// 表单数据（可编辑）
const formData = reactive({
  name: '',
  description: '',
  min_size: 0
})

// 表单字段配置
const formFields = computed<FormField[]>(() => [
  {
    name: 'name',
    label: '镜像名称',
    type: 'text',
    required: true,
    placeholder: '输入镜像名称',
    defaultValue: originalData.name
  },
  {
    name: 'min_size',
    label: '最小容量(GB)',
    type: 'custom', // 使用自定义渲染
    required: true,
    tip: `当前容量: ${originalData.min_size}GB，修改后不能减小`
  },
  {
    name: 'description',
    label: '描述',
    type: 'textarea',
    placeholder: '输入描述信息',
    rows: 3,
    maxlength: 200,
    showWordLimit: true,
    defaultValue: originalData.description || ''
  }
])

// 额外的验证规则
const extraRules = computed<FormRules>(() => ({
  name: [
    createRequiredRule('镜像名称'),
    createLengthRule('镜像名称', { min: 2, max: 50 })
  ],
  min_size: [
    {
      required: true,
      message: '请输入最小容量',
      trigger: 'blur'
    },
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
}))

// 加载镜像数据
const loadImageData = async () => {
  try {
    const image = await imagesApi.getById(imageId.value)
    
    // 设置原始数据
    originalData.name = image.name
    originalData.ceph_location = image.ceph_location
    originalData.mon_host = image.mon_host
    originalData.min_size = image.min_size
    originalData.description = image.description || ''
    
    // 设置表单数据
    formData.name = image.name
    formData.description = image.description || ''
    formData.min_size = image.min_size
    
  } catch (error) {
    ElMessage.error('加载镜像数据失败')
    router.push('/images')
  }
}

// 提交处理
const handleSubmit = async (data: any): Promise<void> => {
  // 构建更新数据
  const updateData: ImageUpdate & { min_size?: number } = {
    name: data.name,
    description: data.description || ''
  }
  
  // 如果最小容量有变化且比原来大，才包含在更新数据中
  if (data.min_size !== originalData.min_size) {
    if (data.min_size < originalData.min_size) {
      throw new Error(`最小容量不能小于当前值(${originalData.min_size}GB)`)
    }
    updateData.min_size = data.min_size
  }
  
  return imagesApi.update(imageId.value, updateData)
}

// 初始化
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
.image-edit {
  max-width: 800px;
  margin: 0 auto;
}

.readonly-info {
  margin-bottom: 20px;
}

.min-size-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.size-tip {
  display: flex;
  align-items: center;
  gap: 6px;
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