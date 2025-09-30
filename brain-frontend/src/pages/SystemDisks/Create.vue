<template>
  <div class="create-disk">
    <el-card>
      <template #header>
        <h2>创建系统磁盘</h2>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="镜像" prop="system_disk.image_id">
          <el-select
            v-model="form.system_disk.image_id"
            placeholder="选择镜像"
            style="width: 100%"
            filterable
            @change="handleImageChange"
          >
            <el-option
              v-for="image in images"
              :key="image.id"
              :label="image.name"
              :value="image.id"
            >
              <span>{{ image.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                {{ image.mon_host }}
              </span>
            </el-option>
          </el-select>
          <div v-if="selectedImage" style="margin-top: 8px; color: #606266; font-size: 12px;">
            镜像最小要求: {{ selectedImage.min_size }} GB
          </div>
        </el-form-item>

        <el-form-item label="MV200服务器" prop="system_disk.mv200_id">
          <el-select
            v-model="form.system_disk.mv200_id"
            placeholder="选择MV200服务器"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="server in mv200Servers"
              :key="server.id"
              :label="`${server.name} (${server.ip_address})`"
              :value="server.id"
            >
              <span>{{ server.name }} ({{ server.ip_address }})</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                {{ getHostIP(server.bare_id) }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="磁盘大小(GB)" prop="system_disk.size_gb">
          <el-input-number
            v-model="form.system_disk.size_gb"
            :min="minDiskSize"
            controls-position="right"
          />
        </el-form-item>

        <el-form-item label="flatten" prop="system_disk.flatten">
          <template #label>
            <span>flatten</span>
            <el-tooltip 
              effect="dark" 
              content="flatten操作增加系统盘创建的耗时，但系统盘的性能会有所提升"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <el-radio-group v-model="form.system_disk.flatten">
            <el-radio :label="true">是</el-radio>
            <el-radio :label="false">否</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="系统用户名" prop="system_user.name">
          <el-input v-model="form.system_user.name" placeholder="输入系统用户名" />
        </el-form-item>

        <el-form-item label="系统密码" prop="system_user.password">
          <el-input
            v-model="form.system_user.password"
            type="password"
            placeholder="输入系统密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="form.system_disk.description"
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
import { ref, onMounted, computed } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { imagesApi } from '@/api/images'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import { systemDisksApi } from '@/api/system-disks'
import type { Image, MVServer, BareMetalCreate } from '@/types/api'

const formRef = ref<FormInstance>()
const loading = ref(false)
const images = ref<Image[]>([])
const mv200Servers = ref<MVServer[]>([])
const bares = ref<BareMetalServer[]>([])

// 初始化表单，size_gb 先设为 0，选择镜像后会自动更新
const form = ref<BareMetalCreate>({
  system_disk: {
    image_id: '',
    mv200_id: '',
    size_gb: 0, // 初始设为 0，选择镜像后更新为 min_size
    flatten: false, // 新增 flatten 属性，默认 false
    description: '',
  },
  system_user: {
    name: '',
    password: '',
  },
})

const bareMap = computed(() => {
  const map = new Map<string, string>()
  bares.value.forEach(bare => {
    map.set(bare.id, bare)
  })
  return map
})

// 根据ID获取裸金属服务器
const getHostIP = (bare_id: string) => {
  const bare = bareMap.value.get(bare_id);
  if (!bare) return '未配置';

  return `${bare.name} (${bare.host_ip})`;
}

// 计算选中的镜像
const selectedImage = computed(() => {
  if (!form.value.system_disk.image_id) return null
  return images.value.find(img => img.id === form.value.system_disk.image_id) || null
})

// 计算最小磁盘大小
const minDiskSize = computed(() => {
  if (!selectedImage.value) return 1
  return Math.max(1, selectedImage.value.min_size || 1)
})

const rules: FormRules = {
  'system_disk.image_id': [{ required: true, message: '请选择镜像', trigger: 'change' }],
  'system_disk.mv200_id': [{ required: true, message: '请选择MV200服务器', trigger: 'change' }],
  'system_disk.size_gb': [
    { required: true, message: '请输入磁盘大小', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (!selectedImage.value) {
          callback(new Error('请先选择镜像'))
          return
        }
        if (value < minDiskSize.value) {
          callback(new Error(`磁盘大小不能小于镜像最小要求 (${minDiskSize.value} GB)`))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  'system_user.name': [{ required: true, message: '请输入系统用户名', trigger: 'blur' }],
  'system_user.password': [{ required: true, message: '请输入系统密码', trigger: 'blur' }],
}

// 镜像选择变化处理
const handleImageChange = (imageId: string) => {
  const image = images.value.find(img => img.id === imageId)
  if (image) {
    // 将磁盘大小设置为镜像的 min_size
    form.value.system_disk.size_gb = image.min_size || 10
  }
}

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
    ElMessage.error('加载资源失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  // 再次验证磁盘大小
  if (!selectedImage.value) {
    ElMessage.error('请先选择镜像')
    return
  }
  
  if (form.value.system_disk.size_gb < minDiskSize.value) {
    ElMessage.error(`磁盘大小不能小于镜像最小要求 (${minDiskSize.value} GB)`)
    return
  }

  loading.value = true
  try {
    await systemDisksApi.create(form.value)
    ElMessage.success('创建成功')
    window.location.href = '/system-disks'
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadResources()
})
</script>
