<template>
  <div class="images-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>镜像管理</span>
          <el-button type="primary" @click="$router.push('/images/create')"> 录入镜像 </el-button>
        </div>
      </template>

      <el-table :data="images" v-loading="loading">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MoreFilled, Edit, Delete } from '@element-plus/icons-vue'
import { imagesApi } from '@/api/images'
import type { Image } from '@/types/api'

const loading = ref(false)
const images = ref<Image[]>([])

const loadData = async () => {
  loading.value = true
  try {
    images.value = await imagesApi.getAll()
  } catch (error) {
    ElMessage.error('加载镜像列表失败')
  } finally {
    loading.value = false
  }
}

// 下拉菜单命令处理
const handleCommand = (command: string, image: Image) => {
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

const handleDelete = async (image: Image) => {
  try {
    await ElMessageBox.confirm(`确定要删除镜像 "${image.name}" 吗？`, '确认删除', {
      type: 'warning',
    })

    await imagesApi.delete(image.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    // 用户取消删除
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

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>