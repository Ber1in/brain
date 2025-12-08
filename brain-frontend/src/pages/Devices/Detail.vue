<template>
  <div class="device-detail">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>服务器详情 - {{ deviceData.bmc?.hostname }}</h2>
          <div class="header-actions">
            <el-button 
              :type="isFollowing ? 'success' : 'primary'" 
              :icon="isFollowing ? 'Check' : 'Star'"
              @click="handleFollow"
              :loading="followLoading"
              class="follow-btn"
            >
              {{ isFollowing ? '已关注' : '关注' }}
            </el-button>
            <el-button 
              type="warning" 
              @click="handleRefresh" 
              :loading="refreshing"
              :disabled="refreshing"
            >
              <el-icon><Refresh /></el-icon>
              {{ refreshing ? '更新中...' : '更新信息' }}
            </el-button>
            <!-- 操作下拉框 -->
            <el-dropdown @command="(command) => handleCommand(command)" size="small">
              <el-button type="primary">
                操作<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu class="action-dropdown-menu">
                  <el-dropdown-item command="edit" class="dropdown-item">
                    <el-icon><Edit /></el-icon>
                    <span>编辑</span>
                  </el-dropdown-item>
                  
                  <!-- 修改启动项 -->
                  <el-dropdown-item 
                    command="bootEntry" 
                    class="dropdown-item boot-entry-item"
                  >
                    <el-icon><Setting /></el-icon>
                    <span>修改启动项</span>
                  </el-dropdown-item>

                  <!-- 电源操作 -->
                  <el-dropdown-item 
                    command="powerCycle" 
                    class="dropdown-item power-cycle-item"
                  >
                    <el-icon><Refresh /></el-icon>
                    <span>冷重启</span>
                  </el-dropdown-item>
                  <el-dropdown-item 
                    command="powerReset" 
                    class="dropdown-item power-reset-item"
                  >
                    <el-icon><RefreshRight /></el-icon>
                    <span>热重启</span>
                  </el-dropdown-item>
                  
                  <!-- 占用服务器按钮 -->
                  <el-dropdown-item 
                    command="occupy" 
                    :disabled="isDeviceOccupied && !isCurrentUserOccupier"
                    class="occupy-item occupy-server-item dropdown-item"
                  >
                    <el-icon><Timer /></el-icon>
                    <span>
                      {{ getOccupyButtonText() }}
                    </span>
                    <el-tooltip 
                      v-if="isDeviceOccupied && !isCurrentUserOccupier"
                      effect="dark" 
                      content="当前服务器已被占用，请联系占用人"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  
                  <!-- 释放占用按钮 -->
                  <el-dropdown-item 
                    command="release" 
                    :disabled="!isDeviceOccupied || !isCurrentUserOccupier"
                    class="occupy-item end-occupy-item dropdown-item"
                  >
                    <el-icon><Unlock /></el-icon>
                    <span>释放占用</span>
                    <el-tooltip 
                      v-if="!isDeviceOccupied"
                      effect="dark" 
                      content="服务器未被占用"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                    <el-tooltip 
                      v-else-if="isDeviceOccupied && !isCurrentUserOccupier"
                      effect="dark" 
                      content="当前用户不是占用人，请联系占用人"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided class="danger-item dropdown-item">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <!-- 其余内容保持不变 -->
      <el-descriptions :column="2" border>
        <!-- 基本信息 -->
        <el-descriptions-item label="创建时间">{{ formatTime(deviceData.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(deviceData.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="占用信息">
          <div v-if="isDeviceOccupied">
            <el-tag type="success" style="margin-right: 8px;">{{ deviceData.user }}</el-tag>
            <span>占用至 {{ getEndTimeDisplay() }}</span>
          </div>
          <el-tag v-else type="info">未占用</el-tag>
        </el-descriptions-item>

        <!-- BMC信息 -->
        <el-descriptions-item label="服务器名称">{{ deviceData.bmc?.hostname || '-' }}</el-descriptions-item>
        <el-descriptions-item label="BMC IP">{{ deviceData.bmc?.ip || '-' }}</el-descriptions-item>

        <!-- 服务器信息 -->
        <el-descriptions-item label="服务器IP">{{ deviceData.device?.ip || '-' }}</el-descriptions-item>
        
        <!-- 新增的管理口信息 -->
        <el-descriptions-item label="管理口MAC地址">{{ deviceData.device?.mac || '-' }}</el-descriptions-item>
        <el-descriptions-item label="管理网网关">{{ deviceData.device?.gateway || '-' }}</el-descriptions-item>

        <!-- 操作系统类型 - 修改后的展示方式 -->
        <el-descriptions-item label="操作系统类型" :span="2">
          <div v-if="bootEntriesLoading" class="loading-text">
            <el-icon class="is-loading"><Loading /></el-icon>
            查询启动项信息中...
          </div>
          <div v-else-if="bootEntriesList && bootEntriesList.length > 0">
            <div 
              v-for="os in bootEntriesList" 
              :key="os.key" 
              class="os-item"
              :class="{ 
                'current-os': os.isCurrent,
                'default-os': os.isDefault
              }"
            >
              {{ os.displayText }}
            </div>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>

        <!-- 标签 -->
        <el-descriptions-item label="标签" :span="2">
          <div v-if="deviceData.tags && deviceData.tags.length > 0">
            <el-tag 
              v-for="tag in deviceData.tags" 
              :key="tag" 
              type="info"
              style="margin-right: 8px; margin-bottom: 4px;"
            >
              {{ tag }}
            </el-tag>
          </div>
          <span v-else>-</span>
        </el-descriptions-item>

        <!-- 备注 -->
        <el-descriptions-item label="备注" :span="2">
          {{ deviceData.notes || '无' }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 服务器信息、CPU信息、网卡信息并排布局 1:1:3 -->
      <div class="info-row" style="margin-top: 20px;">
        <!-- 服务器信息卡片 - 1/5宽度 -->
        <el-card header="服务器信息" class="server-info-card" v-if="hasServerInfo">
          <div class="compact-info-list">
            <div class="info-item">
              <div class="info-label">厂商</div>
              <div class="info-value">{{ deviceData.device?.vendor || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">型号</div>
              <div class="info-value">{{ deviceData.device?.product || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">序列号</div>
              <div class="info-value">{{ deviceData.device?.sn || '-' }}</div>
            </div>
          </div>
        </el-card>

        <!-- CPU信息卡片 - 1/5宽度 -->
        <el-card header="CPU信息" class="cpu-info-card" v-if="hasCpuInfo">
          <div class="compact-info-list">
            <div class="info-item">
              <div class="info-label">厂商</div>
              <div class="info-value">{{ deviceData.device?.cpu_vendor || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">型号</div>
              <div class="info-value">{{ deviceData.device?.cpu_mode || '-' }}</div>
            </div>
            <div class="info-item">
              <div class="info-label">架构</div>
              <div class="info-value">{{ deviceData.device?.arch || '-' }}</div>
            </div>
          </div>
        </el-card>

        <!-- 网卡详细信息 - 3/5宽度 -->
        <el-card header="网卡信息" class="nic-card" v-if="deviceData.nics && deviceData.nics.length > 0">
          <el-table :data="processedNics" class="compact-table">
            <el-table-column prop="type" label="类型" width="110">
              <template #default="{ row }">
                <span>{{ formatNicTypeForDisplay(row.type) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="sn" label="序列号" width="170"/>
            <!-- BDF列移到MAC地址前面 -->
            <el-table-column label="BDF" width="80">
              <template #default="{ row }">
                <div v-if="row.nic_info && row.nic_info.length > 0">
                  <div 
                    v-for="(info, index) in row.nic_info" 
                    :key="index" 
                    class="bdf-mac-pair"
                  >
                    <div class="bdf-item">{{ info.bdf || '-' }}</div>
                  </div>
                </div>
                <span v-else class="empty-text">-</span>
              </template>
            </el-table-column>
            <!-- 网口名列 -->
            <el-table-column label="网口名" width="100">
              <template #default="{ row }">
                <div v-if="row.nic_info && row.nic_info.length > 0">
                  <div 
                    v-for="(info, index) in row.nic_info" 
                    :key="index" 
                    class="bdf-mac-pair"
                  >
                    <div class="iface-name">{{ info.iface !== null ? info.iface : '-' }}</div>
                  </div>
                </div>
                <span v-else class="empty-text">-</span>
              </template>
            </el-table-column>
            <el-table-column label="MAC地址">
              <template #default="{ row }">
                <div v-if="row.nic_info && row.nic_info.length > 0">
                  <div 
                    v-for="(info, index) in row.nic_info" 
                    :key="index" 
                    class="bdf-mac-pair"
                  >
                    <div class="mac-address">{{ info.mac || '-' }}</div>
                  </div>
                </div>
                <span v-else class="empty-text">-</span>
              </template>
            </el-table-column>
            <!-- SOC IP列 - 已添加匹配异常提示 -->
            <el-table-column label="SOC IP" width="140">
              <template #default="{ row }">
                <div v-if="getMv200StatusForNic(row.sn)" class="soc-ip-status">
                  <!-- 匹配异常状态 -->
                  <div 
                    v-if="getMv200StatusForNic(row.sn).status === 'multiple_matched'" 
                    class="error-info"
                  >
                    <el-tooltip 
                      effect="dark" 
                      :content="getMultipleMv200Tooltip(getMv200StatusForNic(row.sn))" 
                      placement="top"
                    >
                      <div class="error-message">
                        <el-icon><Warning /></el-icon>
                        <span>匹配异常</span>
                        <span class="match-count">({{ getMv200StatusForNic(row.sn).devices.length }}张)</span>
                      </div>
                    </el-tooltip>
                  </div>
                  
                  <!-- 正常匹配状态 -->
                  <div 
                    v-else-if="getMv200StatusForNic(row.sn).status === 'matched'" 
                    class="soc-ip-link"
                  >
                    <el-link 
                      type="primary" 
                      @click="handleMv200Detail(getMv200StatusForNic(row.sn).data)"
                      class="underlined-link"
                      :underline="false"
                    >
                      {{ getMv200StatusForNic(row.sn).data.ip_address }}
                    </el-link>
                  </div>
                  
                  <!-- 未匹配状态 -->
                  <span v-else class="empty-text">-</span>
                </div>
                <span v-else class="empty-text">-</span>
              </template>
            </el-table-column>
            <el-table-column v-if="hasAidpuNics" prop="aidpu_sn" label="AIDPU SN" width="120" />
            <el-table-column v-if="hasAidpuNics" prop="firmware_version" label="固件版本" width="100" />
            <el-table-column v-if="hasAidpuNics" prop="management_ip" label="管理IP" width="100" />
          </el-table>
        </el-card>
      </div>
    </el-card>

    <!-- 占用/修改时间对话框 -->
    <el-dialog
      v-model="occupyDialogVisible"
      :title="occupyDialogTitle"
      width="480px"
      class="occupy-dialog"
      :close-on-click-modal="false"
    >
      <div class="dialog-header">
        <div class="device-info">
          <el-icon class="server-icon"><Monitor /></el-icon>
          <div class="info-content">
            <div class="hostname">{{ deviceData.bmc?.hostname }}</div>
            <div class="ip-address">{{ deviceData.device?.ip }}</div>
          </div>
        </div>
        <div class="user-info">
          <el-avatar :size="32" style="background-color: #409eff;">
            {{ currentUser?.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="username">{{ currentUser }}</span>
        </div>
      </div>

      <div v-if="isModifyMode && deviceData.time" class="original-time">
        <el-icon><Clock /></el-icon>
        <span>原截止时间：</span>
        <strong>{{ getEndTimeDisplay() }}</strong>
      </div>

      <el-form :model="occupyForm" class="occupy-form" label-width="auto">
        <div class="form-section">
          <div class="section-title">
            <el-icon><Calendar /></el-icon>
            <span>{{ isModifyMode ? '设置新的结束时间' : '设置占用结束时间' }}</span>
          </div>
          
          <el-form-item class="compact-item">
            <template #label>
              <span class="form-label">结束时间</span>
              <span class="required">*</span>
            </template>
            <el-date-picker
              v-model="occupyForm.endTime"
              type="datetime"
              placeholder="选择占用结束时间"
              style="width: 100%"
              :disabled-date="disabledDate"
              :disabled-hours="disabledHours"
              :disabled-minutes="disabledMinutes"
              :disabled-seconds="disabledSeconds"
              :shortcuts="timeShortcuts"
              class="enhanced-picker"
            />
          </el-form-item>

          <el-form-item class="compact-item">
            <template #label>
              <span class="form-label">占用时长</span>
            </template>
            <div class="duration-display">
              <el-tag 
                :type="getDurationType()" 
                class="duration-tag"
                :class="getDurationSize()"
              >
                <el-icon><Watch /></el-icon>
                {{ calculateDuration() }}
              </el-tag>
              <div v-if="occupyForm.endTime" class="duration-detail">
                <span class="end-time">截止: {{ getEndTimeDisplayFromForm() }}</span>
              </div>
            </div>
          </el-form-item>
        </div>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="occupyDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handleOccupy" 
            :loading="occupyLoading"
            :disabled="!occupyForm.endTime"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            {{ isModifyMode ? '确认修改' : '确认占用' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 修改启动项对话框 -->
    <el-dialog
      v-model="bootEntryDialogVisible"
      title="修改启动项"
      width="700px"
      class="boot-entry-dialog"
      :close-on-click-modal="false"
    >
      <div class="boot-entries-content" v-loading="bootEntriesLoading">
        <div class="dialog-header">
          <div class="device-info">
            <el-icon class="server-icon"><Monitor /></el-icon>
            <div class="info-content">
              <div class="hostname">{{ deviceData.bmc?.hostname }}</div>
              <div class="ip-address">{{ deviceData.device?.ip }}</div>
            </div>
          </div>
          <div class="user-info">
            <el-avatar :size="32" style="background-color: #409eff;">
              {{ currentUser?.charAt(0).toUpperCase() }}
            </el-avatar>
            <span class="username">{{ currentUser }}</span>
          </div>
        </div>
        <!-- 启动项选择 -->
        <div class="boot-selection">
          <div class="section-title">
            <el-icon><Setting /></el-icon>
            <span>选择下次启动项</span>
          </div>

          <div v-if="bootEntriesList.length > 0" class="boot-entries-list">
            <div
              v-for="entry in bootEntriesList"
              :key="entry.key"
              class="boot-entry-item"
              :class="{
                'current-entry': entry.isCurrent,
                'selected-entry': selectedBootEntry === entry.key
              }"
              @click="selectedBootEntry = entry.key"
            >
              <div class="boot-entry-content">
                <div class="boot-entry-main">
                  <el-radio 
                    v-model="selectedBootEntry" 
                    :label="entry.key"
                    class="boot-radio"
                  >
                    <div class="boot-entry-text">{{ entry.value }}</div>
                  </el-radio>
                  <div class="boot-entry-tags">
                    <el-tag v-if="entry.isCurrent" type="success" size="small">当前</el-tag>
                    <el-tag v-if="entry.isNext" type="warning" size="small">下次</el-tag>
                    <el-tag v-if="entry.isDefault" type="info" size="small">默认</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="no-boot-entries">
            <el-empty description="暂无启动项信息" />
          </div>

          <!-- 启动选项 -->
          <div class="boot-options">
            <el-checkbox v-model="setAsDefaultBoot" class="default-boot-checkbox">
              设置为默认启动项
            </el-checkbox>
            <div class="option-tip">
              勾选后，此启动项将作为服务器的默认启动项
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="bootEntryDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handleSetBootEntry" 
            :loading="bootEntryLoading"
            :disabled="!selectedBootEntry"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            确认修改
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 电源重启确认对话框 -->
    <el-dialog
      v-model="powerDialogVisible"
      :title="powerDialogTitle"
      width="400px"
      class="power-dialog"
      :close-on-click-modal="false"
    >
      <div class="power-dialog-content">
        <div class="dialog-tip">
          <el-alert
            :title="powerType === 'cycle' ? '冷重启将完全断电后重新启动服务器' : '热重启将保持通电状态重新启动服务器'"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
        <div class="confirm-message">
          <p>
            确定要对服务器 <strong>"{{ deviceData.bmc?.hostname }}"</strong> 执行{{ powerType === 'cycle' ? '冷重启' : '热重启' }}吗？
          </p>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="powerDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handlePowerConfirm" 
            :loading="powerLoading"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            确认重启
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Edit, 
  Refresh, 
  Loading, 
  Timer, 
  Unlock, 
  InfoFilled,
  Delete,
  Setting,
  RefreshRight,
  ArrowDown,
  Monitor,
  Clock,
  Calendar,
  Watch,
  Check,
  Star,
  Warning
} from '@element-plus/icons-vue'
import { deviceApi } from '@/api/device'
import { mv200Api } from '@/api/mv200'
import type { ServerDetailResponse, AIDPU_Nic, BootEntriesResponse, MVServer, NicBase, NicInfo } from '@/types/api'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const deviceId = ref<string>('')
const refreshing = ref(false)
const bootEntriesLoading = ref(false)
const bootEntriesData = ref<BootEntriesResponse | null>(null)
const allMv200s = ref<MVServer[]>([])

// 当前用户信息
const currentUser = computed(() => authStore.username)

// 占用服务器相关
const occupyDialogVisible = ref(false)
const occupyLoading = ref(false)
const occupyForm = reactive({
  endTime: null as Date | null
})

// 启动项管理相关
const bootEntryDialogVisible = ref(false)
const bootEntryLoading = ref(false)
const selectedBootEntry = ref<string>('')
const setAsDefaultBoot = ref(false)

// 电源操作相关
const powerDialogVisible = ref(false)
const powerLoading = ref(false)
const powerType = ref<'cycle' | 'reset'>('cycle')

const deviceData = ref<ServerDetailResponse>({
  bmc: { hostname: '', ip: '' },
  device: { ip: '', username: '' },
  nics: [],
  tags: [],
  notes: '',
  user: '',
  time: '',
  created_at: '',
  updated_at: '',
  id: ''
})

// 关注相关
const followLoading = ref(false)

// 计算当前用户是否已关注
const isFollowing = computed(() => {
  const recipients = deviceData.value.recipients || []
  return recipients.includes(currentUser.value)
})

// 根据网卡序列号获取对应的MV200匹配状态（支持多种状态）
const getMv200StatusForNic = (nicSn: string): any => {
  if (!nicSn || !allMv200s.value.length) {
    return {
      status: 'not_matched',
      message: '未找到匹配的MV200'
    }
  }
  
  // 查找所有匹配的MV200（可能有多个）
  const matchedMv200s = allMv200s.value.filter(mv200 => mv200.nic_sn === nicSn)
  
  // 根据匹配到的MV200数量返回不同状态
  if (matchedMv200s.length === 0) {
    return {
      status: 'not_matched',
      message: '未找到匹配的MV200'
    }
  } else if (matchedMv200s.length === 1) {
    return {
      status: 'matched',
      data: matchedMv200s[0],
      message: null
    }
  } else {
    // 匹配到多张MV200的情况
    return {
      status: 'multiple_matched',
      devices: matchedMv200s.map(mv200 => ({
        name: mv200.name,
        ip_address: mv200.ip_address,
        id: mv200.id
      })),
      message: `匹配到 ${matchedMv200s.length} 张MV200`,
      count: matchedMv200s.length
    }
  }
}

// 获取多匹配提示信息的方法（用于MV200匹配异常）
const getMultipleMv200Tooltip = (mv200Info: any) => {
  if (mv200Info.status !== 'multiple_matched') return ''
  
  const mv200List = mv200Info.devices.map((device: any, index: number) => 
    `${index + 1}. ${device.name} (${device.ip_address})`
  ).join('\n')
  
  return `${mv200Info.message}\n\n:\n${mv200List}`
}

// 关注/取消关注服务器
const handleFollow = async () => {
  try {
    followLoading.value = true
    
    const updateData = {
      auto: false,
      focus: !isFollowing.value, // true表示关注，false表示取消关注
      device: {
        ip: deviceData.value.device.ip,
        username: deviceData.value.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: deviceData.value.bmc.hostname,
        ip: deviceData.value.bmc.ip
      },
      tags: deviceData.value.tags || [],
      notes: deviceData.value.notes || '',
      os_types: deviceData.value.os_types || []
    }
    
    await deviceApi.update(deviceId.value, updateData)
    
    if (!isFollowing.value) {
      // 关注成功
      ElMessage.success(`关注成功，将会接收到该服务器的占用释放提醒邮件`)
    } else {
      // 取消关注成功
      ElMessage.success('取消关注, 不再接收该服务器的占用释放提醒邮件')
    }
    
    // 重新加载数据以更新关注状态
    await loadDeviceDetail()
    
  } catch (error: any) {
    const action = isFollowing.value ? '取消关注' : '关注'
    ElMessage.error(`${action}失败: ${error.response?.data?.detail || '请求失败'}`)
  } finally {
    followLoading.value = false
  }
}

// 计算是否有服务器信息
const hasServerInfo = computed(() => {
  return deviceData.value.device?.vendor || deviceData.value.device?.product || deviceData.value.device?.sn
})

// 计算是否有CPU信息
const hasCpuInfo = computed(() => {
  return deviceData.value.device?.arch || deviceData.value.device?.cpu_vendor || deviceData.value.device?.cpu_mode
})

// 计算操作系统类型列表
const bootEntriesList = computed(() => {
  const bootEntries = bootEntriesData.value
  if (!bootEntries || !bootEntries.entries) return []

  const { entries, current, next, default: defaultOs } = bootEntries
  const result = []

  for (const [key, value] of Object.entries(entries)) {
    const statusFlags = []
    if (key === current) statusFlags.push('当前')
    if (key === next) statusFlags.push('下次')
    if (key === defaultOs) statusFlags.push('默认')
    
    let displayText = value
    if (statusFlags.length > 0) {
      displayText += ` (${statusFlags.join(')(')})`
    }

    result.push({
      key,
      value,
      displayText,
      isCurrent: key === current,
      isNext: key === next,
      isDefault: key === defaultOs
    })
  }

  return result
})

// 处理网卡数据，统一处理 nic_info
const processedNics = computed(() => {
  if (!deviceData.value.nics) return []
  
  return deviceData.value.nics.map(nic => {
    // 所有网卡都有 nic_info 数组，但普通网卡可能没有
    const nicInfo = (nic as any).nic_info || []
    
    return {
      ...nic,
      nic_info: nicInfo,
      // 标记是否为AIDPU网卡
      isAidpu: 'soc_ip' in nic,
      displayType: nic.type
    }
  })
})

// MV200详情页面跳转
const handleMv200Detail = (mv200: MVServer | null) => {
  if (mv200 && mv200.id) {
    router.push(`/mv200/detail/${mv200.id}`)
  } else {
    ElMessage.warning('无法找到MV200详情')
  }
}

// 检查是否有AIDPU网卡
const hasAidpuNics = computed(() => {
  return deviceData.value.nics?.some(nic => 'soc_ip' in nic)
})

// 时间快捷选项
const timeShortcuts = [
  {
    text: '1小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3600 * 1000)
      return date
    }
  },
  {
    text: '2小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 2 * 3600 * 1000)
      return date
    }
  },
  {
    text: '4小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 4 * 3600 * 1000)
      return date
    }
  },
  {
    text: '8小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 8 * 3600 * 1000)
      return date
    }
  },
  {
    text: '1天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 24 * 3600 * 1000)
      return date
    }
  },
  {
    text: '3天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3 * 24 * 3600 * 1000)
      return date
    }
  }
]

// 根据剩余秒数计算截止时间
const getEndTimeFromSeconds = (seconds: number): Date => {
  const now = new Date()
  now.setTime(now.getTime() + seconds * 1000)
  return now
}

// 根据截止时间计算剩余秒数
const getSecondsFromEndTime = (endTime: Date): number => {
  const now = new Date()
  return Math.floor((endTime.getTime() - now.getTime()) / 1000)
}

// 统一的日期时间格式化函数
const formatDateTime = (date: Date): string => {
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  
  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`
}

// 检查服务器是否被占用
const isDeviceOccupied = computed(() => {
  const device = deviceData.value
  // 检查user和time是否有效
  const hasValidUser = device.user && device.user.trim() !== ''
  const hasValidTime = device.time !== undefined && device.time !== null && device.time > 0
  
  // 如果有有效的用户和时间，再检查时间是否过期
  if (hasValidUser && hasValidTime) {
    return device.time > 0 // 剩余时间大于0表示未过期
  }
  
  return false
})

// 检查当前用户是否是占用人
const isCurrentUserOccupier = computed(() => {
  return deviceData.value.user === currentUser.value
})

// 根据剩余秒数显示截止时间
const getEndTimeDisplay = () => {
  const device = deviceData.value
  if (!device.time || device.time <= 0) return '-'
  
  const endTime = getEndTimeFromSeconds(device.time)
  return formatDateTime(endTime)
}

// 获取占用按钮文本
const getOccupyButtonText = () => {
  if (isDeviceOccupied.value && isCurrentUserOccupier.value) {
    return '修改占用'
  }
  return '占用服务器'
}

// 检查是否为修改模式
const isModifyMode = computed(() => {
  return isDeviceOccupied.value && isCurrentUserOccupier.value
})

// 获取对话框标题
const occupyDialogTitle = computed(() => {
  return isModifyMode.value ? '修改占用' : '占用服务器'
})

// 禁用超过3天的日期和时间
const disabledDate = (time: Date) => {
  const now = new Date()
  const threeDaysLater = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000)
  
  // 只允许选择今天、明天、后天、大后天（4天内）
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const maxDate = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000) // 大后天
  
  // 禁用今天之前和3天后的日期
  return time.getTime() < today.getTime() || time.getTime() > maxDate.getTime()
}

// 禁用小时
const disabledHours = () => {
  const now = new Date()
  const selectedDate = occupyForm.endTime
  
  if (!selectedDate) return []
  
  const disabledHours: number[] = []
  const selectedDay = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  
  // 如果选择的是今天，禁用当前时间之前的小时
  if (selectedDay.getTime() === today.getTime()) {
    for (let i = 0; i < now.getHours(); i++) {
      disabledHours.push(i)
    }
  }
  
  // 如果选择的是3天后，禁用当前时间之后的小时
  const threeDaysLater = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000)
  if (selectedDay.getTime() === threeDaysLater.getTime()) {
    for (let i = now.getHours() + 1; i < 24; i++) {
      disabledHours.push(i)
    }
  }
  
  return disabledHours
}

// 禁用分钟
const disabledMinutes = (selectedHour: number) => {
  const now = new Date()
  const selectedDate = occupyForm.endTime
  
  if (!selectedDate) return []
  
  const disabledMinutes: number[] = []
  const selectedDay = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  
  // 如果选择的是今天且选中的小时等于当前小时，禁用当前时间之前的分钟
  if (selectedDay.getTime() === today.getTime() && selectedHour === now.getHours()) {
    for (let i = 0; i < now.getMinutes(); i++) {
      disabledMinutes.push(i)
    }
  }
  
  // 如果选择的是3天后且选中的小时等于当前小时，禁用当前时间之后的分钟
  const threeDaysLater = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000)
  if (selectedDay.getTime() === threeDaysLater.getTime() && selectedHour === now.getHours()) {
    for (let i = now.getMinutes() + 1; i < 60; i++) {
      disabledMinutes.push(i)
    }
  }
  
  return disabledMinutes
}

// 禁用秒数
const disabledSeconds = (selectedHour: number, selectedMinute: number) => {
  const now = new Date()
  const selectedDate = occupyForm.endTime
  
  if (!selectedDate) return []
  
  const disabledSeconds: number[] = []
  const selectedDay = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  
  // 如果选择的是今天且选中的小时和分钟都等于当前时间，禁用当前时间之前的秒数
  if (selectedDay.getTime() === today.getTime() && 
      selectedHour === now.getHours() && 
      selectedMinute === now.getMinutes()) {
    for (let i = 0; i < now.getSeconds(); i++) {
      disabledSeconds.push(i)
    }
  }
  
  // 如果选择的是3天后且选中的小时和分钟都等于当前时间，禁用当前时间之后的秒数
  const threeDaysLater = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000)
  if (selectedDay.getTime() === threeDaysLater.getTime() && 
      selectedHour === now.getHours() && 
      selectedMinute === now.getMinutes()) {
    for (let i = now.getSeconds() + 1; i < 60; i++) {
      disabledSeconds.push(i)
    }
  }
  
  return disabledSeconds
}

// 计算占用时长（显示用）
const calculateDuration = () => {
  if (!occupyForm.endTime) return '-'
  
  const now = new Date()
  const endTime = new Date(occupyForm.endTime)
  const durationMs = endTime.getTime() - now.getTime()
  
  if (durationMs <= 0) return '结束时间必须晚于当前时间'
  
  const seconds = Math.floor(durationMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) {
    return `${days}天${hours % 24}小时${minutes % 60}分钟`
  } else if (hours > 0) {
    return `${hours}小时${minutes % 60}分钟`
  } else {
    return `${minutes}分钟`
  }
}

// 获取持续秒数
const getDurationSeconds = () => {
  if (!occupyForm.endTime) return 0
  
  const now = new Date()
  const endTime = new Date(occupyForm.endTime)
  const durationMs = endTime.getTime() - now.getTime()
  
  return Math.floor(durationMs / 1000)
}

// 获取时长类型
const getDurationType = () => {
  if (!occupyForm.endTime) return 'info'
  
  const seconds = getDurationSeconds()
  const hours = seconds / 3600
  
  if (hours <= 1) return 'danger'
  if (hours <= 4) return 'warning'
  return 'success'
}

// 获取时长标签大小
const getDurationSize = () => {
  if (!occupyForm.endTime) return ''
  
  const durationText = calculateDuration()
  if (durationText.length > 10) return 'duration-large'
  return ''
}

// 获取结束时间显示（表单用）- 统一使用 YYYY/MM/DD HH:mm:ss 格式
const getEndTimeDisplayFromForm = () => {
  if (!occupyForm.endTime) return ''
  
  const endTime = new Date(occupyForm.endTime)
  return formatDateTime(endTime)
}

// 计算电源操作对话框标题
const powerDialogTitle = computed(() => {
  const typeText = powerType.value === 'cycle' ? '冷重启' : '热重启'
  return `${typeText}服务器`
})

// 格式化网卡类型显示（适用于服务器详情页面）
const formatNicTypeForDisplay = (type: string | undefined): string => {
  if (!type) return '未知类型'
  
  const typeLower = type.toLowerCase()
  
  // 特殊处理：metaScale-200 OCP3.0 -> MS200-OCP
  if (typeLower.includes('metascale-200') && typeLower.includes('ocp3.0')) {
    return 'MS200-OCP'
  }
  
  // 其他类型按原样显示
  return type
}

// 格式化时间显示
const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  try {
    return new Date(timeStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(/\//g, '/')
  } catch (error) {
    return timeStr // 如果解析失败，返回原始字符串
  }
}

// 加载所有MV200数据
const loadAllMv200s = async () => {
  try {
    const data = await mv200Api.getAll()
    allMv200s.value = data
  } catch (error) {
    console.error('加载MV200列表失败:', error)
  }
}

// 加载启动项信息
const loadBootEntries = async () => {
  try {
    bootEntriesLoading.value = true
    const data = await deviceApi.getBootEntries(deviceId.value)
    bootEntriesData.value = data
  } catch (error) {
    console.error('加载启动项信息失败:', error)
    // 不显示错误信息，因为启动项信息不是必须的
  } finally {
    bootEntriesLoading.value = false
  }
}

// 加载服务器详情
const loadDeviceDetail = async () => {
  try {
    const data = await deviceApi.getById(deviceId.value)
    
    deviceData.value = { ...data }
    
    // 同时加载启动项信息和MV200数据
    await Promise.all([
      loadBootEntries(),
      loadAllMv200s()
    ])
  } catch (error) {
    ElMessage.error('加载服务器详情失败')
    router.push('/devices')
  }
}

// 更新服务器信息
const handleRefresh = async () => {
  try {
    refreshing.value = true
    
    await ElMessageBox.confirm(
      '确定要更新服务器信息吗？这将重新获取服务器的硬件和云脉网卡信息。',
      '确认更新',
      {
        type: 'warning',
        confirmButtonText: '确定更新',
        cancelButtonText: '取消'
      }
    )

    // 调用自动更新接口
    await deviceApi.update(deviceId.value, { auto: true })
    
    ElMessage.success('服务器信息更新成功')
    
    // 重新加载详情数据和启动项信息
    await loadDeviceDetail()
    
    // 强制重新计算 computed 属性
    deviceData.value = { ...deviceData.value }
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error(error.response?.data?.detail || '更新服务器信息失败')
  } finally {
    refreshing.value = false
  }
}

// 下拉菜单命令处理
const handleCommand = (command: string) => {
  switch (command) {
    case 'edit':
      handleEdit()
      break
    case 'bootEntry':
      handleBootEntryDialog()
      break
    case 'powerCycle':
      handlePowerOperation('cycle')
      break
    case 'powerReset':
      handlePowerOperation('reset')
      break
    case 'occupy':
      handleOccupyDialog()
      break
    case 'release':
      handleRelease()
      break
    case 'delete':
      handleDelete()
      break
  }
}

// 编辑
const handleEdit = () => {
  router.push(`/devices/edit/${deviceId.value}`)
}

// 打开占用服务器对话框
const handleOccupyDialog = () => {
  // 设置默认结束时间
  let defaultEndTime = new Date()
  defaultEndTime.setTime(defaultEndTime.getTime() + 60 * 60 * 1000) // 默认1小时后
  
  // 如果是修改模式，且设备有剩余时间，使用原剩余时间计算新的截止时间
  if (isModifyMode.value && deviceData.value.time && deviceData.value.time > 0) {
    defaultEndTime = getEndTimeFromSeconds(deviceData.value.time)
  }
  
  occupyForm.endTime = defaultEndTime
  occupyDialogVisible.value = true
}

// 占用/修改时间服务器
const handleOccupy = async () => {
  if (!occupyForm.endTime) return
  
  try {
    occupyLoading.value = true
    
    // 计算持续秒数
    const durationSeconds = getDurationSeconds()
    
    const updateData = {
      auto: false,
      time: durationSeconds, // 传持续秒数
      // user字段后端会通过token自动获取当前用户
      device: {
        ip: deviceData.value.device.ip,
        username: deviceData.value.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: deviceData.value.bmc.hostname,
        ip: deviceData.value.bmc.ip
      },
      tags: deviceData.value.tags || [],
      notes: deviceData.value.notes || '',
      os_types: deviceData.value.os_types || []
    }
    
    await deviceApi.update(deviceId.value, updateData)
    ElMessage.success(`已成功${isModifyMode.value ? '修改占用' : '占用'}服务器 ${deviceData.value.bmc.hostname}`)
    occupyDialogVisible.value = false
    loadDeviceDetail() // 重新加载数据
  } catch (error) {
    ElMessage.error(`${isModifyMode.value ? '修改占用' : '占用'}服务器失败`)
  } finally {
    occupyLoading.value = false
  }
}

// 释放占用
const handleRelease = async () => {
  if (!isDeviceOccupied.value) {
    ElMessage.warning('服务器未被占用，无法释放')
    return
  }
  
  if (!isCurrentUserOccupier.value) {
    ElMessage.warning('您不是当前占用人，无法释放该服务器')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要释放占用 "${deviceData.value.bmc.hostname}" 吗？`, 
      '确认结束', 
      {
        type: 'warning',
      }
    )

    const updateData = {
      auto: false,
      time: 0, // 设置为0表示释放占用
      // user字段后端会自动处理
      device: {
        ip: deviceData.value.device.ip,
        username: deviceData.value.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: deviceData.value.bmc.hostname,
        ip: deviceData.value.bmc.ip
      },
      tags: deviceData.value.tags || [],
      notes: deviceData.value.notes || '',
      os_types: deviceData.value.os_types || []
    }
    
    await deviceApi.update(deviceId.value, updateData)
    ElMessage.success('服务器已释放')
    loadDeviceDetail() // 重新加载数据
  } catch (error) {
    // 用户取消释放
  }
}

// 处理启动项对话框
const handleBootEntryDialog = async () => {
  selectedBootEntry.value = ''
  setAsDefaultBoot.value = false
  bootEntryDialogVisible.value = true
}

// 设置启动项
const handleSetBootEntry = async () => {
  if (!selectedBootEntry.value) return

  try {
    bootEntryLoading.value = true
    
    const bootEntryName = bootEntriesData.value?.entries[selectedBootEntry.value]
    
    await ElMessageBox.confirm(
      `确定要设置下次启动项为 "${bootEntryName}" 吗？${
        setAsDefaultBoot.value ? '同时会设置为默认启动项。' : ''
      }`,
      '确认设置启动项',
      {
        type: 'warning',
        confirmButtonText: '确定设置',
        cancelButtonText: '取消'
      }
    )

    // 调用设置启动项接口
    await deviceApi.setBootEntry(deviceId.value, selectedBootEntry.value, setAsDefaultBoot.value)
    
    ElMessage.success('启动项设置成功')
    bootEntryDialogVisible.value = false
    
    // 重置状态
    selectedBootEntry.value = ''
    setAsDefaultBoot.value = false
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      // 用户取消操作
      return
    }
    ElMessage.error(error.response?.data?.detail || '设置启动项失败')
  } finally {
    bootEntryLoading.value = false
  }
}

// 处理电源操作
const handlePowerOperation = (operation: 'cycle' | 'reset') => {
  powerType.value = operation
  powerDialogVisible.value = true
}

// 确认电源操作
const handlePowerConfirm = async () => {
  try {
    powerLoading.value = true

    if (powerType.value === 'cycle') {
      await deviceApi.powerCycle(deviceId.value)
    } else {
      await deviceApi.powerReset(deviceId.value)
    }
    const operationText = powerType.value === 'cycle' ? '冷重启' : '热重启'
    ElMessage.success(`${operationText}命令已发送`)
    powerDialogVisible.value = false
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '重启操作失败')
  } finally {
    powerLoading.value = false
  }
}

// 删除
const handleDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备 "${deviceData.value.bmc.hostname}" 吗？`, 
      '确认删除', 
      {
        type: 'warning',
      }
    )

    await deviceApi.delete(deviceId.value)
    ElMessage.success('删除成功')
    router.push('/devices')
  } catch (error) {
    // 用户取消删除
  }
}

onMounted(() => {
  deviceId.value = route.params.id as string
  if (!deviceId.value) {
    ElMessage.error('服务器ID不能为空')
    router.push('/devices')
    return
  }
  loadDeviceDetail()
})
</script>

<style scoped>
/* 关注按钮样式 */
.follow-btn {
  min-width: 80px;
}

.follow-btn:deep(.el-icon) {
  margin-right: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

/* BDF和MAC配对展示样式 */
.bdf-mac-pair {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
}

.bdf-mac-pair:last-child {
  border-bottom: none;
}

.mac-address {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  font-weight: 500;
  color: #1f2937;
}

/* 空文本样式 */
.empty-text {
  color: #9ca3af;
  font-style: italic;
}

/* SOC IP状态容器 */
.soc-ip-status {
  display: flex;
  align-items: center;
  min-height: 40px;
}

/* 错误信息样式（与MV200详情页保持一致） */
.error-info {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 4px;
  padding: 6px 8px;
  width: 100%;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  cursor: help;
  color: #f56c6c;
  justify-content: center;
}

.error-message .el-icon {
  font-size: 14px;
  flex-shrink: 0;
}

/* 匹配数量标签 */
.match-count {
  font-size: 11px;
  color: #999;
  margin-left: 2px;
}

/* SOC IP链接样式 */
.soc-ip-link {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 0;
}

.soc-ip-link :deep(.el-link) {
  display: inline-flex;
  align-items: center;
  line-height: 1.4;
  padding: 0;
  margin: 0;
  font-family: 'Monaco', 'Consolas', monospace;
  font-weight: 500;
  font-size: 12px;
}

/* 下划线链接样式 */
.underlined-link {
  text-decoration: underline !important;
  text-underline-offset: 2px;
  text-decoration-thickness: 1px;
}

.underlined-link:hover {
  text-decoration-thickness: 2px;
}

/* 并排布局样式 - 1:1:3比例 */
.info-row {
  display: flex;
  gap: 3px;
  align-items: flex-start;
}

.server-info-card {
  flex: 1.2;
  min-width: 0;
  max-width: calc(20% ); /* 1.2/6 = 20% */
}

.cpu-info-card {
  flex: 1.4;
  min-width: 0;
  max-width: calc(23% + 10px); /* 1.4/6 = 20% */
}

.nic-card {
  flex: 3.4;
  min-width: 0;
  max-width: calc(60% - 11px); /* 3.6/6 = 60% */
}

.iface-name {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
}

/* 紧凑信息列表样式 */
.compact-info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 6px;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.info-item:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.info-label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
  min-width: 30px;
}

.info-value {
  font-size: 14px;
  color: #1e293b;
  font-weight: 600;
  font-family: 'Monaco', 'Consolas', monospace;
  text-align: right;
  flex: 1;
  word-break: break-all;
}

/* 紧凑表格样式 */
.compact-table :deep(.el-table__header-wrapper th) {
  padding: 6px 0;
  font-size: 12px;
  background-color: #f8fafc;
}

.compact-table :deep(.el-table__body-wrapper td) {
  padding: 6px 0;
  font-size: 12px;
  vertical-align: top;
}

.compact-table :deep(.el-table .cell) {
  padding: 0 6px;
  line-height: 1.3;
}

.compact-table :deep(.el-table) {
  font-size: 12px;
}

.os-item {
  padding: 4px 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.current-os {
  background-color: #e6f7ff;
  border: 1px solid #91d5ff;
  color: #1890ff;
}

.default-os {
  background-color: #f6ffed;
  border: 1px solid #b7eb8f;
  color: #52c41a;
}

.loading-text {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

:deep(.el-descriptions) {
  margin-top: 20px;
}

:deep(.el-descriptions__label) {
  font-weight: 600;
}

/* 更新按钮加载状态样式 */
:deep(.el-button--warning) {
  background-color: #e6a23c;
  border-color: #e6a23c;
}

:deep(.el-button--warning:hover) {
  background-color: #e6a23c;
  border-color: #e6a23c;
  opacity: 0.8;
}

:deep(.el-button--warning:focus) {
  background-color: #e6a23c;
  border-color: #e6a23c;
}

/* 操作下拉菜单样式优化 */
:deep(.action-dropdown-menu) {
  min-width: 160px;
}

:deep(.dropdown-item) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  text-align: left !important;
}

:deep(.dropdown-item .el-dropdown-menu__item) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  padding: 8px 12px !important;
}

:deep(.dropdown-item .el-icon) {
  margin-right: 8px !important;
  flex-shrink: 0 !important;
}

:deep(.dropdown-item span) {
  flex: 1 !important;
  text-align: left !important;
}

/* 启动项按钮样式 */
:deep(.boot-entry-item:not(.is-disabled)) {
  color: #7239ea !important;
}

:deep(.boot-entry-item:not(.is-disabled):hover) {
  color: #5f2bc3 !important;
  background-color: #f8f5ff !important;
}

/* 电源操作按钮样式 */
:deep(.power-cycle-item:not(.is-disabled)) {
  color: #e6a23c !important;
}

:deep(.power-cycle-item:not(.is-disabled):hover) {
  color: #cf9236 !important;
  background-color: #fdf6ec !important;
}

:deep(.power-reset-item:not(.is-disabled)) {
  color: #f56c6c !important;
}

:deep(.power-reset-item:not(.is-disabled):hover) {
  color: #dd6161 !important;
  background-color: #fef0f0 !important;
}

/* 占用相关按钮样式优化 */
:deep(.occupy-item) {
  font-weight: 600 !important;
}

:deep(.occupy-server-item:not(.is-disabled)) {
  color: #409eff !important;
}

:deep(.occupy-server-item:not(.is-disabled):hover) {
  color: #337ecc !important;
  background-color: #f0f7ff !important;
}

:deep(.end-occupy-item:not(.is-disabled)) {
  color: #67c23a !important;
}

:deep(.end-occupy-item:not(.is-disabled):hover) {
  color: #529b2e !important;
  background-color: #f0f9eb !important;
}

:deep(.danger-item:not(.is-disabled)) {
  color: #f56c6c !important;
}

:deep(.danger-item:not(.is-disabled):hover) {
  color: #dd6161 !important;
  background-color: #fef0f0 !important;
}

/* 提示框样式 */
:deep(.el-tooltip__popper) {
  white-space: pre-line;
  max-width: 400px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.4;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .info-row {
    flex-direction: column;
  }
  
  .server-info-card,
  .cpu-info-card,
  .nic-card {
    max-width: 100%;
    width: 100%;
  }
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
    padding: 12px;
  }
  
  .info-value {
    margin-left: 0;
    text-align: left;
    width: 100%;
  }
  
  .compact-table :deep(.el-table__header-wrapper th),
  .compact-table :deep(.el-table__body-wrapper td) {
    padding: 4px 0;
  }
  
  .bdf-mac-pair {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .bdf-item {
    font-size: 10px;
  }
  
  .soc-ip-status {
    min-height: 36px;
  }
  
  .error-message {
    font-size: 11px;
    gap: 4px;
  }
  
  .match-count {
    font-size: 10px;
  }
  
  .soc-ip-link :deep(.el-link) {
    font-size: 11px;
  }
}

/* 对话框样式 - 从列表页面复制过来的样式 */
.occupy-dialog,
.boot-entry-dialog,
.power-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 20px 0;
    margin-right: 0;
  }
  
  :deep(.el-dialog__body) {
    padding: 16px 20px;
  }
  
  :deep(.el-dialog__footer) {
    padding: 0 20px 20px;
  }
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #e2e8f0;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.server-icon {
  font-size: 24px;
  color: #409eff;
}

.info-content .hostname {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.info-content .ip-address {
  font-size: 12px;
  color: #6b7280;
  font-family: 'Monaco', 'Consolas', monospace;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.username {
  font-weight: 500;
  color: #374151;
}

/* 原时间显示 */
.original-time {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fffbf0;
  border: 1px solid #fef3c7;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
  color: #92400e;
}

.original-time .el-icon {
  color: #d97706;
}

/* 表单区域 */
.form-section {
  background: white;
  border-radius: 8px;
  padding: 0;
}

/* 紧凑表单项 */
.compact-item {
  margin-bottom: 20px;
  
  :deep(.el-form-item__label) {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;
    color: #374151;
    padding-right: 12px;
  }
}

.form-label {
  font-size: 14px;
}

.required {
  color: #f56c6c;
}

.enhanced-picker {
  :deep(.el-input__wrapper) {
    border-radius: 6px;
    transition: all 0.3s ease;
    
    &:hover {
      border-color: #409eff;
      box-shadow: 0 0 0 1px #409eff;
    }
  }
  
  :deep(.el-input__inner) {
    text-align: center;
    font-weight: 500;
  }
}

/* 时长显示 */
.duration-display {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.duration-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  
  &.duration-large {
    font-size: 15px;
    padding: 10px 16px;
  }
}

.duration-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.end-time {
  color: #6b7280;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 13px;
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.cancel-btn {
  width: 100px;
}

.confirm-btn {
  width: 120px;
  font-weight: 600;
}

/* 启动项相关样式 */
.boot-entries-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.boot-selection {
  background: white;
  border-radius: 8px;
  padding: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f3f4f6;
}

.section-title .el-icon {
  color: #409eff;
}

.boot-entries-list {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
}

.boot-entry-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.boot-entry-item:last-child {
  border-bottom: none;
}

.boot-entry-item:hover {
  background-color: #f5f7fa;
}

.boot-entry-item.current-entry {
  background-color: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.boot-entry-item.selected-entry {
  background-color: #f0f7ff;
  border-left: 3px solid #409eff;
}

.boot-entry-content {
  display: flex;
  flex-direction: column;
}

.boot-entry-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.boot-radio {
  flex: 1;
  
  :deep(.el-radio__label) {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.4;
  }
}

.boot-entry-text {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.4;
}

.boot-entry-tags {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.boot-options {
  padding: 12px 0;
}

.default-boot-checkbox {
  margin-bottom: 4px;
}

.option-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 24px;
}

.no-boot-entries {
  padding: 40px 0;
}

/* 电源重启对话框样式 */
.power-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog-tip {
  margin-bottom: 8px;
}

.confirm-message {
  text-align: center;
  padding: 8px 0;
}

.confirm-message p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}

.confirm-message strong {
  color: #409eff;
}
</style>