<template>
  <div class="xsc-interface-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>XSC网口管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索网口名、SOC、裸金属服务器、IP地址、MTU、VLAN或描述"
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

      <el-table 
        :data="filteredInterfaces" 
        v-loading="loading"
        :default-sort="{ prop: 'mv200_ip', order: 'ascending' }"
      >
        <el-table-column label="网口名" width="120">
          <template #default="{ row }">
            <div class="interface-name-cell">
              <el-tooltip 
                v-if="row.ifnameLoading" 
                content="查询中..." 
                placement="top"
              >
                <el-icon class="loading-icon"><Loading /></el-icon>
              </el-tooltip>
              <span 
                v-else 
                :class="getInterfaceNameClass(row.ifname)"
              >
                {{ getInterfaceName(row.ifname) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column 
          label="SOC IP"
          sortable
          :sort-method="mv200IpSortMethod"
        >
          <template #default="{ row }">
            <div class="mv200-info">
              <div class="highlight-name">{{ getMv200Name(row.mv200_id) }}</div>
              <div class="highlight-ip">({{ getMv200Ip(row.mv200_id) }})</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column 
          label="裸金属服务器"
          sortable
          :sort-method="hostIpSortMethod"
        >
          <template #default="{ row }">
            <div class="highlight-name">{{ getHostName(row.mv200_id) }}</div>
            <div class="highlight-ip">({{ getHostIP(row.mv200_id) }})</div>
          </template>
        </el-table-column>
        <el-table-column 
          prop="ip" 
          label="IP地址"
          sortable
          :sort-method="ipSortMethod"
        >
          <template #default="{ row }">
            <span class="highlight-ip">{{ getIpOnly(row.ip) }}</span>
          </template>
        </el-table-column>
        <el-table-column 
          prop="vlan_tag" 
          label="VLAN ID" 
          width="100"
          sortable
        >
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
import { deviceApi } from '@/api/device'
import type { InterfaceInfo, MVServer, ServerDetailResponse } from '@/types/api'

const router = useRouter()
const loading = ref(false)
const interfaces = ref<(InterfaceInfo & { 
  deleting?: boolean; 
  ifname?: string;
  ifnameLoading?: boolean;
})[]>([])
const mv200Servers = ref<MVServer[]>([])
const devices = ref<ServerDetailResponse[]>([])
const searchKeyword = ref('')

// IP地址排序函数 - 正确的数值比较
const ipSortMethod = (a: InterfaceInfo, b: InterfaceInfo) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    // 将IP地址转换为一个可比较的数字
    // 每段数字占8位，从高位到低位依次是第1段、第2段、第3段、第4段
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const ipA = ipToNumber(getIpOnly(a.ip));
  const ipB = ipToNumber(getIpOnly(b.ip));
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

// SOC IP排序函数
const mv200IpSortMethod = (a: InterfaceInfo, b: InterfaceInfo) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const ipA = ipToNumber(getMv200Ip(a.mv200_id));
  const ipB = ipToNumber(getMv200Ip(b.mv200_id));
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

// 裸金属服务器IP排序函数
const hostIpSortMethod = (a: InterfaceInfo, b: InterfaceInfo) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const ipA = ipToNumber(getHostIP(a.mv200_id));
  const ipB = ipToNumber(getHostIP(b.mv200_id));
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

// 辅助函数：用于数据加载时的排序
const ipSort = (ipA: string, ipB: string) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  return ipToNumber(ipA) - ipToNumber(ipB);
};

// 加载所有设备
const loadAllDevices = async () => {
  try {
    const allDevices = await deviceApi.getAll()
    devices.value = allDevices
  } catch (error) {
    console.error('加载设备列表失败:', error)
  }
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const interfacesResponse = await networkApi.getAll()
    
    // 如果没有网口数据，直接返回
    if (!interfacesResponse || interfacesResponse.length === 0) {
      interfaces.value = []
      mv200Servers.value = []
      return
    }
    
    // 先设置基础数据，不阻塞列表显示
    interfaces.value = interfacesResponse.map(intf => ({
      ...intf,
      deleting: false,
      ifname: undefined,
      ifnameLoading: true // 初始状态为加载中
    }))

    const [mv200Response] = await Promise.all([
      mv200Api.getAll(),
    ])
    mv200Servers.value = mv200Response

    // 单独加载设备列表
    await loadAllDevices()

    // 按SOC IP排序
    interfaces.value = interfaces.value.sort((a, b) => {
      const ipA = getMv200Ip(a.mv200_id);
      const ipB = getMv200Ip(b.mv200_id);
      return ipSort(ipA, ipB);
    });

    // 异步加载网口名信息，不阻塞主流程
    loadInterfaceNames()
  } catch (error) {
    ElMessage.error('加载XSC网口列表失败')
  } finally {
    loading.value = false
  }
}

// 异步加载网口名
const loadInterfaceNames = async () => {
  const promises = interfaces.value.map(async (intf, index) => {
    try {
      const detail = await networkApi.getById(intf.id, intf.mv200_id)
      // 更新对应的接口信息
      interfaces.value[index] = {
        ...interfaces.value[index],
        ifname: detail.ifname,
        ifnameLoading: false
      }
    } catch (error) {
      console.warn(`Failed to get interface name for ${intf.id}:`, error)
      // 即使失败也要更新状态
      interfaces.value[index] = {
        ...interfaces.value[index],
        ifname: undefined,
        ifnameLoading: false
      }
    }
  })
  
  // 可以并行执行所有查询，也可以限制并发数
  await Promise.allSettled(promises)
}

// 计算属性：创建MV200 ID到名称的映射
const mv200Map = computed(() => {
  const map = new Map<string, MVServer>()
  mv200Servers.value.forEach(server => {
    map.set(server.id, server)
  })
  return map
})

// 创建设备映射，通过网卡序列号查找对应的设备
const deviceMap = computed(() => {
  const map = new Map<string, ServerDetailResponse>()
  devices.value.forEach(device => {
    // 遍历设备的网卡，建立网卡序列号到设备的映射
    device.nics?.forEach(nic => {
      if (nic.sn) {
        map.set(nic.sn, device)
      }
    })
  })
  return map
})

// 创建MV200映射，通过MV200 ID获取nic_sn
const mv200NicMap = computed(() => {
  const map = new Map<string, string>()
  mv200Servers.value.forEach(server => {
    map.set(server.id, server.nic_sn)
  })
  return map
})

// 计算属性：过滤网口列表
const filteredInterfaces = computed(() => {
  let filtered = interfaces.value
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = interfaces.value.filter(intf => {
      // 搜索网口名
      if (intf.ifname && intf.ifname.toLowerCase().includes(keyword)) return true
      
      // 搜索IP地址
      if (intf.ip.toLowerCase().includes(keyword)) return true

      // 搜索裸金属服务器信息
      const hostName = getHostName(intf.mv200_id).toLowerCase()
      const hostIP = getHostIP(intf.mv200_id).toLowerCase()
      if (hostName.includes(keyword) || hostIP.includes(keyword)) return true
      
      // 搜索VLAN
      if (intf.vlan_tag.toString().includes(keyword)) return true
      
      // 搜索MTU
      if (intf.mtu?.toString().includes(keyword)) return true
      
      // 搜索描述
      if (intf.description && intf.description.toLowerCase().includes(keyword)) return true
      
      // 搜索MV200服务器信息
      const mv200Name = getMv200Name(intf.mv200_id).toLowerCase()
      const mv200Ip = getMv200Ip(intf.mv200_id).toLowerCase()
      if (mv200Name.includes(keyword) || mv200Ip.includes(keyword)) return true

      return false
    })
  }
  
  // 返回过滤后的数据，el-table会处理排序
  return filtered
})

// 根据ID获取MV200服务器名称
const getMv200Name = (mv200Id: string) => {
  const server = mv200Map.value.get(mv200Id)
  return server ? server.name : mv200Id
}

// 根据ID获取MV200服务器IP
const getMv200Ip = (mv200Id: string) => {
  const server = mv200Map.value.get(mv200Id)
  return server ? server.ip_address : '0.0.0.0'
}

// 根据ID获取裸金属服务器名称
const getHostName = (mv200Id: string) => {
  // 先通过MV200 ID获取对应的网卡序列号
  const nicSn = mv200NicMap.value.get(mv200Id)
  if (!nicSn) return '未知服务器'
  
  // 再通过网卡序列号获取对应的设备
  const device = deviceMap.value.get(nicSn)
  if (!device) return '未知服务器'
  
  return device.bmc?.hostname || '未知服务器'
}

// 根据ID获取裸金属服务器IP
const getHostIP = (mv200Id: string) => {
  // 先通过MV200 ID获取对应的网卡序列号
  const nicSn = mv200NicMap.value.get(mv200Id)
  if (!nicSn) return '0.0.0.0'
  
  // 再通过网卡序列号获取对应的设备
  const device = deviceMap.value.get(nicSn)
  if (!device) return '0.0.0.0'
  
  return device.device?.ip || '0.0.0.0'
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
  if (!ipWithMask) return '0.0.0.0'
  // 分割IP和掩码，返回IP部分
  const [ip] = ipWithMask.split('/')
  return ip || '0.0.0.0'
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

/* 网口名单元格样式 */
.interface-name-cell {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-height: 24px;
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

/* 名称高亮样式 - 只改变字体颜色 */
.highlight-name {
  color: #67c23a;
  font-weight: 600;
}

/* IP地址高亮样式 */
.highlight-ip {
  color: #409eff;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* MAC地址样式 */
.mac-address {
  color: #e6a23c;  /* 改为橙色 */
  font-weight: 500;
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
  color: #409eff;
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