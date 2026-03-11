<template>
  <div class="images-page">
    <GenericTable
      :title="tableTitle"
      :data="images"
      :columns="columns"
      :loading="loading"
      :show-search="true"
      search-placeholder="搜索ID、镜像名、Ceph位置或描述"
      :search-style="{ width: '350px', marginRight: '16px' }"
      :show-actions="true"
      :show-delete="false"
      create-route="/images/create"
      create-button-text="纳管系统镜像"
      :row-key="'id'"
      :on-delete="handleDelete"
      :filter-method="filterMethod"
    >
      <!-- 自定义列插槽 -->
      <template #column-name="{ row }">
        <span class="highlight-name">{{ row.name }}</span>
      </template>
      
      <template #column-ceph-location="{ row }">
        <span class="highlight-path">{{ row.ceph_location }}</span>
      </template>
      
      <template #column-mon-host="{ row }">
        <span class="highlight-ip">{{ row.mon_host }}</span>
      </template>
      
      <template #column-min-size="{ row }">
        <span class="highlight-size">{{ row.min_size }} GB</span>
      </template>
      
      <!-- 自定义操作列插槽 -->
      <template #actions-column="{ row }">
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
                <el-tooltip
                  v-if="!row.canDelete"
                  effect="dark"
                  :content="`仍有 ${getDependentDisks(row.id).length} 个未flatten的云系统盘依赖此镜像，暂不允许删除`"
                  placement="left"
                >
                  <div class="dropdown-item-content">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </div>
                </el-tooltip>
                <div v-else class="dropdown-item-content">
                  <el-icon><Delete /></elicon>
                    <span>删除</span>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
    </GenericTable>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MoreFilled, Edit, Delete } from '@element-plus/icons-vue'
import GenericTable from '@/components/table/GenericTable.vue'
import { imagesApi } from '@/api/images'
import { systemDisksApi } from '@/api/system-disks'
import type { Image, SystemDisk } from '@/types/api'

const loading = ref(false)
const images = ref<Image[]>([])
const systemDisks = ref<SystemDisk[]>([])

const tableTitle = '镜像管理'

// 表格列配置
const columns = [
  {
    prop: 'id',
    label: 'ID',
    width: '200',
  },
  {
    prop: 'name',
    label: '名称',
    slot: 'name',
  },
  {
    prop: 'ceph_location',
    label: 'Ceph位置',
    slot: 'ceph-location',
  },
  {
    prop: 'mon_host',
    label: 'Ceph集群',
    slot: 'mon-host',
  },
  {
    prop: 'min_size',
    label: '最小容量(GB)',
    slot: 'min-size',
  },
  {
    prop: 'description',
    label: '描述',
    showOverflowTooltip: true,
  },
]

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

// 自定义过滤方法
const filterMethod = (value: string, row: any, column: any) => {
  if (!value) return true
  
  const keyword = value.toLowerCase()
  const columnProp = column.property
  
  // 根据列属性进行过滤
  if (columnProp === 'id') {
    return row.id.toLowerCase().includes(keyword)
  } else if (columnProp === 'name') {
    return row.name.toLowerCase().includes(keyword)
  } else if (columnProp === 'ceph_location') {
    return row.ceph_location.toLowerCase().includes(keyword)
  } else if (columnProp === 'mon_host') {
    return row.mon_host.toLowerCase().includes(keyword)
  } else if (columnProp === 'description') {
    return row.description && row.description.toLowerCase().includes(keyword)
  }
  
  // 全局搜索（所有字段）
  return (
    row.id.toLowerCase().includes(keyword) ||
    row.name.toLowerCase().includes(keyword) ||
    row.ceph_location.toLowerCase().includes(keyword) ||
    (row.description && row.description.toLowerCase().includes(keyword))
  )
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
    return false
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
    await loadData()
    return true
  } catch (error) {
    // 用户取消删除
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
    return false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.images-page {
  height: 100%;
}

/* 名称高亮样式 - 只改变字体颜色 */
:deep(.highlight-name) {
  color: #67c23a;
  font-weight: 600;
}

/* IP地址高亮样式 - 只改变字体颜色 */
:deep(.highlight-ip) {
  color: #409eff;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* 路径高亮样式 - 只改变字体颜色 */
:deep(.highlight-path) {
  color: #e6a23c;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* 容量高亮样式 - 只改变字体颜色 */
:deep(.highlight-size) {
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
</style>