<template>
  <div class="system-disks-mv200">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-info">
            <div class="title-section">
              <h3>云系统盘管理</h3>
              <div class="mv200-info">
                <el-tag type="primary" size="large" class="name-tag">
                  <el-icon><Monitor /></el-icon>
                  {{ mv200Info.name }}
                </el-tag>
                <el-tag type="info" size="large">
                  <el-icon><Link /></el-icon>
                  {{ mv200Info.ip }}
                </el-tag>
              </div>
            </div>
            <div class="action-buttons">
              <el-button 
                type="default" 
                @click="refreshData"
                :loading="loading"
              >
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <el-table 
        :data="systemDisks" 
        v-loading="loading"
        style="width: 100%"
      >
        <!-- 1. UUID列 -->
        <el-table-column 
          prop="uuid" 
          label="UUID" 
          width="120"
          sortable
        >
          <template #default="{ row }">
            <el-tag :type="isCloudInitBdev(row) ? 'info' : 'success'" size="small">
              {{ row.uuid }}
            </el-tag>
          </template>
        </el-table-column>
        
        <!-- 2. 网关节点列 - 加宽并左对齐 -->
        <el-table-column 
          label="网关节点"
          width="220"
          align="left"
        >
          <template #default="{ row }">
            <div class="gateway-nodes">
              <div v-if="isCloudInitBdev(row)" class="cloudinit-info">
                <el-tag type="info" size="small">cloudinit数据源</el-tag>
              </div>
              <div v-else-if="row.backend_specific?.block?.gws?.length" class="gateway-list">
                <div v-for="(gw, index) in row.backend_specific.block.gws" :key="index" class="gateway-item">
                  <el-tag size="small" class="gateway-tag">
                    <el-icon><Monitor /></el-icon>
                    {{ gw }}
                  </el-tag>
                </div>
              </div>
              <span v-else class="empty-text">-</span>
            </div>
          </template>
        </el-table-column>
        
        <!-- 3. 块设备列 (显示RBD路径) -->
        <el-table-column 
          label="块设备"
          min-width="200"
          show-overflow-tooltip
          align="left"
        >
          <template #default="{ row }">
            <div v-if="row.backend_specific?.block?.rbd_path" class="rbd-path-cell">
              <span class="rbd-path">
                {{ row.backend_specific.block.rbd_path }}
              </span>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <!-- 4. 镜像列 -->
        <el-table-column 
          label="镜像"
          min-width="180"
          show-overflow-tooltip
          align="left"
        >
          <template #default="{ row }">
            <div v-if="row.backend_specific?.block?.parent" class="image-cell">
              <el-tag type="warning" size="small" class="parent-tag">
                {{ getImageName(row.backend_specific.block.parent) }}
              </el-tag>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <!-- 5. 大小列 -->
        <el-table-column 
          label="大小(GB)"
          width="120"
          sortable
          :sort-method="sizeSortMethod"
          align="left"
        >
          <template #default="{ row }">
            <div v-if="row.backend_specific?.block?.size" class="size-cell">
              <span class="size-text">{{ row.backend_specific.block.size }}</span>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <!-- 操作列 -->
        <el-table-column 
          label="操作" 
          width="100" 
          fixed="right"
          align="center"
        >
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button type="primary" link>
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <!-- 详细信息 -->
                  <el-dropdown-item command="detail" class="dropdown-item">
                    <el-icon><View /></el-icon>
                    <span>详情</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态提示 -->
      <div v-if="systemDisks.length === 0 && !loading" class="empty-state">
        <el-empty description="暂无云系统盘" />
      </div>
    </el-card>

    <!-- 详细信息对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="云系统盘详细信息"
      width="600px"
    >
      <el-descriptions :column="1" border v-if="currentDisk">
        <el-descriptions-item label="UUID">
          <el-tag :type="isCloudInitBdev(currentDisk) ? 'info' : 'success'">
            {{ currentDisk.uuid }}
          </el-tag>
        </el-descriptions-item>
        
        <el-descriptions-item label="控制器">
          {{ currentDisk.ctrlr }}
        </el-descriptions-item>
        
        <el-descriptions-item label="CPU核心掩码">
          <el-tag size="small">{{ currentDisk.cpumask }}</el-tag>
        </el-descriptions-item>
        
        <el-descriptions-item label="虚拟队列">
          <div>数量: {{ currentDisk.vq_count }}</div>
          <div>大小: {{ currentDisk.vq_size }}</div>
        </el-descriptions-item>
        
        <el-descriptions-item label="块设备名称">
          <code>{{ currentDisk.backend_specific?.block?.bdev }}</code>
          <el-tag 
            v-if="isCloudInitBdev(currentDisk)" 
            type="info" 
            size="small" 
            style="margin-left: 8px;"
          >
            cloudinit数据源
          </el-tag>
        </el-descriptions-item>
        
        <el-descriptions-item label="RBD路径">
          <code>{{ currentDisk.backend_specific?.block?.rbd_path || '-' }}</code>
        </el-descriptions-item>
        
        <el-descriptions-item label="镜像路径">
          <code>{{ currentDisk.backend_specific?.block?.parent || '-' }}</code>
        </el-descriptions-item>
        
        <el-descriptions-item label="网关节点">
          <div v-if="currentDisk.backend_specific?.block?.gws?.length" class="gateway-detail">
            <el-tag
              v-for="(gw, index) in currentDisk.backend_specific.block.gws"
              :key="index"
              size="small"
              style="margin-right: 8px; margin-bottom: 4px;"
            >
              {{ gw }}
            </el-tag>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>
        
        <el-descriptions-item label="大小">
          <span v-if="currentDisk.backend_specific?.block?.size" class="size-text">
            {{ currentDisk.backend_specific.block.size }} GB
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        
        <el-descriptions-item label="状态">
          <el-tag :type="currentDisk.backend_specific?.block?.readonly ? 'warning' : 'success'">
            {{ currentDisk.backend_specific?.block?.readonly ? '只读' : '读写' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { 
  Refresh, 
  View,
  Monitor,
  Link,
  MoreFilled
} from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import type { ControllerInfo } from '@/types/api'

const route = useRoute()
const loading = ref(false)
const systemDisks = ref<ControllerInfo[]>([])
const currentDisk = ref<ControllerInfo | null>(null)
const detailDialogVisible = ref(false)

// 从路由参数中获取MV200信息
const mv200Info = ref({
  id: route.params.mv200Id as string,
  name: route.query.name as string || '',
  ip: route.query.ip as string || ''
})

// 检查是否为cloudinit数据源
const isCloudInitBdev = (disk: ControllerInfo): boolean => {
  return disk.backend_specific?.block?.bdev === 'yunsilicon_cloudinit_bdev'
}

// 从完整的镜像路径中提取镜像名称
const getImageName = (fullPath: string): string => {
  if (!fullPath) return '-'
  const parts = fullPath.split('/')
  return parts[parts.length - 1] || fullPath
}

// 大小排序方法
const sizeSortMethod = (a: ControllerInfo, b: ControllerInfo) => {
  const sizeA = a.backend_specific?.block?.size || 0
  const sizeB = b.backend_specific?.block?.size || 0
  return sizeA - sizeB
}

// 加载云系统盘数据
const loadSystemDisks = async () => {
  loading.value = true
  try {
    console.log('正在加载MV200系统盘，ID:', mv200Info.value.id)
    const response = await mv200Api.getSystemDisks(mv200Info.value.id)
    systemDisks.value = response
    
    // 按UUID排序
    systemDisks.value.sort((a, b) => a.uuid - b.uuid)
    console.log('加载成功，共', systemDisks.value.length, '个系统盘')
    
  } catch (error: any) {
    ElMessage.error('加载云系统盘失败: ' + (error.message || '未知错误'))
    console.error('加载云系统盘失败:', error)
  } finally {
    loading.value = false
  }
}

// 刷新数据
const refreshData = () => {
  loadSystemDisks()
}

// 操作命令处理
const handleCommand = (command: string, disk: ControllerInfo) => {
  switch (command) {
    case 'detail':
      showDiskDetail(disk)
      break
  }
}

// 显示详细信息
const showDiskDetail = (disk: ControllerInfo) => {
  currentDisk.value = disk
  detailDialogVisible.value = true
}

onMounted(() => {
  console.log('页面挂载，MV200信息:', mv200Info.value)
  loadSystemDisks()
})
</script>

<style scoped>
.card-header {
  margin-bottom: 0;
}

.header-info {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  width: 100%;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.title-section h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.mv200-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.name-tag {
  font-weight: 500;
}

.name-tag .el-icon,
.ip-tag .el-icon {
  margin-right: 4px;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

/* 表格样式 - 确保左对齐 */
.gateway-nodes {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}

.gateway-list {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
}

.gateway-item {
  display: flex;
  justify-content: flex-start;
  width: 100%;
}

.gateway-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  justify-content: flex-start;
  text-align: left;
}

/* 强制表格单元格左对齐 */
:deep(.el-table__cell) {
  text-align: left !important;
}

/* 特别为每个单元格设置左对齐 */
:deep(.el-table__cell .cell) {
  display: flex;
  justify-content: flex-start !important;
  text-align: left !important;
  align-items: center;
}

/* 网关节点列特别处理 */
:deep(.el-table__cell:nth-child(2) .cell) {
  justify-content: flex-start !important;
  padding-left: 0 !important;
}

.cloudinit-info {
  display: flex;
  justify-content: flex-start;
  width: 100%;
}

/* 其他单元格样式 */
.rbd-path-cell, .image-cell, .size-cell {
  display: flex;
  justify-content: flex-start;
  text-align: left;
}

.rbd-path {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: #409eff;
  text-align: left;
  word-break: break-all;
}

.parent-tag {
  font-family: 'Monaco', 'Consolas', monospace;
  text-align: left;
}

.size-text {
  color: #67c23a;
  font-weight: 500;
  text-align: left;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
  text-align: left;
}

/* 空状态样式 */
.empty-state {
  padding: 60px 0;
}

/* 操作下拉菜单样式 */
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  color: #f56c6c;
  background-color: #fef0f0;
}

/* 描述列表样式 */
:deep(.el-descriptions__label) {
  font-weight: 600;
  width: 120px;
}

:deep(.el-descriptions__content) {
  font-family: 'Monaco', 'Consolas', monospace;
}

:deep(code) {
  background-color: #f6f8fa;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 12px;
}

/* 详情对话框中的网关节点样式 */
.gateway-detail {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 4px;
}
</style>