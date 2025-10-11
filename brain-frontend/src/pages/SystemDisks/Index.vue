<template>
  <div class="system-disks">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>裸金属云系统磁盘</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索ID、镜像名、SOC IP、裸金属服务器、创建人或描述"
              clearable
              style="width: 410px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="$router.push('/system-disks/create')">
              创建云系统盘
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredDisks" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="200" />
        <el-table-column label="镜像名称">
          <template #default="{ row }">
            <template v-if="imageMap.get(row.image_id)">
              <span class="highlight-name">{{ getImageName(row.image_id) }}</span>
              <span class="highlight-ip">({{ row.mon_host }})</span>
            </template>
            <template v-else>
              <span class="highlight-deleted">镜像已删除</span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="SOC IP">
          <template #default="{ row }">
            <span class="highlight-name">{{ getMV200Name(row.mv200_id) }}</span>
            <span class="highlight-ip">({{ row.mv200_ip }})</span>
          </template>
        </el-table-column>
        <el-table-column label="裸金属服务器">
          <template #default="{ row }">
            <span class="highlight-name">{{ getHostName(row.mv200_id) }}</span>
            <span class="highlight-ip">({{ getHostIP(row.mv200_id) }})</span>
          </template>
        </el-table-column>
        <el-table-column prop="size_gb" label="磁盘大小(GB)" width="120">
          <template #default="{ row }">
            <span class="highlight-size">{{ row.size_gb }} GB</span>
          </template>
        </el-table-column>
        <el-table-column label="Flatten" width="120">
          <template #header>
            <span>Flatten</span>
            <el-tooltip 
              effect="dark" 
              content="已经flatten过的系统盘性能会有所提升"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span :class="row.flatten ? 'highlight-true' : 'highlight-false'">
              {{ row.flatten ? '是' : '否' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="creator" label="创建人" width="90">
          <template #default="{ row }">
            <span class="highlight-creator">{{ row.creator }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button type="primary" link>
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">
                    <el-icon><Edit /></el-icon>
                    <span>编辑</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="upload" divided>
                    <el-icon><Upload /></el-icon>
                    <span>保存为镜像</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="rebuild">
                    <el-icon><Refresh /></el-icon>
                    <span>重置镜像</span>
                  </el-dropdown-item>
                  <el-dropdown-item 
                    command="flatten" 
                    :disabled="row.flatten"
                  >
                    <el-icon><Operation /></el-icon>
                    <span>Flatten</span>
                    <el-tooltip 
                      v-if="row.flatten" 
                      effect="dark" 
                      content="该云盘已经flatten" 
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;">
                        <InfoFilled />
                      </el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided class="danger-item">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 保存为镜像对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="保存系统盘为新镜像"
      width="500px"
    >
      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="名称">
          <el-input
            v-model="uploadForm.dest_name"
            placeholder="请输入新镜像名称（可选）"
            clearable
          />
          <div class="form-tip">如不填写，系统将自动生成镜像名称</div>
        </el-form-item>
        <el-form-item label="存储池">
          <el-input
            v-model="uploadForm.dest_pool"
            placeholder="请输入目标存储池（可选）"
            clearable
          />
          <div class="form-tip">如不填写，将保存到镜像默认存储池 images</div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入镜像描述（可选）"
            clearable
          />
        </el-form-item>
      </el-form>
      
      <div class="warning-message">
        <el-alert
          title="重要提示"
          type="warning"
          :closable="false"
          description="请确认该系统盘不在使用中，若系统盘依旧存在IO，保存的新镜像数据可能不完整。"
          show-icon
        />
      </div>
      
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload" :loading="uploadLoading">
          确认保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置镜像对话框 -->
    <el-dialog
      v-model="rebuildDialogVisible"
      title="重置系统盘镜像"
      width="500px"
    >
      <el-form :model="rebuildForm" label-width="120px">
        <el-form-item label="选择镜像">
          <el-select
            v-model="rebuildForm.image_id"
            placeholder="请选择镜像"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="image in images"
              :key="image.id"
              :label="`${image.name} (${image.mon_host})`"
              :value="image.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <div class="warning-message">
        <el-alert
          title="重要提示"
          type="warning"
          :closable="false"
          description="重置镜像操作，将会丢失当前系统盘内所有数据。此操作不可逆，请谨慎操作！"
          show-icon
        />
      </div>
      
      <template #footer>
        <el-button @click="rebuildDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRebuild" :loading="rebuildLoading" style="background-color: #e6a23c; border-color: #e6a23c;">
          确认重置
        </el-button>
      </template>
    </el-dialog>

    <!-- Flatten确认对话框 -->
    <el-dialog
      v-model="flattenDialogVisible"
      title="确认Flatten操作"
      width="400px"
    >
      <div class="warning-message">
        <el-alert
          title="重要提示"
          type="warning"
          :closable="false"
          description="Flatten操作完成后将不再依赖镜像，提升系统盘性能。但Flatten过程中磁盘性能可能有所下降"
          show-icon
        />
      </div>
      <div class="confirm-message">
        <p>确定要对系统磁盘 <strong>"{{ currentDisk?.id }}"</strong> 执行Flatten操作吗？</p>
      </div>
      
      <template #footer>
        <el-button @click="flattenDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmFlatten" 
          :loading="flattenLoading"
        >
          确认Flatten
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled, MoreFilled, Edit, Upload, Refresh, Delete, Operation, InfoFilled, Search } from '@element-plus/icons-vue'
import { systemDisksApi } from '@/api/system-disks'
import { imagesApi } from '@/api/images'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import type { SystemDisk, Image, MVServer, BareMetalServer } from '@/types/api'

const loading = ref(false)
const disks = ref<SystemDisk[]>([])
const images = ref<Image[]>([])
const mv200Servers = ref<MVServer[]>([])
const bares = ref<BareMetalServer[]>([])
const searchKeyword = ref('')

// 上传为镜像相关
const uploadDialogVisible = ref(false)
const uploadLoading = ref(false)
const currentDisk = ref<SystemDisk | null>(null)
const uploadForm = reactive({
  dest_name: '',
  dest_pool: '',
  description: ''
})

// 重置镜像相关
const rebuildDialogVisible = ref(false)
const rebuildLoading = ref(false)
const rebuildForm = reactive({
  image_id: ''
})

// Flatten相关
const flattenDialogVisible = ref(false)
const flattenLoading = ref(false)

// 计算属性：创建ID到名称的映射
const imageMap = computed(() => {
  const map = new Map<string, string>()
  images.value.forEach(image => {
    map.set(image.id, image.name)
  })
  return map
})

const mv200Map = computed(() => {
  const map = new Map<string, MVServer>()
  mv200Servers.value.forEach(server => {
    map.set(server.id, server)
  })
  return map
})

const bareMap = computed(() => {
  const map = new Map<string, BareMetalServer>()
  bares.value.forEach(bare => {
    map.set(bare.id, bare)
  })
  return map
})

// 计算属性：过滤磁盘列表
const filteredDisks = computed(() => {
  if (!searchKeyword.value) {
    return disks.value
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return disks.value.filter(disk => {
    // 搜索ID
    if (disk.id.toLowerCase().includes(keyword)) return true
    
    // 搜索镜像名
    const imageName = getImageName(disk.image_id).toLowerCase()
    if (imageName.includes(keyword)) return true
    
    // 搜索SOC IP
    if (disk.mv200_ip.toLowerCase().includes(keyword)) return true
    
    // 搜索裸金属服务器信息
    const hostName = getHostName(disk.mv200_id).toLowerCase()
    const hostIP = getHostIP(disk.mv200_id).toLowerCase()
    if (hostName.includes(keyword) || hostIP.includes(keyword)) return true
    
    // 搜索创建人
    if (disk.creator && disk.creator.toLowerCase().includes(keyword)) return true
    
    // 搜索描述
    if (disk.description && disk.description.toLowerCase().includes(keyword)) return true
    
    return false
  })
})

// 根据ID获取镜像名称
const getImageName = (imageId: string) => {
  return imageMap.value.get(imageId) || "镜像已删除"
}

// 根据ID获取SOC IP名称
const getMV200Name = (serverId: string) => {
  const server = mv200Map.value.get(serverId)
  return server?.name || serverId
}

// 根据ID获取裸金属服务器名称
const getHostName = (mv200_id: string) => {
  const server = mv200Map.value.get(mv200_id)
  if (!server || !server.bare_id) return '-'
  
  const bare_info = bareMap.value.get(server.bare_id)
  return bare_info ? bare_info.name : '-'
}

// 根据ID获取裸金属服务器IP
const getHostIP = (mv200_id: string) => {
  const server = mv200Map.value.get(mv200_id)
  if (!server || !server.bare_id) return '-'
  
  const bare_info = bareMap.value.get(server.bare_id)
  return bare_info ? bare_info.host_ip : '-'
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const [disksResponse, imagesResponse, serversResponse, baresResponse] = await Promise.all([
      systemDisksApi.getAll(),
      imagesApi.getAll(),
      mv200Api.getAll(),
      bareApi.getAll(),
    ])
    
    disks.value = disksResponse
    images.value = imagesResponse
    mv200Servers.value = serversResponse
    bares.value = baresResponse

  } catch (error) {
    ElMessage.error('加载数据失败')
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理，这里可以留空或添加其他逻辑
}

// 下拉菜单命令处理
const handleCommand = (command: string, disk: SystemDisk) => {
  switch (command) {
    case 'edit':
      handleEdit(disk)
      break
    case 'upload':
      handleUploadToImage(disk)
      break
    case 'rebuild':
      handleRebuildFromImage(disk)
      break
    case 'flatten':
      handleFlatten(disk)
      break
    case 'delete':
      handleDelete(disk)
      break
  }
}

// 编辑
const handleEdit = (disk: SystemDisk) => {
  window.location.href = `/system-disks/edit/${disk.id}`
}

// 删除
const handleDelete = async (disk: SystemDisk) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除系统磁盘 ${disk.id}（关联SOC：${disk.mv200_ip}）吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    // 显示表格加载状态
    loading.value = true
    
    // 执行删除操作
    const response = await systemDisksApi.delete(disk.id)
    
    ElMessage.success('删除成功')
    
    // 检查清理状态并提示
    if (response.efi_status === 1 || response.cloudinit_status === 1) {
      let warningMessage = '删除成功，但存在以下相关残留问题：\n'
      
      if (response.efi_status === 1) {
        warningMessage += '• 自动清理EFI启动项失败，需要重启系统完成自动清理\n'
      }
      
      if (response.cloudinit_status === 1) {
        warningMessage += '• cloud-init数据源清理失败\n'
      }
      
      ElMessage.warning({
        message: warningMessage,
        duration: 8000, // 延长显示时间
        showClose: true
      })
    }
    
    // 重新加载数据
    await loadData()
    
  } catch (error) {
    // 用户取消删除
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  } finally {
    loading.value = false
  }
}

// 保存为镜像
const handleUploadToImage = (disk: SystemDisk) => {
  currentDisk.value = disk
  uploadForm.dest_name = ''
  uploadDialogVisible.value = true
}

// 确认保存为镜像
const confirmUpload = async () => {
  if (!currentDisk.value) return
  
  try {
    uploadLoading.value = true
    
    // 调用保存为镜像的API
    await systemDisksApi.uploadToImage(currentDisk.value.id, {
      dest_name: uploadForm.dest_name || undefined,
      dest_pool: uploadForm.dest_pool || undefined,
      description: uploadForm.description || undefined
    })
    
    ElMessage.success('保存为镜像操作已提交，请稍后查看镜像列表')
    uploadDialogVisible.value = false
    
  } catch (error) {
    ElMessage.error('保存为镜像失败')
    console.error('保存为镜像失败:', error)
  } finally {
    uploadLoading.value = false
  }
}

// 重置镜像
const handleRebuildFromImage = (disk: SystemDisk) => {
  currentDisk.value = disk
  rebuildForm.image_id = ''
  rebuildDialogVisible.value = true
}

// 确认重置镜像
const confirmRebuild = async () => {
  if (!currentDisk.value) return
  
  if (!rebuildForm.image_id) {
    ElMessage.warning('请选择镜像')
    return
  }
  
  try {
    rebuildLoading.value = true

    // 调用重置镜像的API - 通过查询参数传递 image_id
    const response = await systemDisksApi.rebuildFromImage(currentDisk.value.id, rebuildForm.image_id)
    
    ElMessage.success('重置镜像操作已提交，系统盘将使用新镜像重建')
    // 检查清理状态并提示
    if (response.efi_status === 1 || response.cloudinit_status === 1) {
      let warningMessage = '刷新成功，但存在以下相关残留问题：\n'
      
      if (response.efi_status === 1) {
        warningMessage += '• 自动刷新EFI启动项失败，需要重启系统完成自动刷新\n'
      }
      
      if (response.cloudinit_status === 1) {
        warningMessage += '• cloud-init数据源刷新失败\n'
      }
      
      ElMessage.warning({
        message: warningMessage,
        duration: 8000, // 延长显示时间
        showClose: true
      })
    }
    rebuildDialogVisible.value = false
    
    // 重新加载数据以更新状态
    await loadData()
    
  } catch (error) {
    ElMessage.error('重置镜像失败')
    console.error('重置镜像失败:', error)
  } finally {
    rebuildLoading.value = false
  }
}

// Flatten操作
const handleFlatten = (disk: SystemDisk) => {
  currentDisk.value = disk
  flattenDialogVisible.value = true
}

// 确认Flatten操作
const confirmFlatten = async () => {
  if (!currentDisk.value) return
  
  try {
    flattenLoading.value = true
    
    // 调用Flatten API
    await systemDisksApi.flatten(currentDisk.value.id)
    
    ElMessage.success('Flatten操作已提交')
    flattenDialogVisible.value = false
    
    // 重新加载数据以更新状态
    await loadData()
    
  } catch (error) {
    ElMessage.error('Flatten操作失败')
    console.error('Flatten操作失败:', error)
  } finally {
    flattenLoading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.warning-message {
  margin-top: 16px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.confirm-message {
  text-align: center;
  margin: 20px 0;
}

.confirm-message p {
  font-size: 16px;
  line-height: 1.5;
}

.confirm-message strong {
  color: #67c23a;
}

/* 名称高亮样式 - 只改变字体颜色 */
.highlight-name {
  color: #67c23a;
  font-weight: 600;
}

/* IP地址高亮样式 - 只改变字体颜色 */
.highlight-ip {
  color: #409eff;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* 已删除镜像样式 - 置灰显示 */
.highlight-deleted {
  color: #c0c4cc;
  font-weight: 500;
  font-style: italic;
}

/* 磁盘大小高亮样式 - 只改变字体颜色 */
.highlight-size {
  color: #e6a23c;
  font-weight: 600;
}

/* Flatten状态高亮 - 只改变字体颜色 */
.highlight-true {
  color: #67c23a;
  font-weight: 600;
}

.highlight-creator {
  color: #13c2c2;
  font-weight: 500;
}

.highlight-false {
  color: #f56c6c;
  font-weight: 600;
}

:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  color: #f56c6c;
  background-color: #fef0f0;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-dropdown-menu__item.is-disabled) {
  color: #c0c4cc;
  cursor: not-allowed;
}

:deep(.el-dropdown-menu__item.is-disabled:hover) {
  background-color: transparent;
}
</style>