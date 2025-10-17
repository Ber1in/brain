<template>
  <div class="xsc-interface-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>XSC网口管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索ID、SOC、IP地址、网关、MTU、VLAN或描述"
              clearable
              style="width: 400px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="$router.push('/xsc-interface/create')">
              创建XSC网口
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredInterfaces" v-loading="loading">
        <el-table-column prop="id" label="ID" width="200" />
        <el-table-column label="MV200">
          <template #default="{ row }">
            <div class="mv200-info">
              <div class="mv200-name">{{ getMv200Name(row.mv200_id) }}</div>
              <div class="dns-ip">{{ getMv200Ip(row.mv200_id) }}</div>
            </div>
          </template>
        </el-table-column>
        <!-- 新增网口名列 -->
        <el-table-column label="网口名" width="120">
          <template #default="{ row }">
            <span :class="getInterfaceNameClass(row.ifname)">
              {{ getInterfaceName(row.ifname) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址">
          <template #default="{ row }">
            <span class="highlight-ip">{{ getIpOnly(row.ip) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="gateway" label="网关">
          <template #default="{ row }">
            <span class="highlight-gateway">{{ row.gateway }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="vlan_tag" label="VLAN ID" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.vlan_tag" type="info">{{ row.vlan_tag }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="mac" label="MAC地址" width="150">
          <template #default="{ row }">
            <span v-if="row.mac" class="mac-address">{{ row.mac }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="mtu" label="MTU" width="80">
          <template #default="{ row }">
            {{ row.mtu || 1500 }}
          </template>
        </el-table-column>
        <el-table-column prop="dns" label="DNS服务器" width="180">
          <template #default="{ row }">
            <div v-if="row.dns && row.dns.length > 0" class="dns-list">
              <div v-for="(dns, index) in row.dns" :key="index" class="dns-item">
                <span class="dns-ip">{{ dns }}</span>
              </div>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button 
                type="primary" 
                link
                :loading="row.deleting"
                :disabled="row.deleting"
              >
                <el-icon v-if="!row.deleting" :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">
                    <div class="dropdown-item-content">
                      <el-icon><Edit /></el-icon>
                      <span>编辑</span>
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item 
                    command="delete" 
                    divided 
                    class="danger-item"
                    :disabled="row.deleting"
                  >
                    <div class="dropdown-item-content">
                      <el-icon v-if="!row.deleting"><Delete /></el-icon>
                      <el-icon v-else class="loading-icon"><Loading /></el-icon>
                      <span>{{ row.deleting ? '删除中...' : '删除' }}</span>
                    </div>
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MoreFilled, Edit, Delete, Search, Loading } from '@element-plus/icons-vue'
import { networkApi } from '@/api/network'
import { mv200Api } from '@/api/mv200'
import type { InterfaceInfo, MVServer } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const interfaces = ref<(InterfaceInfo & { deleting?: boolean; ifname?: string })[]>([])
const mv200Servers = ref<MVServer[]>([])
const searchKeyword = ref('')

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const [interfacesResponse, mv200Response] = await Promise.all([
      networkApi.getAll(),
      mv200Api.getAll()
    ])
    
    // 为每个接口获取详细信息以获取ifname
    const interfacesWithDetails = await Promise.all(
      interfacesResponse.map(async (intf) => {
        try {
          // 调用getById获取详细信息，其中可能包含ifname
          const detail = await networkApi.getById(intf.id, intf.mv200_id)
          return {
            ...intf,
            ifname: detail.ifname, // 从详细接口信息中获取ifname
            deleting: false
          }
        } catch (error) {
          // 如果获取详细信息失败，仍然返回基本数据
          console.warn(`Failed to get details for interface ${intf.id}:`, error)
          return {
            ...intf,
            ifname: undefined,
            deleting: false
          }
        }
      })
    )
    
    interfaces.value = interfacesWithDetails
    mv200Servers.value = mv200Response
  } catch (error) {
    ElMessage.error('加载XSC网口列表失败')
  } finally {
    loading.value = false
  }
}

// 计算属性：创建MV200 ID到名称的映射
const mv200Map = computed(() => {
  const map = new Map<string, MVServer>()
  mv200Servers.value.forEach(server => {
    map.set(server.id, server)
  })
  return map
})

// 计算属性：过滤网口列表
const filteredInterfaces = computed(() => {
  if (!searchKeyword.value) {
    return interfaces.value
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return interfaces.value.filter(intf => {
    // 搜索ID
    if (intf.id.toLowerCase().includes(keyword)) return true
    
    // 搜索IP地址
    if (intf.ip.toLowerCase().includes(keyword)) return true
    
    // 搜索网关
    if (intf.gateway.toLowerCase().includes(keyword)) return true
    
    // 搜索VLAN
    if (intf.vlan_tag.toString().includes(keyword)) return true
    
    // 搜索MTU
    if (intf.mtu?.toString().includes(keyword)) return true
    
    // 搜索描述
    if (intf.description && intf.description.toLowerCase().includes(keyword)) return true
    
    // 搜索DNS服务器
    if (intf.dns && intf.dns.some(dns => dns.toLowerCase().includes(keyword))) return true
    
    // 搜索MV200服务器信息
    const mv200Name = getMv200Name(intf.mv200_id).toLowerCase()
    const mv200Ip = getMv200Ip(intf.mv200_id).toLowerCase()
    if (mv200Name.includes(keyword) || mv200Ip.includes(keyword)) return true
    
    return false
  })
})

// 根据ID获取MV200服务器名称
const getMv200Name = (mv200Id: string) => {
  const server = mv200Map.value.get(mv200Id)
  return server ? server.name : mv200Id
}

// 根据ID获取MV200服务器IP
const getMv200Ip = (mv200Id: string) => {
  const server = mv200Map.value.get(mv200Id)
  return server ? server.ip_address : '-'
}

// 获取网口名显示
const getInterfaceName = (ifname?: string) => {
  return ifname || '未知'
}

// 获取网口名样式类
const getInterfaceNameClass = (ifname?: string) => {
  return ifname ? 'highlight-ifname' : 'highlight-unknown'
}

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理
}

const getIpOnly = (ipWithMask: string) => {
  if (!ipWithMask) return '-'
  // 分割IP和掩码，返回IP部分
  const [ip] = ipWithMask.split('/')
  return ip || '-'
}

// 下拉菜单命令处理
const handleCommand = (command: string, intf: InterfaceInfo & { deleting?: boolean }) => {
  switch (command) {
    case 'edit':
      handleEdit(intf)
      break
    case 'delete':
      handleDelete(intf)
      break
  }
}

const handleEdit = (intf: InterfaceInfo) => {
  router.push(`/xsc-interface/edit/${intf.id}`)
}

const handleDelete = async (intf: InterfaceInfo & { deleting?: boolean }) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除XSC网口 "${intf.description || intf.ip}" 吗？`, 
      '确认删除', 
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger'
      }
    )

    // 设置删除状态
    intf.deleting = true
    
    await networkApi.delete(intf.id, intf.mv200_id)
    ElMessage.success('删除成功')
    await loadData() // 重新加载数据
  } catch (error) {
    // 用户取消删除或删除失败
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请重试')
    }
    // 重置删除状态
    intf.deleting = false
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

/* MV200信息样式 */
.mv200-info {
  display: flex;
  flex-direction: column;
}

.mv200-name {
  color: #67c23a;
  font-weight: 600;
  margin-bottom: 2px;
}

/* 网口名高亮样式 */
.highlight-ifname {
  color: #13c2c2;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

/* 未知网口名样式 */
.highlight-unknown {
  color: #c0c4cc;
  font-style: italic;
}

/* IP地址高亮样式 */
.highlight-ip {
  color: #409eff;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* 网关高亮样式 */
.highlight-gateway {
  color: #e6a23c;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* MAC地址样式 */
.mac-address {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

/* DNS服务器列表样式 */
.dns-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dns-item {
  display: flex;
  align-items: center;
}

.dns-ip {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #909399;
}

/* 加载图标样式 */
.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover:not(.is-disabled)) {
  color: #f56c6c;
  background-color: #fef0f0;
}

:deep(.danger-item.is-disabled) {
  color: #c0c4cc;
  cursor: not-allowed;
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

/* 确认删除按钮样式 */
:deep(.el-button--danger) {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

:deep(.el-button--danger:hover) {
  background-color: #f78989;
  border-color: #f78989;
}
</style>