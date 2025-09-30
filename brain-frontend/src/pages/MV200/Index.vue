<template>
  <div class="mv200-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>MV200卡管理</span>
          <el-button type="primary" @click="$router.push('/mv200/create')">
            录入MV200服务器
          </el-button>
        </div>
      </template>

      <el-table :data="servers" v-loading="loading">
        <el-table-column prop="id" label="ID" width="200" />
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="ip_address" label="SOC IP" />
        <el-table-column label="裸金属服务器">
          <template #default="{ row }">
            {{ getBareName(row.bare_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="clouddisk_enable" label="支持云盘启动">
          <template #header>
            <span>支持云盘启动</span>
            <el-tooltip 
              effect="dark" 
              content="当支持云盘启动时，在主机启动阶段会一直等待dpu ready，直到准备好云系统盘"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <el-tag :type="row.clouddisk_enable ? 'success' : 'danger'">
              {{ row.clouddisk_enable ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
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
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import type { MVServer, BareMetalServer } from '@/types/api'

const loading = ref(false)
const servers = ref<MVServer[]>([])
const bares = ref<BareMetalServer[]>([])

const loadData = async () => {
  loading.value = true
  try {
    const [baresResponse, serversResponse] = await Promise.all([
      bareApi.getAll(),
      mv200Api.getAll()
    ])
    servers.value = serversResponse
    bares.value = baresResponse
  } catch (error) {
    ElMessage.error('加载MV200服务器列表失败')
  } finally {
    loading.value = false
  }
}

// 计算属性：创建ID到名称的映射
const bareMap = computed(() => {
  const map = new Map<string, string>()
  bares.value.forEach(bare => {
    map.set(bare.id, bare)
  })
  return map
})

// 根据ID获取镜像名称
const getBareName = (bareId: string) => {
  const bare = bareMap.value.get(bareId)
  return bare ? `${bare.name} (${bare.host_ip})` : bareId
}

const handleEdit = (server: MVServer) => {
  window.location.href = `/mv200/edit/${server.id}`
}

const handleDelete = async (server: MVServer) => {
  try {
    await ElMessageBox.confirm(`确定要删除MV200服务器 "${server.name}" 吗？`, '确认删除', {
      type: 'warning',
    })

    await mv200Api.delete(server.id)
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
