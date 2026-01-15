<template>
  <div class="system-disks-mv200">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-info">
            <div class="title-section">
              <h3>云系统盘管理</h3>
              <div class="mv200-info">
                <el-tag type="primary" size="large" class="name-tag">
                  <el-icon><Cpu /></el-icon>
                  {{ mv200Info.name }}
                </el-tag>
                <el-tag type="info" size="large">
                  <el-icon><Link /></el-icon>
                  {{ mv200Info.ip }}
                </el-tag>
              </div>
            </div>
            <div class="action-buttons">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索UUID、网关节点、镜像、块设备"
                clearable
                style="width: 300px; margin-right: 16px;"
                @input="handleSearch"
                @clear="handleSearch"
              >
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>
              <el-button 
                type="primary" 
                @click="showCreateDialog"
                :loading="loading"
              >
                <el-icon><Plus /></el-icon>
                创建云系统盘
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <el-table 
        :data="filteredDisks" 
        v-loading="loading"
        style="width: 100%"
      >
        <!-- 1. UUID列 -->
        <el-table-column 
          prop="uuid" 
          label="UUID" 
          width="120"
          sortable
        >
          <template #default="{ row }">
            <el-tag :type="isCloudInitBdev(row) ? 'info' : 'success'" size="small">
              {{ row.uuid }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- 2. 网关节点列 - 加宽并左对齐 -->
        <el-table-column 
          label="网关节点"
          width="220"
          align="left"
        >
          <template #default="{ row }">
            <div class="gateway-nodes">
              <div v-if="isCloudInitBdev(row)" class="cloudinit-info">
                <el-tag type="info" size="small">cloudinit数据源</el-tag>
              </div>
              <div v-else-if="row.backend_specific?.block?.gws?.length" class="gateway-list">
                <div v-for="(gw, index) in row.backend_specific.block.gws" :key="index" class="gateway-item">
                  <el-tag size="small" class="gateway-tag">
                    <el-icon><Monitor /></el-icon>
                    {{ gw }}
                  </el-tag>
                </div>
              </div>
              <span v-else class="empty-text">-</span>
            </div>
          </template>
        </el-table-column>
        
        <!-- 3. 块设备列 (显示RBD路径) -->
        <el-table-column 
          label="块设备"
          min-width="200"
          show-overflow-tooltip
          align="left"
        >
          <template #default="{ row }">
            <div v-if="row.backend_specific?.block?.rbd_path" class="rbd-path-cell">
              <span class="rbd-path">
                {{ row.backend_specific.block.rbd_path }}
              </span>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <!-- 4. 镜像列 -->
        <el-table-column 
          label="镜像"
          min-width="180"
          show-overflow-tooltip
          align="left"
        >
          <template #default="{ row }">
            <div v-if="row.backend_specific?.block?.parent" class="image-cell">
              <el-tag type="warning" size="small" class="parent-tag">
                {{ getImageName(row.backend_specific.block.parent) }}
              </el-tag>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <!-- 5. 大小列 -->
        <el-table-column 
          label="大小(GB)"
          width="120"
          sortable
          :sort-method="sizeSortMethod"
          align="left"
        >
          <template #default="{ row }">
            <div v-if="row.backend_specific?.block?.size" class="size-cell">
              <span class="size-text">{{ row.backend_specific.block.size }}</span>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <!-- 操作列 -->
        <el-table-column 
          label="操作" 
          width="100" 
          fixed="right"
          align="center"
        >
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button type="primary" link>
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <!-- 详细信息 -->
                  <el-dropdown-item command="detail" class="dropdown-item">
                    <el-icon><View /></el-icon>
                    <span>详情</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态提示 -->
      <div v-if="filteredDisks.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无云系统盘">
          <el-button type="primary" @click="showCreateDialog">
            创建云系统盘
          </el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 详细信息对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="云系统盘详细信息"
      width="600px"
    >
      <el-descriptions :column="1" border v-if="currentDisk">
        <el-descriptions-item label="UUID">
          <el-tag :type="isCloudInitBdev(currentDisk) ? 'info' : 'success'">
            {{ currentDisk.uuid }}
          </el-tag>
        </el-descriptions-item>
        
        <el-descriptions-item label="控制器">
          {{ currentDisk.ctrlr }}
        </el-descriptions-item>
        
        <el-descriptions-item label="CPU核心掩码">
          <el-tag size="small">{{ currentDisk.cpumask }}</el-tag>
        </el-descriptions-item>
        
        <el-descriptions-item label="虚拟队列">
          <div>数量: {{ currentDisk.vq_count }}</div>
          <div>大小: {{ currentDisk.vq_size }}</div>
        </el-descriptions-item>
        
        <el-descriptions-item label="bdev名称">
          <code>{{ currentDisk.backend_specific?.block?.bdev }}</code>
          <el-tag 
            v-if="isCloudInitBdev(currentDisk)" 
            type="info" 
            size="small" 
            style="margin-left: 8px;"
          >
            cloudinit数据源
          </el-tag>
        </el-descriptions-item>
        
        <el-descriptions-item label="RBD路径">
          <code>{{ currentDisk.backend_specific?.block?.rbd_path || '-' }}</code>
        </el-descriptions-item>
        
        <el-descriptions-item label="镜像路径">
          <code>{{ currentDisk.backend_specific?.block?.parent || '-' }}</code>
        </el-descriptions-item>
        
        <el-descriptions-item label="网关节点">
          <div v-if="currentDisk.backend_specific?.block?.gws?.length" class="gateway-detail">
            <el-tag
              v-for="(gw, index) in currentDisk.backend_specific.block.gws"
              :key="index"
              size="small"
              style="margin-right: 8px; margin-bottom: 4px;"
            >
              {{ gw }}
            </el-tag>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>
        
        <el-descriptions-item label="大小">
          <span v-if="currentDisk.backend_specific?.block?.size" class="size-text">
            {{ currentDisk.backend_specific.block.size }} GB
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        
        <el-descriptions-item label="状态">
          <el-tag :type="currentDisk.backend_specific?.block?.readonly ? 'warning' : 'success'">
            {{ currentDisk.backend_specific?.block?.readonly ? '只读' : '读写' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 创建云系统盘对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建云系统盘"
      width="700px"
      :close-on-click-modal="false"
      @closed="handleDialogClosed"
    >
      <el-form 
        :model="createForm" 
        :rules="createRules" 
        ref="createFormRef" 
        label-width="140px"
        class="create-form"
      >
        <!-- 镜像选择 -->
        <el-form-item label="选择镜像" prop="system_disk.image_id">
          <el-select
            v-model="createForm.system_disk.image_id"
            placeholder="请选择镜像"
            style="width: 100%"
            clearable
            @change="handleImageChange"
            :loading="imagesLoading"
          >
            <el-option
              v-for="image in images"
              :key="image.id"
              :label="`${image.name} (${image.mon_host})`"
              :value="image.id"
            />
          </el-select>
        </el-form-item>

        <!-- 系统盘容量 -->
        <el-form-item label="系统盘容量(GB)" prop="system_disk.size_gb">
          <el-input-number
            v-model="createForm.system_disk.size_gb"
            :min="selectedImage ? selectedImage.min_size : 1"
            :max="1024"
            controls-position="right"
            style="width: 200px"
          />
          <div class="form-tip">
            镜像要求的最小容量 {{ selectedImage ? selectedImage.min_size : 1 }} GB
          </div>
        </el-form-item>

        <!-- Flatten开关 -->
        <el-form-item label="Flatten">
          <el-switch
            v-model="createForm.system_disk.flatten"
            active-text="是"
            inactive-text="否"
          />
          <el-tooltip 
            effect="dark" 
            content="flatten操作增加系统盘创建的耗时，但系统盘会脱离对镜像的依赖，性能会有所提升"
            placement="top"
          >
            <el-icon style="margin-left: 8px; cursor: help;">
              <QuestionFilled />
            </el-icon>
          </el-tooltip>
        </el-form-item>

        <!-- 虚拟队列配置 -->
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="虚拟队列数量" prop="system_disk.vq_count">
              <el-input-number
                v-model="createForm.system_disk.vq_count"
                :min="1"
                :max="16"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="虚拟队列大小" prop="system_disk.vq_size">
              <el-input-number
                v-model="createForm.system_disk.vq_size"
                :min="256"
                :max="1024"
                :step="256"
                controls-position="right"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- Ceph Monitor地址 -->
        <el-form-item label="Ceph Monitor地址" prop="system_disk.mon_hosts">
          <el-input
            v-model="createForm.system_disk.mon_hosts"
            placeholder="多个mon_host地址用逗号分隔"
            clearable
            @blur="formatMonHosts"
          />
        </el-form-item>

        <!-- 存储池 -->
        <el-form-item label="存储池" prop="system_disk.pool">
          <el-input
            v-model="createForm.system_disk.pool"
            placeholder="请输入存储池名称"
            clearable
            style="width: 200px"
          />
        </el-form-item>

        <!-- 系统盘设备名称 -->
        <el-form-item label="系统盘设备名称" prop="system_disk.disk_id">
          <el-input
            v-model="createForm.system_disk.disk_id"
            placeholder="只能包含字母、数字、点、下划线和连字符"
            clearable
            style="width: 300px"
          />
          <div class="form-tip">
            若不填，则系统会自动生成一个UUID4作为名称
          </div>
        </el-form-item>

        <!-- 系统用户配置 -->
        <div class="form-section">
          <div class="section-title">
            <el-icon><User /></el-icon>
            <span>系统用户配置</span>
          </div>
          
          <!-- 用户名 -->
          <el-form-item label="用户名" prop="system_user.name">
            <el-input
              v-model="createForm.system_user.name"
              placeholder="请输入系统用户名"
              clearable
              style="width: 300px"
            />
          </el-form-item>
          
          <!-- 密码 -->
          <el-form-item label="密码" prop="system_user.password">
            <el-input
              v-model="createForm.system_user.password"
              placeholder="请输入系统用户密码"
              clearable
              :type="showPassword ? 'text' : 'password'"
              style="width: 300px"
            >
              <template #suffix>
                <el-icon 
                  @click="showPassword = !showPassword"
                  style="cursor: pointer;"
                >
                  <View v-if="showPassword" />
                  <Hide v-else />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>
        </div>
      </el-form>
      
      <div class="warning-message">
        <el-alert
          title="重要提示"
          type="warning"
          :closable="false"
          description="创建系统盘操作需要一定时间，请耐心等待。系统盘创建过程中请不要关闭此对话框。"
          show-icon
        />
      </div>
      
      <template #footer>
        <el-button @click="createDialogVisible = false" :disabled="creating">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleCreateSystemDisk" 
          :loading="creating"
        >
          确认创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { 
  Refresh, 
  View,
  Monitor,
  Cpu,
  Link,
  MoreFilled,
  Plus,
  QuestionFilled,
  User,
  Hide,
  Search
} from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { imagesApi } from '@/api/images'
import type { ControllerInfo } from '@/types/api'
import type { Image } from '@/types/api'

const route = useRoute()
const loading = ref(false)
const imagesLoading = ref(false)
const creating = ref(false)
const systemDisks = ref<ControllerInfo[]>([])
const currentDisk = ref<ControllerInfo | null>(null)
const detailDialogVisible = ref(false)
const createDialogVisible = ref(false)
const showPassword = ref(false)
const createFormRef = ref<FormInstance>()
const images = ref<Image[]>([])
const selectedImage = ref<Image | null>(null)
const searchKeyword = ref('')

const mv200Info = ref({
  id: route.params.mv200Id as string,
  name: route.query.name as string || '',
  ip: route.query.ip as string || ''
})

// 创建表单数据
const createForm = reactive({
  system_disk: {
    image_id: '',
    size_gb: 20,
    mon_hosts: '',
    vq_count: 2,
    vq_size: 512,
    disk_id: '',
    pool: 'compute',
    flatten: false
  },
  system_user: {
    name: 'root',
    password: ''
  }
})

// 表单验证规则
const createRules: FormRules = {
  'system_disk.image_id': [
    { required: true, message: '请选择镜像', trigger: 'change' }
  ],
  'system_disk.size_gb': [
    { required: true, message: '请输入系统盘容量', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (selectedImage.value && value < selectedImage.value.min_size) {
          callback(new Error(`系统盘容量不能小于${selectedImage.value.min_size}GB`))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  'system_disk.mon_hosts': [
    { required: true, message: '请输入Ceph Monitor地址', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback(new Error('Ceph Monitor地址不能为空'))
          return
        }
        
        const hosts = value.split(',').map(host => host.trim()).filter(host => host)
        if (hosts.length === 0) {
          callback(new Error('请至少输入一个Ceph Monitor地址'))
          return
        }
        
        // 验证IP地址格式
        const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/
        for (const host of hosts) {
          if (!ipRegex.test(host)) {
            callback(new Error(`Ceph Monitor地址格式错误: ${host}`))
            return
          }
        }
        
        callback()
      },
      trigger: 'blur'
    }
  ],
  'system_disk.pool': [
    { required: true, message: '请输入存储池名称', trigger: 'blur' }
  ],
  'system_disk.disk_id': [
    {
      validator: (rule, value, callback) => {
        if (!value) {
          callback()
          return
        }
        
        const diskIdPattern = /^[A-Za-z0-9._-]+$/
        if (!diskIdPattern.test(value)) {
          callback(new Error('系统盘设备名称只能包含字母、数字、点、下划线和连字符'))
          return
        }
        
        callback()
      },
      trigger: 'blur'
    }
  ],
  'system_user.name': [
    { required: true, message: '请输入系统用户名', trigger: 'blur' },
    { min: 1, max: 32, message: '用户名长度在1到32个字符之间', trigger: 'blur' }
  ],
  'system_user.password': [
    { required: true, message: '请输入系统用户密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能小于6个字符', trigger: 'blur' }
  ]
}

// 检查是否为cloudinit数据源
const isCloudInitBdev = (disk: ControllerInfo): boolean => {
  return disk.backend_specific?.block?.bdev === 'yunsilicon_cloudinit_bdev'
}

// 从完整的镜像路径中提取镜像名称
const getImageName = (fullPath: string): string => {
  if (!fullPath) return '-'
  const parts = fullPath.split('/')
  return parts[parts.length - 1] || fullPath
}

// 大小排序方法
const sizeSortMethod = (a: ControllerInfo, b: ControllerInfo) => {
  const sizeA = a.backend_specific?.block?.size || 0
  const sizeB = b.backend_specific?.block?.size || 0
  return sizeA - sizeB
}

// 加载云系统盘数据
const loadSystemDisks = async () => {
  loading.value = true
  try {
    console.log('正在加载MV200系统盘，ID:', mv200Info.value.id)
    const response = await mv200Api.getSystemDisks(mv200Info.value.id)
    systemDisks.value = response
    
    // 按UUID排序
    systemDisks.value.sort((a, b) => a.uuid - b.uuid)
    console.log('加载成功，共', systemDisks.value.length, '个系统盘')
    
  } catch (error: any) {
    ElMessage.error('加载云系统盘失败: ' + (error.message || '未知错误'))
    console.error('加载云系统盘失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载镜像列表
const loadImages = async () => {
  imagesLoading.value = true
  try {
    const response = await imagesApi.getAll()
    images.value = response
    console.log('镜像列表加载成功，共', images.value.length, '个镜像')
  } catch (error: any) {
    ElMessage.error('加载镜像列表失败: ' + (error.message || '未知错误'))
    console.error('加载镜像列表失败:', error)
  } finally {
    imagesLoading.value = false
  }
}

// 计算属性：搜索过滤
const filteredDisks = computed(() => {
  if (!searchKeyword.value) {
    return systemDisks.value
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return systemDisks.value.filter(disk => {
    // 搜索UUID
    if (disk.uuid.toString().includes(keyword)) return true
    
    // 搜索网关节点
    if (disk.backend_specific?.block?.gws?.some(gw => 
      gw.toLowerCase().includes(keyword)
    )) return true
    
    // 搜索镜像
    if (disk.backend_specific?.block?.parent?.toLowerCase().includes(keyword)) return true
    
    // 搜索块设备
    if (disk.backend_specific?.block?.bdev?.toLowerCase().includes(keyword)) return true
    
    // 搜索RBD路径
    if (disk.backend_specific?.block?.rbd_path?.toLowerCase().includes(keyword)) return true
    
    return false
  })
})

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑在computed属性中处理
}

// 刷新数据
const refreshData = () => {
  loadSystemDisks()
}

// 显示创建对话框
const showCreateDialog = async () => {
  // 先加载镜像列表
  await loadImages()
  createDialogVisible.value = true
}

// 处理镜像选择变化
const handleImageChange = (imageId: string) => {
  selectedImage.value = images.value.find(img => img.id === imageId) || null
  if (selectedImage.value && createForm.system_disk.size_gb < selectedImage.value.min_size) {
    createForm.system_disk.size_gb = selectedImage.value.min_size
  }
}

// 格式化Monitor地址
const formatMonHosts = () => {
  if (createForm.system_disk.mon_hosts) {
    createForm.system_disk.mon_hosts = createForm.system_disk.mon_hosts
      .split(',')
      .map(host => host.trim())
      .filter(host => host)
      .join(',')
  }
}

// 处理对话框关闭
const handleDialogClosed = () => {
  // 重置表单
  createFormRef.value?.resetFields()
  selectedImage.value = null
  createForm.system_disk = {
    image_id: '',
    size_gb: 20,
    mon_hosts: '',
    vq_count: 2,
    vq_size: 512,
    disk_id: '',
    pool: 'compute',
    flatten: false
  }
  createForm.system_user = {
    name: 'root',
    password: ''
  }
}

// 创建云系统盘
const handleCreateSystemDisk = async () => {
  if (!createFormRef.value) return
  
  try {
    // 验证表单
    await createFormRef.value.validate()
    
    // 确认创建
    await ElMessageBox.confirm(
      '确认要创建云系统盘吗？此操作需要一定时间，请耐心等待。',
      '确认创建',
      {
        type: 'warning',
        confirmButtonText: '确认创建',
        cancelButtonText: '取消'
      }
    )
    
    creating.value = true
    
    // 准备请求数据
    const requestData: any = {
      system_disk: {
        image_id: createForm.system_disk.image_id,
        size_gb: createForm.system_disk.size_gb,
        mon_hosts: createForm.system_disk.mon_hosts
          .split(',')
          .map(host => host.trim())
          .filter(host => host),
        vq_count: createForm.system_disk.vq_count,
        vq_size: createForm.system_disk.vq_size,
        pool: createForm.system_disk.pool,
        flatten: createForm.system_disk.flatten
      },
      system_user: createForm.system_user
    }
    
    // 只有在 disk_id 有值时才添加这个参数
    if (createForm.system_disk.disk_id && createForm.system_disk.disk_id.trim() !== '') {
      requestData.system_disk.disk_id = createForm.system_disk.disk_id.trim()
    }
    
    console.log('创建云系统盘请求数据:', requestData)
    
    // 调用API
    const response = await mv200Api.createSystemDisk(mv200Info.value.id, requestData)
    
    // 处理响应
    let successMessage = '云系统盘创建成功'
    let warningMessage = ''
    
    if (response.efi_status === 1) {
      warningMessage += '• 启动项创建失败，需要重启系统完成启动项创建\n'
    }
    
    if (response.cloudinit_status === 1) {
      warningMessage += '• cloud-init数据源创建失败，可能导致系统无法自动配置管理IP及用户密码\n'
    }
    
    if (warningMessage) {
      ElMessage.warning({
        message: `${successMessage}，但存在以下问题：\n${warningMessage}`,
        duration: 8000,
        showClose: true
      })
    } else {
      ElMessage.success(successMessage)
    }
    
    // 关闭对话框并刷新数据
    createDialogVisible.value = false
    loadSystemDisks()
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      // 用户取消创建
      return
    }
    
    ElMessage.error('创建云系统盘失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    console.error('创建云系统盘失败:', error)
  } finally {
    creating.value = false
  }
}

// 操作命令处理
const handleCommand = (command: string, disk: ControllerInfo) => {
  switch (command) {
    case 'detail':
      showDiskDetail(disk)
      break
  }
}

// 显示详细信息
const showDiskDetail = (disk: ControllerInfo) => {
  currentDisk.value = disk
  detailDialogVisible.value = true
}

onMounted(() => {
  console.log('页面挂载，MV200信息:', mv200Info.value)
  loadSystemDisks()
})
</script>

<style scoped>
.card-header {
  margin-bottom: 0;
}

.header-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  width: 100%;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-section h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.mv200-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.name-tag {
  font-weight: 500;
}

.name-tag .el-icon,
.ip-tag .el-icon {
  margin-right: 4px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 表格样式 - 确保左对齐 */
.gateway-nodes {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}

.gateway-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
}

.gateway-item {
  display: flex;
  justify-content: flex-start;
  width: 100%;
}

.gateway-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-start;
  text-align: left;
}

/* 强制表格单元格左对齐 */
:deep(.el-table__cell) {
  text-align: left !important;
}

/* 特别为每个单元格设置左对齐 */
:deep(.el-table__cell .cell) {
  display: flex;
  justify-content: flex-start !important;
  text-align: left !important;
  align-items: center;
}

/* 网关节点列特别处理 */
:deep(.el-table__cell:nth-child(2) .cell) {
  justify-content: flex-start !important;
  padding-left: 0 !important;
}

.cloudinit-info {
  display: flex;
  justify-content: flex-start;
  width: 100%;
}

/* 其他单元格样式 */
.rbd-path-cell, .image-cell, .size-cell {
  display: flex;
  justify-content: flex-start;
  text-align: left;
}

.rbd-path {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: #409eff;
  text-align: left;
  word-break: break-all;
}

.parent-tag {
  font-family: 'Monaco', 'Consolas', monospace;
  text-align: left;
}

.size-text {
  color: #67c23a;
  font-weight: 500;
  text-align: left;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
  text-align: left;
}

/* 空状态样式 */
.empty-state {
  padding: 60px 0;
}

/* 操作下拉菜单样式 */
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  color: #f56c6c;
  background-color: #fef0f0;
}

/* 描述列表样式 */
:deep(.el-descriptions__label) {
  font-weight: 600;
  width: 120px;
}

:deep(.el-descriptions__content) {
  font-family: 'Monaco', 'Consolas', monospace;
}

:deep(code) {
  background-color: #f6f8fa;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 12px;
}

/* 详情对话框中的网关节点样式 */
.gateway-detail {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 4px;
}

/* 创建表单样式 */
.create-form {
  margin-top: 10px;
}

.form-section {
  margin-bottom: 20px;
  padding: 16px;
  background-color: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-title .el-icon {
  color: #409eff;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

.warning-tip {
  color: #e6a23c;
  font-weight: 500;
}

.warning-message {
  margin-top: 20px;
}

/* 密码输入框图标样式 */
:deep(.el-input__suffix) {
  cursor: pointer;
}

:deep(.el-input__suffix .el-icon) {
  color: #c0c4cc;
}

:deep(.el-input__suffix .el-icon:hover) {
  color: #409eff;
}

/* 搜索框样式 */
:deep(.el-input__wrapper) {
  border-radius: 4px;
}
</style>