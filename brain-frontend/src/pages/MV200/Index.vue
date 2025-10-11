<template>
  <div class="mv200-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>MV200卡管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索ID、名称、SOC IP、裸金属服务器或描述"
              clearable
              style="width: 350px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="$router.push('/mv200/create')">
              录入MV200服务器
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredServers" v-loading="loading">
        <el-table-column prop="id" label="ID" width="200" />
        <el-table-column prop="name" label="名称">
          <template #default="{ row }">
            <span class="highlight-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="SOC IP">
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.ip_address }}</span>
          </template>
        </el-table-column>
        <el-table-column label="裸金属服务器">
          <template #default="{ row }">
            <span class="highlight-name">{{ getBareName(row.bare_id) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="clouddisk_enable" label="支持云盘启动" width="140">
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
            <el-switch
              v-model="row.clouddisk_enable"
              :loading="row.switchLoading"
              @change="(value) => handleSwitchChange(value, row)"
              active-text="是"
              inactive-text="否"
              active-color="#67c23a"
              inactive-color="#f56c6c"
            />
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
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled, MoreFilled, Edit, Delete, Search } from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import type { MVServer, BareMetalServer } from '@/types/api'

const loading = ref(false)
const servers = ref<(MVServer & { switchLoading?: boolean })[]>([])
const bares = ref<BareMetalServer[]>([])
const searchKeyword = ref('')

const loadData = async () => {
  loading.value = true
  try {
    const [baresResponse, serversResponse] = await Promise.all([
      bareApi.getAll(),
      mv200Api.getAll()
    ])
    // 为每个服务器添加switchLoading状态
    servers.value = serversResponse.map(server => ({
      ...server,
      switchLoading: false
    }))
    bares.value = baresResponse
  } catch (error) {
    ElMessage.error('加载MV200服务器列表失败')
  } finally {
    loading.value = false
  }
}

// 计算属性：创建ID到名称的映射
const bareMap = computed(() => {
  const map = new Map<string, BareMetalServer>()
  bares.value.forEach(bare => {
    map.set(bare.id, bare)
  })
  return map
})

// 计算属性：过滤服务器列表
const filteredServers = computed(() => {
  if (!searchKeyword.value) {
    return servers.value
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return servers.value.filter(server => {
    // 搜索ID
    if (server.id.toLowerCase().includes(keyword)) return true
    
    // 搜索MV200名称
    if (server.name.toLowerCase().includes(keyword)) return true
    
    // 搜索SOC IP
    if (server.ip_address.toLowerCase().includes(keyword)) return true
    
    // 搜索裸金属服务器信息
    const bareInfo = getBareName(server.bare_id).toLowerCase()
    if (bareInfo.includes(keyword)) return true
    
    // 搜索描述
    if (server.description && server.description.toLowerCase().includes(keyword)) return true
    
    return false
  })
})

// 根据ID获取裸金属服务器信息
const getBareName = (bareId: string) => {
  const bare = bareMap.value.get(bareId)
  return bare ? `${bare.name} (${bare.host_ip})` : bareId
}

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理，这里可以留空或添加其他逻辑
}

// 处理开关状态变化
const handleSwitchChange = async (value: boolean, server: MVServer & { switchLoading?: boolean }) => {
  if (server.switchLoading) return
  
  server.switchLoading = true
  try {
    await mv200Api.update(server.id, {
      clouddisk_enable: value
    })
    ElMessage.success(`已${value ? '启用' : '禁用'}云盘启动支持`)
  } catch (error) {
    // 更新失败，恢复原来的状态
    server.clouddisk_enable = !value
    ElMessage.error('状态更新失败')
  } finally {
    server.switchLoading = false
  }
}

// 下拉菜单命令处理
const handleCommand = (command: string, server: MVServer) => {
  switch (command) {
    case 'edit':
      handleEdit(server)
      break
    case 'delete':
      handleDelete(server)
      break
  }
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