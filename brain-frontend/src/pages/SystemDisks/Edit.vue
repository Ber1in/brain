<template>
  <div class="system-disk-edit">
    <el-card>
      <template #header>
        <h2>编辑系统磁盘</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="磁盘ID">
          <el-input v-model="diskId" disabled />
        </el-form-item>

        <el-form-item label="镜像">
          <el-input :value="originalData.image_id" disabled />
          <div class="readonly-info">镜像名称: {{ getImageName(originalData.image_id) }} ({{ originalData.mon_host }})</div>
        </el-form-item>

        <el-form-item label="MV200">
          <el-input :value="originalData.mv200_id" disabled />
          <div class="readonly-info">SOC IP: {{ originalData.mv200_ip }} 裸金属服务器: {{ getHostIP(originalData.mv200_id) }}</div>
        </el-form-item>

        <el-form-item label="磁盘大小">
          <el-input :value="`${originalData.size_gb} GB`" disabled />
        </el-form-item>

        <el-form-item label="创建人">
          <el-input :value="originalData.creator" disabled />
        </el-form-item>

        <el-form-item label="描述" prop="description">
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
          <el-button @click="$router.push('/system-disks')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { systemDisksApi } from '@/api/system-disks'
import { imagesApi } from '@/api/images'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import type { SystemDisk, SystemDiskUpdate, Image, MVServer, BareMetalServer } from '@/types/api'

const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const diskId = ref<string>('')
const images = ref<Image[]>([])
const bares = ref<BareMetalServer[]>([])
const mv200Servers = ref<MVServer[]>([])

const originalData = reactive({
  image_id: '',
  mv200_id: '',
  mv200_ip: '',
  size_gb: 0,
  mon_host: '',
  creator: '',
  description: ''
})

const form = ref<SystemDiskUpdate>({
  description: ''
})

const rules: FormRules = {
  description: [
    { max: 200, message: '描述长度不能超过200个字符', trigger: 'blur' }
  ]
}

// 计算属性：创建ID到名称的映射
const imageMap = computed(() => {
  const map = new Map<string, string>()
  images.value.forEach(image => {
    map.set(image.id, image.name)
  })
  return map
})

const mv200Map = computed(() => {
  const map = new Map<string, string>()
  mv200Servers.value.forEach(server => {
    map.set(server.id, server.bare_id)
  })
  return map
})

const bareMap = computed(() => {
  const map = new Map<string, string>()
  bares.value.forEach(bare => {
    map.set(bare.id, bare.host_ip)
  })
  return map
})

// 根据ID获取名称
const getImageName = (imageId: string) => {
  return imageMap.value.get(imageId) || imageId
}

const getBareID = (mv200_id: string) => {
  return mv200Map.value.get(mv200_id)
}

const getHostIP = (mv200_id: string) => {
  const bare_id = getBareID(mv200_id)
  return bareMap.value.get(bare_id)
}

// 加载资源数据
const loadResources = async () => {
  try {
    const [imagesResponse, serversResponse, baresResponse] = await Promise.all([
      imagesApi.getAll(),
      mv200Api.getAll(),
      bareApi.getAll(),
    ])
    images.value = imagesResponse
    mv200Servers.value = serversResponse
    bares.value = baresResponse
  } catch (error) {
    console.error('加载资源数据失败:', error)
  }
}

// 加载磁盘数据
const loadDiskData = async () => {
  try {
    const disk = await systemDisksApi.getById(diskId.value)
    originalData.image_id = disk.image_id
    originalData.mv200_id = disk.mv200_id
    originalData.mv200_ip = disk.mv200_ip
    originalData.size_gb = disk.size_gb
    originalData.mon_host = disk.mon_host
    originalData.creator = disk.creator || ''
    originalData.description = disk.description || ''
    
    form.value.description = disk.description || ''
  } catch (error) {
    ElMessage.error('加载磁盘数据失败')
    router.push('/system-disks')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await systemDisksApi.update(diskId.value, form.value)
    ElMessage.success('更新成功')
    router.push('/system-disks')
  } catch (error) {
    ElMessage.error('更新失败')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  diskId.value = route.params.id as string
  if (!diskId.value) {
    ElMessage.error('磁盘ID不能为空')
    router.push('/system-disks')
    return
  }
  
  await loadResources()
  await loadDiskData()
})
</script>
