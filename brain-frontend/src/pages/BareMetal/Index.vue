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
        <el-table-column prop="name" label="名称">
          <template #default="{ row }">
            <span class="highlight-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="host_ip" label="管理IP">
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.host_ip }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="gateway" label="网关">
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.gateway }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="mac" label="管理口MAC">
          <template #default="{ row }">
            <span class="highlight-mac">{{ row.mac }}</span>
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
                  <el-dropdown-item command="boot" divided>
                    <el-icon><Setting /></el-icon>
                    <span>修改启动项</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="warmReset">
                    <el-icon><RefreshRight /></el-icon>
                    <span>重启</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="coldReset">
                    <el-icon><RefreshLeft /></el-icon>
                    <span>冷重启</span>
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

    <!-- 启动项认证对话框 -->
    <el-dialog
      v-model="bootAuthDialogVisible"
      title="修改启动项 - 身份认证"
      width="400px"
    >
      <div class="dialog-tip">
        <el-alert
          title="请确保服务器在线且网络连接正常"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>
      <el-form :model="bootAuthForm" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input
            v-model="bootAuthForm.user"
            placeholder="请输入服务器用户名"
            clearable
          />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input
            v-model="bootAuthForm.pwd"
            type="password"
            placeholder="请输入服务器密码"
            clearable
            show-password
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="bootAuthDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleBootAuth" 
          :loading="bootAuthLoading"
          :disabled="!bootAuthForm.user || !bootAuthForm.pwd"
        >
          查询启动项
        </el-button>
      </template>
    </el-dialog>

    <!-- 启动项设置对话框 -->
    <el-dialog
      v-model="bootSetDialogVisible"
      :title="`修改启动项 - ${currentServer?.name}`"
      width="500px"
    >
      <el-form label-width="100px">
        <el-form-item label="选择启动项" required>
          <el-select
            v-model="selectedBootId"
            placeholder="请选择启动项"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="(name, id) in bootEntries"
              :key="id"
              :label="getBootOptionLabel(name, id)"
              :value="id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="bootSetDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleSetBoot" 
          :loading="setBootLoading"
          :disabled="!selectedBootId"
        >
          设置启动项
        </el-button>
      </template>
    </el-dialog>

    <!-- 重启确认对话框 -->
    <el-dialog
      v-model="resetDialogVisible"
      :title="resetDialogTitle"
      width="400px"
    >
      <div class="dialog-tip">
        <el-alert
          :title="resetType === 'cold' ? '冷重启将完全断电后重新启动服务器' : '热重启将保持通电状态重新启动服务器'"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>
      <div class="confirm-message">
        <p>确定要对服务器 <strong>"{{ currentServer?.name }}"</strong> 执行{{ resetType === 'cold' ? '冷重启' : '热重启' }}吗？</p>
      </div>
      
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmReset" 
          :loading="resetLoading"
        >
          确认重启
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MoreFilled, Edit, Delete, Setting, RefreshLeft, RefreshRight } from '@element-plus/icons-vue'
import { bareApi } from '@/api/bare'
import type { BareMetalServer } from '@/types/api'

const loading = ref(false)
const servers = ref<BareMetalServer[]>([])

// 启动项相关
const bootAuthDialogVisible = ref(false)
const bootSetDialogVisible = ref(false)
const bootAuthLoading = ref(false)
const setBootLoading = ref(false)
const currentServer = ref<BareMetalServer | null>(null)
const bootEntries = ref<Record<string, string>>({})
const currentBootId = ref('')
const nextBootId = ref<string | null>('')
const selectedBootId = ref('')
const bootAuthForm = reactive({
  user: '',
  pwd: ''
})

// 重启相关
const resetDialogVisible = ref(false)
const resetLoading = ref(false)
const resetType = ref<'cold' | 'warm'>('cold')
const resetDialogTitle = ref('')

// 计算当前启动项名称
const currentBootName = computed(() => {
  if (currentBootId.value && bootEntries.value[currentBootId.value]) {
    return bootEntries.value[currentBootId.value]
  }
  return currentBootId.value || '未知'
})

// 计算下一次启动项名称
const nextBootName = computed(() => {
  if (nextBootId.value && bootEntries.value[nextBootId.value]) {
    return bootEntries.value[nextBootId.value]
  }
  return nextBootId.value || ''
})

// 生成启动项下拉框选项标签
const getBootOptionLabel = (name: string, id: string) => {
  let label = name
  if (id === currentBootId.value) {
    label += ' (当前)'
  }
  if (id === nextBootId.value) {
    label += ' (下一次)'
  }
  return label
}

// 加载数据
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

// 下拉菜单命令处理
const handleCommand = (command: string, server: BareMetalServer) => {
  switch (command) {
    case 'edit':
      handleEdit(server)
      break
    case 'boot':
      handleBootConfig(server)
      break
    case 'coldReset':
      handleColdReset(server)
      break
    case 'warmReset':
      handleWarmReset(server)
      break
    case 'delete':
      handleDelete(server)
      break
  }
}

// 编辑
const handleEdit = (server: BareMetalServer) => {
  window.location.href = `/bare/edit/${server.id}`
}

// 删除
const handleDelete = async (server: BareMetalServer) => {
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

// 修改启动项 - 第一步：认证
const handleBootConfig = (server: BareMetalServer) => {
  currentServer.value = server
  bootAuthForm.user = ''
  bootAuthForm.pwd = ''
  bootEntries.value = {}
  currentBootId.value = ''
  nextBootId.value = ''
  selectedBootId.value = ''
  bootAuthDialogVisible.value = true
}

// 启动项认证
const handleBootAuth = async () => {
  if (!currentServer.value) return
  
  try {
    bootAuthLoading.value = true
    const response = await bareApi.getBootEntries(
      currentServer.value.id, 
      bootAuthForm.user, 
      bootAuthForm.pwd
    )
    
    bootEntries.value = response.entries
    currentBootId.value = response.current
    nextBootId.value = response.next || null
    selectedBootId.value = '' // 清空选择
    
    // 关闭认证对话框，打开设置对话框
    bootAuthDialogVisible.value = false
    bootSetDialogVisible.value = true
    
    ElMessage.success('启动项查询成功')
  } catch (error) {
    ElMessage.error('查询启动项失败，请检查用户名和密码')
    console.error('查询启动项失败:', error)
  } finally {
    bootAuthLoading.value = false
  }
}

// 设置启动项
const handleSetBoot = async () => {
  if (!currentServer.value || !selectedBootId.value) return
  
  try {
    setBootLoading.value = true
    await bareApi.setBootEntry(
      currentServer.value.id,
      selectedBootId.value,
      bootAuthForm.user,
      bootAuthForm.pwd
    )
    
    ElMessage.success('启动项设置成功')
    bootSetDialogVisible.value = false
    
    // 更新下一次启动项
    nextBootId.value = selectedBootId.value
    
  } catch (error) {
    ElMessage.error('设置启动项失败')
    console.error('设置启动项失败:', error)
  } finally {
    setBootLoading.value = false
  }
}

// 冷重启
const handleColdReset = (server: BareMetalServer) => {
  currentServer.value = server
  resetType.value = 'cold'
  resetDialogTitle.value = `冷重启 - ${server.name}`
  resetDialogVisible.value = true
}

// 热重启
const handleWarmReset = (server: BareMetalServer) => {
  currentServer.value = server
  resetType.value = 'warm'
  resetDialogTitle.value = `热重启 - ${server.name}`
  resetDialogVisible.value = true
}

// 确认重启
const confirmReset = async () => {
  if (!currentServer.value) return
  
  try {
    resetLoading.value = true
    
    if (resetType.value === 'cold') {
      await bareApi.powerCycle(currentServer.value.id)
      ElMessage.success('冷重启命令已发送')
    } else {
      await bareApi.powerReset(currentServer.value.id)
      ElMessage.success('热重启命令已发送')
    }
    
    resetDialogVisible.value = false
    
  } catch (error) {
    ElMessage.error('重启失败')
    console.error('重启失败:', error)
  } finally {
    resetLoading.value = false
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

.dialog-tip {
  margin-bottom: 20px;
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

/* MAC地址高亮样式 - 只改变字体颜色 */
.highlight-mac {
  color: #e6a23c;
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