<template>
  <div class="bare-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>裸金属服务器管理</span>
          <el-button type="primary" @click="$router.push('/bare/create')">
            录入裸金属服务器
          </el-button>
        </div>
      </template>

      <el-table :data="servers" v-loading="loading">
        <el-table-column prop="id" label="ID" width="200" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="host_ip" label="管理IP" />
        <el-table-column prop="gateway" label="网关" />
        <el-table-column prop="mac" label="管理口MAC" />
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
import { QuestionFilled } from '@element-plus/icons-vue'
import { bareApi } from '@/api/bare'
import type { MVServer } from '@/types/api'

const loading = ref(false)
const servers = ref<MVServer[]>([])

const loadData = async () => {
  loading.value = true
  try {
    servers.value = await bareApi.getAll()
  } catch (error) {
    ElMessage.error('加载裸金属服务器列表失败')
  } finally {
    loading.value = false
  }
}

const handleEdit = (server: MVServer) => {
  window.location.href = `/bare/edit/${server.id}`
}

const handleDelete = async (server: MVServer) => {
  try {
    await ElMessageBox.confirm(`确定要删除裸金属服务器 "${server.name}" 吗？`, '确认删除', {
      type: 'warning',
    })

    await bareApi.delete(server.id)
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
