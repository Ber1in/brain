<template>
  <div class="device-create">
    <el-card>
      <template #header>
        <h2>录入服务器</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="服务器名称" prop="bmc.hostname">
          <el-input 
            v-model="form.bmc.hostname" 
            placeholder="输入服务器名称，在当前系统中标识该服务器" 
            clearable
          />
        </el-form-item>

        <el-form-item label="服务器IP" prop="device.ip">
          <el-input 
            v-model="form.device.ip" 
            placeholder="输入服务器管理IP地址" 
            clearable
          />
        </el-form-item>

        <el-form-item label="OS用户名" prop="device.username">
          <el-input 
            v-model="form.device.username" 
            placeholder="输入当前操作系统管理员用户名"
            clearable
          />
        </el-form-item>

        <el-form-item label="OS密码" prop="device.password">
          <el-input 
            v-model="form.device.password" 
            type="password"
            placeholder="输入当前操作系统管理员密码" 
            clearable
            show-password
          />
        </el-form-item>

        <el-form-item label="标签">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入标签"
            style="width: 100%"
            :loading="tagsLoading"
            @blur="handleTagBlur"
            @change="handleTagChange"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag.id"
              :label="tag.name"
              :value="tag.name"
            />
          </el-select>
          <div class="form-tip">选择已有标签或输入新标签（输入后按回车创建）</div>
        </el-form-item>

        <el-form-item label="备注">
          <el-input 
            v-model="form.notes" 
            type="textarea" 
            :rows="3" 
            placeholder="输入备注信息"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            创建
          </el-button>
          <el-button @click="$router.push('/devices')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { deviceApi } from '@/api/device'
import { tagApi } from '@/api/tag'
import type { ServerRequest, TagResponse } from '@/types/api'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const tagsLoading = ref(false)
const availableTags = ref<TagResponse[]>([])

const form = reactive<ServerRequest>({
  bmc: {
    hostname: '',
    ip: null // BMC IP 设置为 null，后端会自动生成
  },
  device: {
    ip: '',
    username: 'root',
    password: ''
  },
  nics: [],
  os_types: [],
  tags: [],
  notes: ''
})

// IP地址验证函数
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
  'bmc.hostname': [
    { required: true, message: '请输入服务器名称', trigger: 'blur' },
    { min: 1, max: 50, message: '服务器名称长度应在1-50个字符之间', trigger: 'blur' }
  ],
  'device.ip': [
    { required: true, validator: validateIP, trigger: 'blur' }
  ],
  'device.username': [
    { required: true, message: '请输入操作系统用户名', trigger: 'blur' }
  ],
  'device.password': [
    { required: true, message: '请输入操作系统密码', trigger: 'blur' }
  ]
}

// 获取标签名称列表（用于快速查找）
const getTagNames = (): string[] => {
  return availableTags.value.map(tag => tag.name)
}

// 加载标签列表
const loadTags = async () => {
  try {
    tagsLoading.value = true
    const response = await tagApi.getTags()
    availableTags.value = response.tags || []
  } catch (error) {
    console.error('加载标签失败:', error)
    ElMessage.error('加载标签列表失败')
  } finally {
    tagsLoading.value = false
  }
}

// 创建新标签
const createTag = async (tagName: string) => {
  try {
    await tagApi.createTag({ name: tagName })
    // 创建成功后重新加载标签列表
    await loadTags()
    ElMessage.success(`标签 "${tagName}" 创建成功`)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || `创建标签 "${tagName}" 失败`)
    throw error // 重新抛出错误，让调用者处理
  }
}

// 处理标签变化
const handleTagChange = async (selectedTags: string[]) => {
  // 检查是否有新创建的标签（不在 availableTags 中）
  const tagNames = getTagNames()
  const newTags = selectedTags.filter(tag => !tagNames.includes(tag))
  
  for (const newTag of newTags) {
    if (newTag.trim()) {
      try {
        await createTag(newTag.trim())
      } catch (error) {
        // 如果创建失败，从当前选中中移除该标签
        const index = form.tags.indexOf(newTag)
        if (index > -1) {
          form.tags.splice(index, 1)
        }
      }
    }
  }
}

// 处理标签输入框失去焦点
const handleTagBlur = (event: FocusEvent) => {
  const input = event.target as HTMLInputElement
  const value = input.value?.trim()
  
  if (value && !form.tags.includes(value) && !getTagNames().includes(value)) {
    // 如果有输入值且不是已有标签，创建新标签
    createTag(value).then(() => {
      // 创建成功后添加到当前选中
      if (!form.tags.includes(value)) {
        form.tags.push(value)
      }
      input.value = '' // 清空输入框
    }).catch(() => {
      // 创建失败，不清空输入框，让用户重新输入
    })
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    loading.value = true

    // 直接提交表单，BMC IP 为 null 让后端自动生成
    await deviceApi.create(form)
    ElMessage.success('创建成功')
    router.push('/devices')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载标签
onMounted(() => {
  loadTags()
})
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>