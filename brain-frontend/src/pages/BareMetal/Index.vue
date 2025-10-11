<template>
  <div class="bare-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>裸金属服务器管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索ID、名称、管理IP、MAC或描述"
              clearable
              style="width: 350px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="$router.push('/bare/create')">
              录入裸金属服务器
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
      title="修改启动项 - 操作系统身份认证"
      width="400px"
    >
      <div class="dialog-tip">
        <el-alert
          title="请确保服务器在线且网络连接正常，需要操作系统管理员权限"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>
      <el-form :model="bootAuthForm" label-width="100px">
        <el-form-item label="OS用户名" required>
          <el-input
            v-model="bootAuthForm.user"
            placeholder="请输入服务器操作系统用户名"
            clearable
          />
        </el-form-item>
        <el-form-item label="OS密码" required>
          <el-input
            v-model="bootAuthForm.pwd"
            type="password"
            placeholder="请输入服务器操作系统密码"
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
          :loading="bootAuthLoading || credentialCheckLoading"
          :disabled="!bootAuthForm.user || !bootAuthForm.pwd"
        >
          {{ credentialCheckLoading ? '验证中...' : '查询启动项' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 启动项设置对话框 -->
    <el-dialog
      v-model="bootSetDialogVisible"
      :title="`修改启动项 - ${currentServer?.name}`"
      width="500px"
    >
      <div class="dialog-tip" v-if="currentServer?.os_user">
        <el-alert
          title="将用缓存的操作系统凭据设置启动项"
          type="info"
          :closable="false"
          show-icon
        />
      </div>
      <el-form label-width="100px">
        <el-form-item label="下一次启动" required>
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
        
        <!-- 新增：设置为默认启动项选项 -->
        <el-form-item>
          <el-checkbox v-model="setDefaultBoot">
            同时设置为默认启动项
          </el-checkbox>
          <el-tooltip 
              effect="dark" 
              content="勾选后会将此启动项调整到启动顺序的最前面"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
        </el-form-item>
        
        <el-form-item label="当前启动项" v-if="currentBootId">
          <div class="boot-info">
            <span>{{ currentBootName }}</span>
            <el-tag size="small" type="success">当前</el-tag>
          </div>
        </el-form-item>
        <el-form-item label="下一次启动" v-if="nextBootId">
          <div class="boot-info">
            <span>{{ nextBootName }}</span>
            <el-tag size="small" type="warning">下一次</el-tag>
          </div>
        </el-form-item>
        <el-form-item label="默认启动" v-if="defaultBootId">
          <div class="boot-info">
            <span>{{ defaultBootName }}</span>
            <el-tag size="small" type="primary">默认</el-tag>
          </div>
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
import { MoreFilled, Edit, Delete, Setting, RefreshLeft, RefreshRight, Search, QuestionFilled } from '@element-plus/icons-vue'
import { bareApi } from '@/api/bare'
import type { BareMetalServer } from '@/types/api'

const loading = ref(false)
const servers = ref<BareMetalServer[]>([])
const searchKeyword = ref('')

// 启动项相关
const bootAuthDialogVisible = ref(false)
const bootSetDialogVisible = ref(false)
const bootAuthLoading = ref(false)
const setBootLoading = ref(false)
const credentialCheckLoading = ref(false)
const currentServer = ref<BareMetalServer | null>(null)
const bootEntries = ref<Record<string, string>>({})
const currentBootId = ref('')
const defaultBootId = ref<string | null>('') 
const nextBootId = ref<string | null>('')
const selectedBootId = ref('')
const setDefaultBoot = ref(false) // 新增：是否设置为默认启动项
const bootAuthForm = reactive({
  user: '',
  pwd: ''
})

// 重启相关
const resetDialogVisible = ref(false)
const resetLoading = ref(false)
const resetType = ref<'cold' | 'warm'>('cold')
const resetDialogTitle = ref('')

// 计算属性：过滤服务器列表
const filteredServers = computed(() => {
  if (!searchKeyword.value) {
    return servers.value
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return servers.value.filter(server => {
    // 搜索ID
    if (server.id.toLowerCase().includes(keyword)) return true
    
    // 搜索名称
    if (server.name.toLowerCase().includes(keyword)) return true
    
    // 搜索管理IP
    if (server.host_ip.toLowerCase().includes(keyword)) return true
    
    // 搜索MAC地址
    if (server.mac.toLowerCase().includes(keyword)) return true
    
    // 搜索描述
    if (server.description && server.description.toLowerCase().includes(keyword)) return true
    
    return false
  })
})

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

// 计算默认启动项名称
const defaultBootName = computed(() => {
  if (defaultBootId.value && bootEntries.value[defaultBootId.value]) {
    return bootEntries.value[defaultBootId.value]
  }
  return defaultBootId.value || '未知'
})

// 生成启动项下拉框选项标签
const getBootOptionLabel = (name: string, id: string) => {
  let label = name
  if (id === currentBootId.value) {
    label += ' (当前)'
  }
  if (id === defaultBootId.value) {
    label += ' (默认)'
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

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理，这里可以留空或添加其他逻辑
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
const handleBootConfig = async (server: BareMetalServer) => {
  currentServer.value = server
  bootEntries.value = {}
  currentBootId.value = ''
  defaultBootId.value = ''
  nextBootId.value = ''
  selectedBootId.value = ''
  setDefaultBoot.value = false // 重置勾选状态
  // 首先尝试使用保存的凭据
  if (server.os_user && server.os_password) {
    try {
      credentialCheckLoading.value = true
      ElMessage.info('正在校验操作系统凭据...')
      
      // 验证保存的凭据是否仍然有效
      const verifyResult = await bareApi.verifyCredentials(server.id, true)
      
      if (verifyResult.valid) {
        // 凭据有效，直接获取启动项
        await getBootEntriesWithSavedCredentials()
        return
      } else {
        ElMessage.warning('缓存的凭据已失效，请重新输入服务器账号密码')
      }
    } catch (error) {
      ElMessage.warning('缓存的凭据验证失败，请重新输入服务器账号密码')
    } finally {
      credentialCheckLoading.value = false
    }
  }
  
  // 没有保存的凭据或凭据无效，显示认证对话框
  bootAuthForm.user = ''
  bootAuthForm.pwd = ''
  bootAuthDialogVisible.value = true
}

// 使用保存的凭据获取启动项
const getBootEntriesWithSavedCredentials = async () => {
  if (!currentServer.value) return
  
  try {
    bootAuthLoading.value = true
    const response = await bareApi.getBootEntries(currentServer.value.id, true)
    
    bootEntries.value = response.entries
    currentBootId.value = response.current
    defaultBootId.value = response.default || null
    nextBootId.value = response.next || null
    selectedBootId.value = ''
    
    // 直接打开设置对话框，不显示认证对话框
    bootSetDialogVisible.value = true
    bootAuthDialogVisible.value = false
    
    ElMessage.success('启动项查询成功')
  } catch (error) {
    ElMessage.error('使用缓存的凭据查询启动项失败')
    console.error('查询启动项失败:', error)
    // 失败时显示认证对话框
    bootAuthDialogVisible.value = true
  } finally {
    bootAuthLoading.value = false
  }
}

// 启动项认证（输入新凭据的情况）
const handleBootAuth = async () => {
  if (!currentServer.value) return
  
  try {
    bootAuthLoading.value = true
    const response = await bareApi.getBootEntries(
      currentServer.value.id, 
      false,
      bootAuthForm.user, 
      bootAuthForm.pwd
    )
    
    bootEntries.value = response.entries
    currentBootId.value = response.current
    defaultBootId.value = response.default || null
    nextBootId.value = response.next || null
    selectedBootId.value = ''
    
    // 认证成功，保存凭据到服务器
    try {
      await bareApi.updateServerCredentials(currentServer.value.id, {
        user: bootAuthForm.user,
        pwd: bootAuthForm.pwd
      })
      
      // 更新本地数据
      const serverIndex = servers.value.findIndex(s => s.id === currentServer.value!.id)
      if (serverIndex !== -1) {
        servers.value[serverIndex].os_user = bootAuthForm.user
        servers.value[serverIndex].os_password = bootAuthForm.pwd
      }
      
      ElMessage.success('操作系统凭据已保存')
    } catch (saveError) {
      console.warn('保存凭据失败:', saveError)
      // 这里不显示错误消息，因为主要功能（获取启动项）已经成功
    }
    
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

// 修改设置启动项逻辑，优先使用保存的凭据
const handleSetBoot = async () => {
  if (!currentServer.value || !selectedBootId.value) return
  
  try {
    setBootLoading.value = true
    
    // 如果有保存的凭据，使用保存的凭据，否则使用当前输入的凭据
    const hasSavedCredentials = !!(currentServer.value.os_user && currentServer.value.os_password)
    
    if (hasSavedCredentials) {
      // 使用保存的凭据
      await bareApi.setBootEntry(
        currentServer.value.id,
        selectedBootId.value,
        true, // use_saved = true
        setDefaultBoot.value // 新增参数
      )
    } else {
      // 使用当前输入的凭据
      await bareApi.setBootEntry(
        currentServer.value.id,
        selectedBootId.value,
        false, // use_saved = false
        setDefaultBoot.value, // 新增参数
        bootAuthForm.user,
        bootAuthForm.pwd
      )
    }
    
    ElMessage.success(`启动项设置成功${setDefaultBoot.value ? '，并已设置为默认启动项' : ''}`)
    bootSetDialogVisible.value = false

    if (setDefaultBoot.value) {
      defaultBootId.value = selectedBootId.value
    }
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

.header-actions {
  display: flex;
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

/* 新增样式 */
.option-tip {
  margin-top: 8px;
  color: #909399;
}

.option-tip small {
  font-size: 12px;
}

.boot-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.boot-info .el-tag {
  margin-left: 8px;
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