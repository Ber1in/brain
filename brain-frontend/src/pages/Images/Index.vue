<template>
  <div class="images-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>镜像管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索ID、镜像名、Ceph位置或描述"
              clearable
              style="width: 350px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="$router.push('/images/create')"> 纳管系统镜像 </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredImages" v-loading="loading">
        <el-table-column prop="id" label="ID" width="200" />
        <el-table-column prop="name" label="名称">
          <template #default="{ row }">
            <span class="highlight-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ceph_location" label="Ceph位置">
          <template #default="{ row }">
            <span class="highlight-path">{{ row.ceph_location }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="mon_host" label="Ceph集群">
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.mon_host }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="min_size" label="最小容量(GB)">
          <template #default="{ row }">
            <span class="highlight-size">{{ row.min_size }} GB</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
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
                  <el-dropdown-item 
                    command="delete" 
                    divided 
                    class="danger-item"
                    :disabled="!row.canDelete"
                  >
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                    <el-tooltip
                      v-if="!row.canDelete"
                      effect="dark"
                      content="仍有未flatten的云系统盘依赖此镜像，暂不允许删除"
                      placement="left"
                    >
                      <el-icon style="margin-left: 4px;">
                        <InfoFilled />
                      </el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MoreFilled, Edit, Delete, Search, InfoFilled } from '@element-plus/icons-vue'
import { imagesApi } from '@/api/images'
import { systemDisksApi } from '@/api/system-disks'
import type { Image, SystemDisk } from '@/types/api'

const loading = ref(false)
const images = ref<Image[]>([])
const systemDisks = ref<SystemDisk[]>([])
const searchKeyword = ref('')

// 计算属性：过滤镜像列表
const filteredImages = computed(() => {
  if (!searchKeyword.value) {
    return images.value
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return images.value.filter(image => {
    // 搜索ID
    if (image.id.toLowerCase().includes(keyword)) return true
    
    // 搜索镜像名
    if (image.name.toLowerCase().includes(keyword)) return true
    
    // 搜索Ceph位置
    if (image.ceph_location.toLowerCase().includes(keyword)) return true
    
    // 搜索描述
    if (image.description && image.description.toLowerCase().includes(keyword)) return true
    
    return false
  })
})

// 计算属性：获取依赖当前镜像的未flatten系统盘
const getDependentDisks = (imageId: string) => {
  return systemDisks.value.filter(disk => 
    disk.image_id === imageId && !disk.flatten
  )
}

// 检查镜像是否可以被删除
const checkImageDeletable = (imageId: string): boolean => {
  const dependentDisks = getDependentDisks(imageId)
  return dependentDisks.length === 0
}

const loadData = async () => {
  loading.value = true
  try {
    // 并行加载镜像和系统盘数据
    const [imagesResponse, disksResponse] = await Promise.all([
      imagesApi.getAll(),
      systemDisksApi.getAll()
    ])
    
    images.value = imagesResponse
    systemDisks.value = disksResponse
    
    // 为每个镜像设置删除状态
    images.value = images.value.map(image => ({
      ...image,
      canDelete: checkImageDeletable(image.id)
    }))
    
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
const handleCommand = (command: string, image: Image & { canDelete?: boolean }) => {
  switch (command) {
    case 'edit':
      handleEdit(image)
      break
    case 'delete':
      handleDelete(image)
      break
  }
}

const handleEdit = (image: Image) => {
  // 跳转到编辑页面
  window.location.href = `/images/edit/${image.id}`
}

const handleDelete = async (image: Image & { canDelete?: boolean }) => {
  // 再次检查是否可以删除（防止状态变化）
  if (!image.canDelete) {
    const dependentDisks = getDependentDisks(image.id)
    ElMessage.warning(`仍有 ${dependentDisks.length} 个未flatten的云系统盘依赖此镜像，暂不允许删除`)
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除镜像 "${image.name}" 吗？此操作不可撤销！`,
      '确认删除', 
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }
    )

    await imagesApi.delete(image.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    // 用户取消删除
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
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

/* 路径高亮样式 - 只改变字体颜色 */
.highlight-path {
  color: #e6a23c;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* 容量高亮样式 - 只改变字体颜色 */
.highlight-size {
  color: #e6a23c;
  font-weight: 600;
}

:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  color: #f56c6c;
  background-color: #fef0f0;
}

:deep(.danger-item.is-disabled) {
  color: #c0c4cc !important;
  background-color: #f5f7fa !important;
  cursor: not-allowed !important;
}

:deep(.danger-item.is-disabled:hover) {
  color: #c0c4cc !important;
  background-color: #f5f7fa !important;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dropdown-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

/* 确保tooltip内容正确显示 */
:deep(.el-tooltip__trigger) {
  display: block;
  width: 100%;
}
</style>