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
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="ceph_location" label="Ceph位置" />
        <el-table-column prop="mon_host" label="Ceph集群" />
        <el-table-column prop="min_size" label="最小容量(GB)" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)"> 删除 </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
</style>
