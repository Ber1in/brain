<template>
  <div class="xsc-interface-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <el-button 
              type="primary" 
              link 
              icon="ArrowLeft"
              @click="goBack"
              style="margin-right: 16px;"
            >
              返回MV200列表
            </el-button>
            <span class="header-title">
              MV200: {{ mv200Name }} ({{ mv200Ip }}) - XSC网口管理
            </span>
          </div>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索网口名、IP地址、MAC地址、VLAN或UUID"
              clearable
              style="width: 300px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            
            <!-- 批量删除按钮 -->
            <el-button 
              type="danger" 
              @click="handleBatchDelete" 
              :disabled="selectedInterfaces.length === 0"
              style="margin-right: 12px;"
              :loading="batchDeleting"
            >
              批量删除
            </el-button>
            
            <el-button 
              type="primary" 
              @click="showCreateDialog"
              :loading="creating"
            >
              <el-icon><Plus /></el-icon>
              创建网口
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="filteredInterfaces" 
        v-loading="loading"
        :default-sort="{ prop: 'uuid', order: 'ascending' }"
        empty-text="该MV200没有配置XSC网口"
        @selection-change="handleSelectionChange"
        :row-class-name="getRowClassName"
      >
        <!-- 多选列 -->
        <el-table-column type="selection" width="40" />
        
        <el-table-column label="UUID" width="100" sortable prop="uuid">
          <template #default="{ row }">
            <el-tag 
              size="small" 
              :type="row.uuid === 0 ? 'warning' : 'primary'"
              :class="{ 'pxe-uuid': row.uuid === 0, 'deleting-cell': row.deletingAnimation }"
            >
              {{ row.uuid }}
              <el-tooltip v-if="row.uuid === 0" content="PXE专用网口" placement="top">
                <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
              </el-tooltip>
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="网口名称" prop="ifname" width="150">
          <template #default="{ row }">
            <span 
              class="interface-name"
              :class="{ 'deleting-cell': row.deletingAnimation }"
            >
              {{ row.ifname || '-' }}
            </span>
          </template>
        </el-table-column>
        
        <el-table-column label="IP地址" width="200">
          <template #default="{ row }">
            <div v-if="row.ip" class="ip-info">
              <span class="ip-address">{{ row.ip }}</span>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>

        <el-table-column label="MAC地址" width="160" sortable prop="mac">
          <template #default="{ row }">
            <span class="mac-address">{{ row.mac || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="VLAN" width="100" sortable prop="vlan">
          <template #default="{ row }">
            <el-tag v-if="row.vlan" size="small" type="info">
              {{ row.vlan }}
            </el-tag>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="MTU" width="100" sortable prop="mtu">
          <template #default="{ row }">
            <span class="mtu-value">{{ row.mtu || 1500 }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="网关" width="150">
          <template #default="{ row }">
            <span>{{ row.gateway || '-' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="DHCP服务器" width="180">
          <template #default="{ row }">
            <span>{{ row.dhcp_server || '-' }}</span>
          </template>
        </el-table-column>
        
        <el-table-column label="DNS服务器" width="180">
          <template #default="{ row }">
            <div v-if="row.dns && row.dns.length > 0" class="dns-list">
              <div v-for="(dns, index) in row.dns.slice(0, 2)" :key="index" class="dns-item">
                <span class="dns-ip">{{ dns }}</span>
              </div>
              <div v-if="row.dns.length > 2" class="dns-more">
                +{{ row.dns.length - 2 }} more
              </div>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" fixed="right">
          <template #default="{ row }">
            <el-dropdown 
              @command="(command) => handleCommand(command, row)" 
              size="small"
              :disabled="row.deleting"
            >
              <el-button type="primary" link :disabled="row.deleting">
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu class="action-dropdown-menu">
                  <el-dropdown-item 
                    command="detail" 
                    class="dropdown-item"
                    :disabled="row.deleting"
                  >
                    <div class="dropdown-item-content">
                      <el-icon><View /></el-icon>
                      <span>详情</span>
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item 
                    command="config" 
                    divided 
                    class="dropdown-item"
                    :disabled="row.deleting"
                  >
                    <div class="dropdown-item-content">
                      <el-icon><Setting /></el-icon>
                      <span>{{ row.vlan ? '清理配置' : '配置网口' }}</span>
                      <el-tooltip 
                        v-if="row.vlan"
                        effect="dark" 
                        content="该网口已有配置，点击清理现有配置"
                        placement="top"
                      >
                        <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                      </el-tooltip>
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item 
                    command="delete" 
                    divided 
                    class="danger-item dropdown-item"
                    :disabled="row.deleting"
                  >
                    <div class="dropdown-item-content">
                      <el-icon v-if="!row.deleting"><Delete /></el-icon>
                      <el-icon v-else class="loading-icon"><Loading /></el-icon>
                      <span>{{ row.deleting ? '删除中...' : '删除网口' }}</span>
                    </div>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <!-- 创建网口对话框 -->
      <el-dialog
        v-model="createDialogVisible"
        title="创建XSC网口"
        width="550px"
        :close-on-click-modal="false"
        class="custom-dialog"
      >
        <el-form
          ref="createFormRef"
          :model="createForm"
          :rules="createRules"
          label-width="120px"
          v-loading="creating"
          class="custom-form"
        >
          <el-form-item label="PXE专用口" prop="pxe">
            <el-switch
              v-model="createForm.pxe"
              active-text="是"
              inactive-text="否"
              @change="handlePxeChange"
            />
            <div class="form-tip">PXE专用口用于网络启动，默认为否</div>
          </el-form-item>
          
          <el-form-item label="UUID" prop="uuid">
            <el-input
              v-model="createForm.uuid"
              :placeholder="createForm.pxe ? '0（PXE专用口）' : '自定义UUID'"
              type="number"
              :min="createForm.pxe ? 0 : 1"
              :max="63"
              :disabled="createForm.pxe"
              clearable
              style="width: 200px;"
            >
              <template #append>
                <el-tooltip :content="createForm.pxe ? 'PXE专用口UUID固定为0' : '建议不填写，由系统自动分配唯一UUID'">
                  <el-icon><InfoFilled /></el-icon>
                </el-tooltip>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="MAC地址" prop="mac">
            <el-input
              v-model="createForm.mac"
              placeholder="自定义mac，如AA:BB:CC:DD:EE:FF"
              clearable
              style="width: 250px;"
              @input="validateMacAddress"
            />
            <div v-if="macError" class="error-tip">{{ macError }}</div>
          </el-form-item>
          
          <el-form-item label="MTU" prop="mtu">
            <el-input-number
              v-model="createForm.mtu"
              :min="576"
              :max="9000"
              :step="1"
              style="width: 200px;"
            />
          </el-form-item>
          
          <el-form-item label="VQ Count" prop="vq_count">
            <el-input-number
              v-model="createForm.vq_count"
              :min="1"
              :max="16"
              :step="1"
              style="width: 200px;"
            />
          </el-form-item>
          
          <el-form-item label="VQ Size" prop="vq_size">
            <el-input-number
              v-model="createForm.vq_size"
              :min="256"
              :max="4096"
              :step="256"
              style="width: 200px;"
            />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <el-button @click="createDialogVisible = false" :disabled="creating">
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handleCreateAndConfig"
            :loading="creating"
          >
            下一步
          </el-button>
        </template>
      </el-dialog>

      <!-- 配置网口对话框 -->
      <el-dialog
        v-model="configDialogVisible"
        :title="`配置XSC网口 - UUID: ${selectedInterface?.uuid}`"
        width="600px"
        :close-on-click-modal="false"
        class="custom-dialog"
      >
        <el-form
          ref="configFormRef"
          :model="configForm"
          :rules="configRules"
          label-width="120px"
          v-loading="configuring"
          class="custom-form"
        >
          <el-form-item label="IP地址/掩码" prop="ip" required>
            <div class="ip-input-group">
              <div class="ip-segments">
                <el-input
                  ref="ipInput1"
                  v-model="ipSegments[0]"
                  placeholder=""
                  maxlength="3"
                  @input="validateIpSegment(0, $event)"
                  @blur="combineConfigIP"
                  @paste="handleIpPaste"
                  @keydown="(e) => handleKeydown(e, 0, 'ip')"
                  style="width: 60px; text-align: center;"
                />
                <span class="ip-dot">.</span>
                <el-input
                  ref="ipInput2"
                  v-model="ipSegments[1]"
                  placeholder=""
                  maxlength="3"
                  @input="validateIpSegment(1, $event)"
                  @keydown="(e) => handleKeydown(e, 1, 'ip')" 
                  @blur="combineConfigIP"
                  style="width: 60px; text-align: center;"
                />
                <span class="ip-dot">.</span>
                <el-input
                  ref="ipInput3"
                  v-model="ipSegments[2]"
                  placeholder=""
                  maxlength="3"
                  @input="validateIpSegment(2, $event)"
                  @keydown="(e) => handleKeydown(e, 2, 'ip')"
                  @blur="combineConfigIP"
                  style="width: 60px; text-align: center;"
                />
                <span class="ip-dot">.</span>
                <el-input
                  ref="ipInput4"
                  v-model="ipSegments[3]"
                  placeholder=""
                  maxlength="3"
                  @input="validateIpSegment(3, $event)"
                  @keydown="(e) => handleKeydown(e, 3, 'ip')" 
                  @blur="combineConfigIP"
                  style="width: 60px; text-align: center;"
                />
              </div>
              <span style="margin: 0 8px;">/</span>
              <el-input-number
                v-model="configSubnetMask"
                :min="0"
                :max="32"
                placeholder="掩码"
                style="width: 100px;"
                @blur="combineConfigIP"
              />
            </div>
            <div class="form-tip">例: 192.168.10.101/24</div>
          </el-form-item>
          
          <el-form-item label="VLAN ID" prop="vlan_tag" required>
            <el-input-number
              v-model="configForm.vlan_tag"
              :min="1"
              :max="4094"
              placeholder="输入VLAN ID"
              style="width: 200px;"
              :controls="false"
            />
          </el-form-item>
          
          <el-form-item label="网关" prop="gateway">
            <div class="ip-segments">
              <el-input
                ref="gatewayInput1"
                v-model="gatewaySegments[0]"
                placeholder=""
                maxlength="3"
                @input="validateGatewaySegment(0, $event)"
                @keydown="(e) => handleKeydown(e, 0, 'gateway')" 
                @blur="combineConfigGateway"
                @paste="handleGatewayPaste"
                style="width: 60px; text-align: center;"
              />
              <span class="ip-dot">.</span>
              <el-input
                ref="gatewayInput2"
                v-model="gatewaySegments[1]"
                placeholder=""
                maxlength="3"
                @input="validateGatewaySegment(1, $event)"
                @keydown="(e) => handleKeydown(e, 1, 'gateway')" 
                @blur="combineConfigGateway"
                style="width: 60px; text-align: center;"
              />
              <span class="ip-dot">.</span>
              <el-input
                ref="gatewayInput3"
                v-model="gatewaySegments[2]"
                placeholder=""
                maxlength="3"
                @input="validateGatewaySegment(2, $event)"
                @keydown="(e) => handleKeydown(e, 2, 'gateway')" 
                @blur="combineConfigGateway"
                style="width: 60px; text-align: center;"
              />
              <span class="ip-dot">.</span>
              <el-input
                ref="gatewayInput4"
                v-model="gatewaySegments[3]"
                placeholder=""
                maxlength="3"
                @input="validateGatewaySegment(3, $event)"
                @keydown="(e) => handleKeydown(e, 3, 'gateway')" 
                @blur="combineConfigGateway"
                style="width: 60px; text-align: center;"
              />
            </div>
          </el-form-item>
          
          <el-form-item label="DHCP服务器" prop="dhcp_server">
            <div class="ip-segments">
              <el-input
                ref="dhcpInput1"
                v-model="dhcpSegments[0]"
                placeholder=""
                maxlength="3"
                @input="validateDhcpSegment(0, $event)"
                @keydown="(e) => handleKeydown(e, 0, 'dhcp')" 
                @blur="combineConfigDhcp"
                @paste="handleDhcpPaste"
                style="width: 60px; text-align: center;"
              />
              <span class="ip-dot">.</span>
              <el-input
                ref="dhcpInput2"
                v-model="dhcpSegments[1]"
                placeholder=""
                maxlength="3"
                @input="validateDhcpSegment(1, $event)"
                @keydown="(e) => handleKeydown(e, 1, 'dhcp')" 
                @blur="combineConfigDhcp"
                style="width: 60px; text-align: center;"
              />
              <span class="ip-dot">.</span>
              <el-input
                ref="dhcpInput3"
                v-model="dhcpSegments[2]"
                placeholder=""
                maxlength="3"
                @input="validateDhcpSegment(2, $event)"
                @keydown="(e) => handleKeydown(e, 2, 'dhcp')" 
                @blur="combineConfigDhcp"
                style="width: 60px; text-align: center;"
              />
              <span class="ip-dot">.</span>
              <el-input
                ref="dhcpInput4"
                v-model="dhcpSegments[3]"
                placeholder=""
                maxlength="3"
                @input="validateDhcpSegment(3, $event)"
                @keydown="(e) => handleKeydown(e, 3, 'dhcp')" 
                @blur="combineConfigDhcp"
                style="width: 60px; text-align: center;"
              />
            </div>
          </el-form-item>
          
          <el-form-item label="DNS服务器" prop="dns">
            <div class="dns-input-group">
              <div v-for="(dns, dnsIndex) in dnsList" :key="dnsIndex" class="dns-item">
                <div class="ip-segments">
                  <el-input
                    :ref="el => setDnsInputRef(dnsIndex, 0, el)"
                    v-model="dnsList[dnsIndex][0]"
                    placeholder=""
                    maxlength="3"
                    @input="validateDnsSegment(dnsIndex, 0, $event)"
                    @keydown="(e) => handleKeydown(e, 0, 'dns', dnsIndex)"
                    @blur="combineConfigDns(dnsIndex)"
                    @paste="(e) => handleDnsPaste(dnsIndex, e)"
                    style="width: 60px; text-align: center;"
                  />
                  <span class="ip-dot">.</span>
                  <el-input
                    :ref="el => setDnsInputRef(dnsIndex, 1, el)"
                    v-model="dnsList[dnsIndex][1]"
                    placeholder=""
                    maxlength="3"
                    @input="validateDnsSegment(dnsIndex, 1, $event)"
                    @keydown="(e) => handleKeydown(e, 1, 'dns', dnsIndex)"
                    @blur="combineConfigDns(dnsIndex)"
                    style="width: 60px; text-align: center;"
                  />
                  <span class="ip-dot">.</span>
                  <el-input
                    :ref="el => setDnsInputRef(dnsIndex, 2, el)"
                    v-model="dnsList[dnsIndex][2]"
                    placeholder=""
                    maxlength="3"
                    @input="validateDnsSegment(dnsIndex, 2, $event)"
                    @keydown="(e) => handleKeydown(e, 2, 'dns', dnsIndex)"
                    @blur="combineConfigDns(dnsIndex)"
                    style="width: 60px; text-align: center;"
                  />
                  <span class="ip-dot">.</span>
                  <el-input
                    :ref="el => setDnsInputRef(dnsIndex, 3, el)"
                    v-model="dnsList[dnsIndex][3]"
                    placeholder=""
                    maxlength="3"
                    @input="validateDnsSegment(dnsIndex, 3, $event)"
                    @keydown="(e) => handleKeydown(e, 3, 'dns', dnsIndex)"
                    @blur="combineConfigDns(dnsIndex)"
                    style="width: 60px; text-align: center;"
                  />
                </div>
                <el-button
                  type="warning"
                  link
                  :icon="Delete"
                  @click="removeConfigDns(dnsIndex)"
                  :disabled="dnsList.length === 1"
                  style="margin-left: 12px;"
                />
              </div>
              <el-button
                type="primary"
                link
                :icon="Plus"
                @click="addConfigDns"
              >
                添加DNS
              </el-button>
            </div>
            <div class="form-tip">可添加多个DNS服务器</div>
          </el-form-item>
          
          <el-form-item label="当前MAC">
            <el-input
              :value="selectedInterface?.mac"
              disabled
              style="width: 250px;"
            />
          </el-form-item>
        </el-form>
        
        <template #footer>
          <el-button 
            @click="configDialogVisible = false" 
            :disabled="configuring"
          >
            {{ isCreatingMode ? '稍后配置' : '取消' }}
          </el-button>
          <el-button 
            type="primary" 
            @click="handleConfig" 
            :loading="configuring"
          >
            配置
          </el-button>
        </template>
      </el-dialog>

      <!-- 详情对话框 -->
      <el-dialog
        v-model="detailDialogVisible"
        :title="`XSC网口详情 - UUID: ${selectedInterface?.uuid}`"
        width="600px"
      >
        <div v-if="selectedInterface" class="interface-detail">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="UUID">
              <el-tag size="small" :type="selectedInterface.uuid === 0 ? 'warning' : 'primary'">
                {{ selectedInterface.uuid }}
                <el-tooltip v-if="selectedInterface.uuid === 0" content="PXE专用网口" placement="top">
                  <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                </el-tooltip>
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="网口名称">
              {{ selectedInterface.ifname || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="MAC地址">
              <span class="mac-address">{{ selectedInterface.mac }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="IP地址">
              <div v-if="selectedInterface.ip" class="ip-info">
                <span class="ip-address">{{ getIpOnly(selectedInterface.ip) }}</span>
                <span v-if="selectedInterface.ip.includes('/')" class="netmask">
                  /{{ selectedInterface.ip.split('/')[1] }}
                </span>
              </div>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="网关">
              {{ selectedInterface.gateway || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="VLAN">
              <el-tag v-if="selectedInterface.vlan" size="small" type="info">
                {{ selectedInterface.vlan }}
              </el-tag>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="MTU">
              {{ selectedInterface.mtu || 1500 }}
            </el-descriptions-item>
            <el-descriptions-item label="DHCP服务器">
              {{ selectedInterface.dhcp_server || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="DNS服务器">
              <div v-if="selectedInterface.dns && selectedInterface.dns.length > 0" class="dns-list-full">
                <div v-for="(dns, index) in selectedInterface.dns" :key="index" class="dns-item">
                  <span class="dns-ip">{{ dns }}</span>
                </div>
              </div>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="PXE专用">
              <el-tag v-if="selectedInterface.pxe || selectedInterface.uuid === 0" type="warning" size="small">是</el-tag>
              <el-tag v-else type="info" size="small">否</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="VQ Count">
              {{ selectedInterface.vq_count || 2 }}
            </el-descriptions-item>
            <el-descriptions-item label="VQ Size">
              {{ selectedInterface.vq_size || 512 }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag v-if="selectedInterface.ip" type="success" size="small">已配置</el-tag>
              <el-tag v-else type="info" size="small">未配置</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>
        <template #footer>
          <el-button @click="detailDialogVisible = false">关闭</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { 
  ArrowLeft, 
  Search, 
  MoreFilled, 
  View,
  Setting,
  Delete,
  Plus,
  InfoFilled,
  Loading
} from '@element-plus/icons-vue'
import { mv200Api } from '@/api/mv200'
import { networkApi } from '@/api/network'
import type { XscnetInfo, InterfaceCreate, OvsflowRequest } from '@/types/api'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const creating = ref(false)
const configuring = ref(false)
const batchDeleting = ref(false)
const xscInterfaces = ref<(XscnetInfo & { deleting?: boolean })[]>([])
const selectedInterfaces = ref<(XscnetInfo & { deleting?: boolean })[]>([])
const searchKeyword = ref('')
const detailDialogVisible = ref(false)
const createDialogVisible = ref(false)
const configDialogVisible = ref(false)
const selectedInterface = ref<(XscnetInfo & { deleting?: boolean }) | null>(null)
const createFormRef = ref<FormInstance>()
const configFormRef = ref<FormInstance>()

const isCreatingMode = ref(false)

// MAC地址错误提示
const macError = ref('')

// 配置弹窗相关
const ipSegments = ref(['', '', '', ''])
const gatewaySegments = ref(['', '', '', ''])
const dhcpSegments = ref(['', '', '', ''])
const dnsList = ref<string[][]>([['', '', '', '']])
const configSubnetMask = ref(24)

// Refs for inputs
const ipInput1 = ref()
const ipInput2 = ref()
const ipInput3 = ref()
const ipInput4 = ref()
const gatewayInput1 = ref()
const gatewayInput2 = ref()
const gatewayInput3 = ref()
const gatewayInput4 = ref()
const dhcpInput1 = ref()
const dhcpInput2 = ref()
const dhcpInput3 = ref()
const dhcpInput4 = ref()
const dnsInputRefs = ref<Record<string, any>>({})

// 安全获取query参数
const getSafeQueryParam = (param: string, defaultValue = '') => {
  const value = route.query[param]
  if (typeof value === 'string' && value) {
    try {
      return decodeURIComponent(value)
    } catch (error) {
      console.warn(`Failed to decode query param ${param}:`, error)
      return value
    }
  }
  return defaultValue
}

// 从路由参数中获取MV200信息
const mv200Id = computed(() => route.params.mv200_id as string)
const mv200Name = computed(() => getSafeQueryParam('name', '未知MV200'))
const mv200Ip = computed(() => getSafeQueryParam('ip', '未知IP'))

// 创建表单数据
const createForm = ref({
  pxe: false,
  mac: '',
  mtu: 1500,
  uuid: undefined as number | undefined,
  vq_count: 2,
  vq_size: 512
})

// 配置表单数据
const configForm = ref<OvsflowRequest>({
  ip: '',
  vlan_tag: 0,
  gateway: '',
  dhcp_server: '',
  dns: []
})

// 获取已存在的UUID列表
const getExistingUuids = () => {
  const uuids = xscInterfaces.value.map(intf => intf.uuid).sort((a, b) => a - b)
  return uuids.length > 0 ? uuids.join(', ') : '无'
}

// 创建表单验证规则
const createRules: FormRules = {
  vq_count: [
    { required: true, message: '请输入VQ Count', trigger: 'blur' },
    { type: 'number', min: 1, max: 16, message: 'VQ Count范围1-16', trigger: 'blur' }
  ],
  vq_size: [
    { required: true, message: '请输入VQ Size', trigger: 'blur' },
    { type: 'number', min: 256, max: 4096, message: 'VQ Size范围256-4096', trigger: 'blur' }
  ],
  mtu: [
    { type: 'number', min: 576, max: 9000, message: 'MTU范围576-9000', trigger: 'blur' }
  ],
  uuid: [
    { 
      type: 'number', 
      min: 0, // 允许0（PXE专用）
      max: 100, 
      message: 'UUID范围0-100', 
      trigger: 'blur',
      validator: (rule, value, callback) => {
        if (value === '' || value === undefined || value === null) {
          callback() // 允许为空
        } else {
          const numValue = Number(value)
          if (isNaN(numValue)) {
            callback(new Error('请输入有效数字'))
          } else if (numValue < 0 || numValue > 100) {
            callback(new Error('UUID范围0-100（0为PXE专用）'))
          } else if (numValue === 0 && createForm.value.pxe === false) {
            callback(new Error('UUID=0只能用于PXE专用网口，请勾选PXE专用'))
          } else {
            // 检查是否已存在该UUID
            const exists = xscInterfaces.value.some(intf => intf.uuid === numValue)
            if (exists) {
              callback(new Error(`UUID ${numValue} 已存在，请选择其他UUID`))
            } else {
              callback()
            }
          }
        }
      }
    }
  ],
  mac: [
    { 
      validator: (rule, value, callback) => {
        if (!value || value.trim() === '') {
          callback() // 允许为空
        } else {
          const macPattern = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/
          if (!macPattern.test(value.trim())) {
            callback(new Error('MAC地址格式不正确，如AA:BB:CC:DD:EE:FF'))
          } else {
            callback()
          }
        }
      },
      trigger: 'blur'
    }
  ]
}

// MAC地址实时验证
const validateMacAddress = () => {
  if (!createForm.value.mac || createForm.value.mac.trim() === '') {
    macError.value = ''
    return
  }
  
  const macPattern = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/
  if (!macPattern.test(createForm.value.mac)) {
    macError.value = 'MAC地址格式不正确，请使用 XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX 格式，不区分大小写'
  } else {
    macError.value = ''
  }
}

// IP地址验证函数（用于配置表单）
const validateIP = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入IP地址和掩码'))
    return
  }
  
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
  if (!ipPattern.test(value)) {
    callback(new Error('请输入有效的IP地址格式，如：192.168.1.100/24'))
    return
  }
  
  const [ip, mask] = value.split('/')
  const maskNum = parseInt(mask)
  
  if (maskNum < 0 || maskNum > 32) {
    callback(new Error('子网掩码必须在0-32之间'))
    return
  }
  
  const parts = ip.split('.')
  for (const part of parts) {
    const num = parseInt(part)
    if (num < 0 || num > 255) {
      callback(new Error('IP地址每个数字段应在0-255之间'))
      return
    }
  }
  
  callback()
}

// 网关验证
const validateGateway = (rule: any, value: string, callback: any) => {
  // 如果网关为空，直接通过验证
  if (value === undefined || value === '') {
    callback()
    return
  }
  
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipPattern.test(value)) {
    callback(new Error('请输入有效的网关地址格式'))
    return
  }
  
  const parts = value.split('.')
  for (const part of parts) {
    const num = parseInt(part)
    if (num < 0 || num > 255) {
      callback(new Error('网关地址每个数字段应在0-255之间'))
      return
    }
  }
  
  callback()
}

// DHCP服务器验证
const validateDhcpServer = (rule: any, value: string, callback: any) => {
  // 如果DHCP服务器为空，直接通过验证
  if (value === undefined || value === '') {
    callback()
    return
  }
  
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
  if (!ipPattern.test(value)) {
    callback(new Error('请输入有效的DHCP服务器地址格式'))
    return
  }
  
  const parts = value.split('.')
  for (const part of parts) {
    const num = parseInt(part)
    if (num < 0 || num > 255) {
      callback(new Error('DHCP服务器地址每个数字段应在0-255之间'))
      return
    }
  }
  
  callback()
}

// 配置表单验证规则
const configRules: FormRules = {
  ip: [
    { required: true, validator: validateIP, trigger: 'blur' }
  ],
  vlan_tag: [
    { required: true, message: '请输入VLAN ID', trigger: 'blur' },
    { type: 'number', min: 1, max: 4094, message: 'VLAN ID范围1-4094', trigger: 'blur' }
  ],
  gateway: [
    { validator: validateGateway, trigger: 'blur' }
  ],
  dhcp_server: [
    { validator: validateDhcpServer, trigger: 'blur' }
  ]
}

// 计算属性：过滤后的网口列表
const filteredInterfaces = computed(() => {
  if (!searchKeyword.value.trim()) {
    return xscInterfaces.value
  }
  
  const keyword = searchKeyword.value.toLowerCase().trim()
  return xscInterfaces.value.filter(intf => {
    // 搜索UUID
    if (intf.uuid.toString().includes(keyword)) return true
    
    // 搜索网口名
    if (intf.ifname && intf.ifname.toLowerCase().includes(keyword)) return true
    
    // 搜索MAC地址
    if (intf.mac && intf.mac.toLowerCase().includes(keyword)) return true
    
    // 搜索IP地址
    if (intf.ip && intf.ip.toLowerCase().includes(keyword)) return true
    
    // 搜索网关
    if (intf.gateway && intf.gateway.toLowerCase().includes(keyword)) return true
    
    // 搜索VLAN
    if (intf.vlan && intf.vlan.toString().includes(keyword)) return true
    
    // 搜索DNS
    if (intf.dns && intf.dns.some(dns => dns.toLowerCase().includes(keyword))) return true
    
    return false
  })
})

// 加载XSC网口数据
const loadXscInterfaces = async () => {
  loading.value = true
  try {
    if (!mv200Id.value) {
      ElMessage.error('无效的MV200 ID')
      router.push('/mv200')
      return
    }

    xscInterfaces.value = await mv200Api.getAllXsc(mv200Id.value)
    
    // 如果有数据，按UUID排序
    if (xscInterfaces.value.length > 0) {
      xscInterfaces.value.sort((a, b) => a.uuid - b.uuid)
    }
  } catch (error: any) {
    console.error('加载XSC网口失败:', error)
    
    if (error.response?.status === 404) {
      ElMessage.error('未找到指定的MV200或XSC网口')
    } else if (error.response?.status === 500) {
      ElMessage.error('服务器内部错误，请稍后重试')
    } else {
      ElMessage.error('加载XSC网口失败，请检查网络连接')
    }
  } finally {
    loading.value = false
  }
}

// 获取IP地址部分（去除掩码）
const getIpOnly = (ipWithMask: string) => {
  if (!ipWithMask) return ''
  const [ip] = ipWithMask.split('/')
  return ip
}

// 处理多选变化
const handleSelectionChange = (selection: (XscnetInfo & { deleting?: boolean })[]) => {
  selectedInterfaces.value = selection
}

const getRowClassName = ({ row }: { row: XscnetInfo & { deleting?: boolean; deletingAnimation?: boolean } }) => {
  const classes = []
  if (row.deletingAnimation) {
    classes.push('deleting-row')
  }
  return classes.join(' ')
}

// 批量删除
const handleBatchDelete = async () => {
  if (selectedInterfaces.value.length === 0) return

  try {
    const uuids = selectedInterfaces.value.map(intf => intf.uuid).join(', ')
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedInterfaces.value.length} 个XSC网口吗？\nUUID: ${uuids}`, 
      '确认批量删除', 
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger'
      }
    )

    batchDeleting.value = true
    
    // 保存副本并清空选择
    const interfacesToDelete = [...selectedInterfaces.value]
    selectedInterfaces.value = []
    
    const failedUuids: number[] = []
    let completedCount = 0
    
    // 逐个执行删除
    for (let i = 0; i < interfacesToDelete.length; i++) {
      const intf = interfacesToDelete[i]
      
      try {
        // 设置删除状态
        intf.deleting = true
        intf.deletingAnimation = true
        
        // 执行删除
        await mv200Api.deleteXsc(mv200Id.value, intf.uuid)
        
        // 删除成功后立即从本地列表中移除
        const index = xscInterfaces.value.findIndex(item => item.uuid === intf.uuid)
        if (index !== -1) {
          xscInterfaces.value.splice(index, 1)
        }
        
        completedCount++
        
        // 短暂延迟让用户能看到进度
        if (i < interfacesToDelete.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 200))
        }
        
      } catch (error) {
        console.error(`删除网口 UUID: ${intf.uuid} 失败:`, error)
        failedUuids.push(intf.uuid)
        
        // 重置删除状态（失败后恢复）
        intf.deleting = false
        intf.deletingAnimation = false
        
        // 确保这个网口还在列表中（如果之前被移除了）
        const exists = xscInterfaces.value.some(item => item.uuid === intf.uuid)
        if (!exists) {
          xscInterfaces.value.push(intf)
          xscInterfaces.value.sort((a, b) => a.uuid - b.uuid)
        }
      }
    }
    
    // 显示最终结果
    const successCount = interfacesToDelete.length - failedUuids.length
    if (successCount > 0) {
      ElMessage.success(`成功删除 ${successCount} 个XSC网口`)
    }
    
    if (failedUuids.length > 0) {
      ElMessage.warning(`以下网口删除失败: ${failedUuids.join(', ')}`)
    }
    
    // 最终同步一次数据
    await loadXscInterfaces()
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败，请重试')
    }
  } finally {
    batchDeleting.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理
}

// 处理操作命令
const handleCommand = (command: string, intf: XscnetInfo & { deleting?: boolean }) => {
  switch (command) {
    case 'detail':
      handleDetail(intf)
      break
    case 'config':
      // 根据是否有vlan决定是清理配置还是新增配置
      if (intf.vlan) {
        handleCleanConfig(intf)
      } else {
        handleConfigDialog(intf)
      }
      break
    case 'delete':
      handleDelete(intf)
      break
  }
}

// 清理配置（删除流表）
const handleCleanConfig = async (intf: XscnetInfo & { deleting?: boolean }) => {
  try {
    await ElMessageBox.confirm(
      `确定要清理网口 UUID: ${intf.uuid} 的配置吗？\n这将删除所有流表配置。`,
      '确认清理配置',
      {
        type: 'warning',
        confirmButtonText: '确定清理',
        cancelButtonText: '取消'
      }
    )
    
    // 调用删除流表接口
    await mv200Api.removeXscOvsFlow(mv200Id.value, intf.uuid)
    
    ElMessage.success(`网口 UUID: ${intf.uuid} 配置已清理`)
    
    // 重新加载数据
    await loadXscInterfaces()
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清理配置失败，请重试')
    }
  }
}

// 查看详情
const handleDetail = (intf: XscnetInfo) => {
  selectedInterface.value = intf
  detailDialogVisible.value = true
}

// 显示创建对话框
const showCreateDialog = () => {
  createForm.value = {
    pxe: false,
    mac: '',
    mtu: 1500,
    uuid: undefined,
    vq_count: 2,
    vq_size: 512
  }
  macError.value = ''
  createDialogVisible.value = true
  nextTick(() => {
    createFormRef.value?.clearValidate()
  })
}

// 设置DNS输入框ref
const setDnsInputRef = (dnsIndex: number, segmentIndex: number, el: any) => {
  if (el) {
    dnsInputRefs.value[`dns_${dnsIndex}_${segmentIndex}`] = el
  }
}

// IP地址相关的处理方法
const validateIpSegment = (index: number, value: string) => {
  let cleanValue = value.replace(/[^\d]/g, '')
  ipSegments.value[index] = cleanValue
}

const validateGatewaySegment = (index: number, value: string) => {
  let cleanValue = value.replace(/[^\d]/g, '')
  gatewaySegments.value[index] = cleanValue
}

const validateDhcpSegment = (index: number, value: string) => {
  let cleanValue = value.replace(/[^\d]/g, '')
  dhcpSegments.value[index] = cleanValue
}

const validateDnsSegment = (dnsIndex: number, segmentIndex: number, value: string) => {
  let cleanValue = value.replace(/[^\d]/g, '')
  dnsList.value[dnsIndex][segmentIndex] = cleanValue
}

// 解析并设置IP地址
const parseAndSetIp = async (text: string, segments: string[], type: 'ip' | 'gateway' | 'dhcp' | 'dns', dnsIndex?: number) => {
  text = text.trim()
  
  const ipRegex = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/
  const match = text.match(ipRegex)
  
  if (match) {
    segments[0] = match[1]
    segments[1] = match[2]
    segments[2] = match[3]
    segments[3] = match[4]
    
    await nextTick()
    
    if (type === 'ip') {
      combineConfigIP()
    } else if (type === 'gateway') {
      combineConfigGateway()
    } else if (type === 'dhcp') {
      combineConfigDhcp()
    } else if (type === 'dns' && dnsIndex !== undefined) {
      combineConfigDns(dnsIndex)
    }
  } else {
    ElMessage.warning('粘贴的内容不是有效的IP地址格式，请使用 xxx.xxx.xxx.xxx 格式')
  }
}

// 处理粘贴事件
const handleIpPaste = async (event: ClipboardEvent) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  await parseAndSetIp(pastedText, ipSegments.value, 'ip')
}

const handleGatewayPaste = async (event: ClipboardEvent) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  await parseAndSetIp(pastedText, gatewaySegments.value, 'gateway')
}

const handleDhcpPaste = async (event: ClipboardEvent) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  await parseAndSetIp(pastedText, dhcpSegments.value, 'dhcp')
}

const handleDnsPaste = async (dnsIndex: number, event: ClipboardEvent) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  await parseAndSetIp(pastedText, dnsList.value[dnsIndex], 'dns', dnsIndex)
}

// 组合IP地址
const combineConfigIP = () => {
  const ip = ipSegments.value.join('.')
  if (ip && configSubnetMask.value !== null && ip !== '...') {
    configForm.value.ip = `${ip}/${configSubnetMask.value}`
  } else {
    configForm.value.ip = ''
  }
}

const combineConfigGateway = () => {
  const gateway = gatewaySegments.value.join('.')
  if (gateway && gateway !== '...') {
    configForm.value.gateway = gateway
  } else {
    configForm.value.gateway = ''
  }
}

const combineConfigDhcp = () => {
  const dhcp = dhcpSegments.value.join('.')
  if (dhcp && dhcp !== '...') {
    configForm.value.dhcp_server = dhcp
  } else {
    configForm.value.dhcp_server = ''
  }
}

const combineConfigDns = (dnsIndex: number) => {
  const dns = dnsList.value[dnsIndex].join('.')
  if (dns && dns !== '...') {
    configForm.value.dns[dnsIndex] = dns
  } else {
    configForm.value.dns[dnsIndex] = ''
  }
}

// 键盘事件处理
const handleKeydown = (event: KeyboardEvent, index: number, type: 'ip' | 'gateway' | 'dhcp' | 'dns', dnsIndex?: number) => {
  if (event.key === '.' || event.key === 'Period') {
    event.preventDefault()
    
    if (type === 'ip') {
      if (index < 3) {
        const nextInput = [ipInput2, ipInput3, ipInput4][index]
        if (nextInput.value) {
          nextInput.value.focus()
        }
      }
    } else if (type === 'gateway') {
      if (index < 3) {
        const nextInput = [gatewayInput2, gatewayInput3, gatewayInput4][index]
        if (nextInput.value) {
          nextInput.value.focus()
        }
      }
    } else if (type === 'dhcp') {
      if (index < 3) {
        const nextInput = [dhcpInput2, dhcpInput3, dhcpInput4][index]
        if (nextInput.value) {
          nextInput.value.focus()
        }
      }
    } else if (type === 'dns' && dnsIndex !== undefined) {
      if (index < 3) {
        const nextInput = dnsInputRefs.value[`dns_${dnsIndex}_${index + 1}`]
        if (nextInput) {
          nextInput.focus()
        }
      }
    }
  }
}

// 配置弹窗的DNS操作
const addConfigDns = () => {
  dnsList.value.push(['', '', '', ''])
  configForm.value.dns.push('')
}

const removeConfigDns = (index: number) => {
  if (dnsList.value.length > 1) {
    dnsList.value.splice(index, 1)
    configForm.value.dns.splice(index, 1)
  }
}

// 显示配置对话框
const handleConfigDialog = (intf: XscnetInfo) => {
  selectedInterface.value = intf
  
  // 重置所有输入框
  ipSegments.value = ['', '', '', '']
  gatewaySegments.value = ['', '', '', '']
  dhcpSegments.value = ['', '', '', '']
  dnsList.value = [['', '', '', '']]
  configSubnetMask.value = 24
  
  // 如果已有配置，填充数据
  if (intf.ip) {
    const [ip, mask] = intf.ip.split('/')
    const ipParts = ip.split('.')
    ipSegments.value = [...ipParts]
    configSubnetMask.value = parseInt(mask) || 24
  }
  
  if (intf.gateway) {
    const gatewayParts = intf.gateway.split('.')
    gatewaySegments.value = [...gatewayParts]
  }
  
  if (intf.dhcp_server) {
    const dhcpParts = intf.dhcp_server.split('.')
    dhcpSegments.value = [...dhcpParts]
  }
  
  if (intf.dns && intf.dns.length > 0) {
    dnsList.value = intf.dns.map(dns => dns.split('.'))
  } else {
    dnsList.value = [['', '', '', '']]
  }
  
  configForm.value = {
    ip: intf.ip || '',
    vlan_tag: intf.vlan || 0,
    gateway: intf.gateway || '',
    dhcp_server: intf.dhcp_server || '',
    dns: intf.dns || []
  }
  
  configDialogVisible.value = true
  nextTick(() => {
    configFormRef.value?.clearValidate()
  })
}

// 创建并配置网口的处理函数
const handleCreateAndConfig = async () => {
  if (!createFormRef.value) return
  
  try {
    // 如果有MAC地址错误，阻止提交
    if (macError.value) {
      ElMessage.error('请修正MAC地址格式后再提交')
      return
    }

    await createFormRef.value.validate()
    creating.value = true
    isCreatingMode.value = true  // 设置为创建模式
    
    // 准备创建数据
    const createData: InterfaceCreate = {
      pxe: createForm.value.pxe,
      vq_count: createForm.value.vq_count,
      vq_size: createForm.value.vq_size,
      mtu: createForm.value.mtu
    }
    
    // 可选字段
    if (createForm.value.mac && createForm.value.mac.trim()) {
      createData.mac = createForm.value.mac.trim()
    }
    
    // 添加uuid字段（如果用户输入了）
    if (createForm.value.uuid !== undefined && createForm.value.uuid !== null) {
      // 再次检查是否已存在该UUID
      const exists = xscInterfaces.value.some(intf => intf.uuid === createForm.value.uuid)
      if (exists) {
        throw new Error(`UUID ${createForm.value.uuid} 已存在，请选择其他UUID`)
      }
      createData.uuid = createForm.value.uuid
    }
    
    // 调用创建接口 - API应该直接返回新创建的网口对象
    const newInterface = await mv200Api.createXsc(mv200Id.value, createData)
    
    if (!newInterface) {
      throw new Error('创建失败，未返回网口信息')
    }
    
    // 关闭创建对话框
    createDialogVisible.value = false
    
    // 直接使用API返回的网口对象
    const createdInterface = {
      ...newInterface,
      deleting: false
    }
    
    // 添加到本地列表
    xscInterfaces.value.push(createdInterface)
    
    // 打开配置对话框
    selectedInterface.value = createdInterface
    handleConfigDialog(createdInterface)
    
    // 异步重新加载列表以确保数据同步
    setTimeout(async () => {
      await loadXscInterfaces()
    }, 100)
    
  } catch (error: any) {
    isCreatingMode.value = false  // 发生错误时重置模式
    if (error.name !== 'ValidationError') {
      console.error('创建网口失败:', error)
      ElMessage.error(error.response?.data?.detail || error.message || '创建网口失败')
    }
  } finally {
    creating.value = false
  }
}

// 创建网口
const handleCreate = async () => {
  if (!createFormRef.value) return
  
  try {
    // 如果有MAC地址错误，阻止提交
    if (macError.value) {
      ElMessage.error('请修正MAC地址格式后再提交')
      return
    }

    await createFormRef.value.validate()
    creating.value = true
    
    // 准备创建数据
    const createData: InterfaceCreate = {
      pxe: createForm.value.pxe,
      vq_count: createForm.value.vq_count,
      vq_size: createForm.value.vq_size,
      mtu: createForm.value.mtu
    }
    
    // 可选字段
    if (createForm.value.mac && createForm.value.mac.trim()) {
      createData.mac = createForm.value.mac.trim()
    }
    
    // 添加uuid字段（如果用户输入了）
    if (createForm.value.uuid !== undefined && createForm.value.uuid !== null) {
      // 再次检查是否已存在该UUID
      const exists = xscInterfaces.value.some(intf => intf.uuid === createForm.value.uuid)
      if (exists) {
        throw new Error(`UUID ${createForm.value.uuid} 已存在，请选择其他UUID`)
      }
      createData.uuid = createForm.value.uuid
    }
    
    // 调用创建接口
    await mv200Api.createXsc(mv200Id.value, createData)
    
    ElMessage.success(`网口创建成功${createData.uuid !== undefined ? `，UUID: ${createData.uuid}` : ''}`)
    createDialogVisible.value = false
    await loadXscInterfaces()
  } catch (error: any) {
    if (error.name !== 'ValidationError') {
      console.error('创建网口失败:', error)
      ElMessage.error(error.response?.data?.detail || error.message || '创建网口失败')
    }
  } finally {
    creating.value = false
  }
}

// 配置网口
const handleConfig = async () => {
  if (!configFormRef.value || !selectedInterface.value) return
  
  try {
    await configFormRef.value.validate()
    configuring.value = true
    
    // 准备配置数据
    const configData: OvsflowRequest = {
      ip: configForm.value.ip,
      vlan_tag: configForm.value.vlan_tag,
      mac: selectedInterface.value.mac
    }
    
    // 可选字段
    if (configForm.value.gateway && configForm.value.gateway.trim()) {
      configData.gateway = configForm.value.gateway.trim()
    }
    if (configForm.value.dhcp_server && configForm.value.dhcp_server.trim()) {
      configData.dhcp_server = configForm.value.dhcp_server.trim()
    }
    if (configForm.value.dns) {
      configData.dns = configForm.value.dns.filter(dns => dns && dns.trim() !== '')
    }
    
    // 如果有现有配置，先清理再配置
    if (selectedInterface.value.vlan) {
      try {
        // 先清理现有配置
        await mv200Api.removeXscOvsFlow(mv200Id.value, selectedInterface.value.uuid)
        ElMessage.info('已清理现有配置')
      } catch (cleanError) {
        console.warn('清理现有配置失败，继续尝试新增配置:', cleanError)
      }
    }
    
    // 新增配置
    await mv200Api.addXscOvsFlow(mv200Id.value, selectedInterface.value.uuid, configData)
    
    ElMessage.success('网口配置成功')
    configDialogVisible.value = false
    await loadXscInterfaces()
  } catch (error: any) {
    if (error.name !== 'ValidationError') {
      console.error('配置网口失败:', error)
      ElMessage.error(error.response?.data?.detail || '配置网口失败')
    }
  } finally {
    configuring.value = false
    isCreatingMode.value = false
  }
}

watch(() => configDialogVisible.value, (newVal) => {
  if (!newVal) {
    isCreatingMode.value = false  // 对话框关闭时重置模式
  }
})

// 删除单个网口
const handleDelete = async (intf: XscnetInfo & { deleting?: boolean }) => {
  try {
    // 检查是否为PXE专用网口（UUID=0）
    if (intf.uuid === 0) {
      ElMessage.warning('PXE专用网口（UUID=0）不可删除')
      return
    }

    await ElMessageBox.confirm(
      `确定要删除XSC网口 "UUID: ${intf.uuid}" 吗？`, 
      '确认删除', 
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger'
      }
    )

    // 设置删除状态和动画标记
    intf.deleting = true
    intf.deletingAnimation = true
    
    // 显示删除进度
    const loadingMessage = ElMessage.info({
      message: `正在删除XSC网口 UUID: ${intf.uuid}...`,
      duration: 0,
      showClose: false
    })
    
    try {
      await mv200Api.deleteXsc(mv200Id.value, intf.uuid)
      
      // 关闭加载消息
      loadingMessage.close()
      
      ElMessage.success(`XSC网口 UUID: ${intf.uuid} 删除成功`)
      await loadXscInterfaces()
    } catch (deleteError) {
      // 关闭加载消息
      loadingMessage.close()
      // 重置删除状态
      intf.deleting = false
      intf.deletingAnimation = false
      throw deleteError
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败，请重试')
    }
  }
}

// 返回MV200列表
const goBack = () => {
  router.push('/mv200')
}

// 添加键盘快捷键支持
import { onBeforeUnmount } from 'vue'

const handleKeyDown = (event: KeyboardEvent) => {
  // 按F5刷新
  if (event.key === 'F5') {
    event.preventDefault()
    loadXscInterfaces()
  }
  // 按ESC关闭所有对话框
  if (event.key === 'Escape') {
    if (detailDialogVisible.value) detailDialogVisible.value = false
    if (createDialogVisible.value) createDialogVisible.value = false
    if (configDialogVisible.value) configDialogVisible.value = false
  }
}

onMounted(async () => {
  if (!mv200Id.value) {
    ElMessage.error('无效的MV200 ID')
    router.push('/mv200')
    return
  }
  
  if (mv200Name.value === '未知MV200' || mv200Ip.value === '未知IP') {
    console.warn('MV200名称或IP信息缺失，请从MV200管理页面正常跳转')
  }
  
  await loadXscInterfaces()
  window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
/* 删除中的行样式 */
:deep(.el-table__row.deleting-row) {
  opacity: 0.6;
  background: linear-gradient(45deg, transparent 25%, rgba(245, 108, 108, 0.1) 25%, rgba(245, 108, 108, 0.1) 50%, transparent 50%, transparent 75%, rgba(245, 108, 108, 0.1) 75%);
  background-size: 20px 20px;
  animation: deleting-stripe 1s linear infinite;
}

@keyframes deleting-stripe {
  from { background-position: 0 0; }
  to { background-position: 20px 0; }
}

/* 删除中的单元格样式 */
:deep(.deleting-cell) {
  color: #f56c6c !important;
  font-weight: 500;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 网口名称样式 */
.interface-name {
  color: #13c2c2;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

/* IP信息样式 */
.ip-info {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.ip-address {
  color: #409eff;
  font-weight: 500;
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.netmask {
  color: #909399;
  font-size: 11px;
  margin-left: 2px;
}

/* MAC地址样式 */
.mac-address {
  color: #e6a23c;
  font-weight: 500;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  letter-spacing: 0.5px;
}

/* MTU值样式 */
.mtu-value {
  color: #67c23a;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

/* 空文本样式 */
.empty-text {
  color: #c0c4cc;
  font-style: italic;
  font-size: 12px;
}

/* PXE专用UUID样式 */
.pxe-uuid {
  background-color: #fdf6ec;
  border-color: #f5dab1;
  color: #e6a23c;
}

/* 状态标签样式 */
.status-tag {
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

/* DNS服务器列表样式 */
.dns-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dns-list-full {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 200px;
  overflow-y: auto;
  padding: 4px 0;
}

.dns-item {
  display: flex;
  align-items: center;
  padding: 2px 0;
}

.dns-ip {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #67c23a;
  background-color: #f6ffed;
  padding: 2px 6px;
  border-radius: 3px;
  border: 1px solid #b7eb8f;
}

.dns-more {
  color: #909399;
  font-size: 11px;
  font-style: italic;
  margin-top: 2px;
}

/* 详情对话框样式 */
.interface-detail {
  padding: 10px;
}

/* 对话框自定义样式 */
.custom-dialog {
  border-radius: 8px;
}

.custom-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid #e8e8e8;
  padding-bottom: 16px;
  margin-bottom: 0;
}

.custom-dialog :deep(.el-dialog__title) {
  color: #303133;
  font-weight: 600;
}

.custom-form {
  padding: 16px 8px 0 8px;
}

.custom-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.custom-form :deep(.el-form-item__label) {
  color: #606266;
  font-weight: 500;
}

/* 表单提示样式 */
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

/* 错误提示样式 */
.error-tip {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 4px;
  line-height: 1.4;
}

/* IP输入组样式 */
.ip-input-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ip-segments {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ip-dot {
  color: #606266;
  font-weight: bold;
  user-select: none;
}

:deep(.ip-segments .el-input__inner) {
  text-align: center;
  padding-left: 4px;
  padding-right: 4px;
  font-size: 13px;
  font-family: 'Courier New', monospace;
}

/* DNS输入组样式 */
.dns-input-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dns-input-group .dns-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dns-input-group .dns-item .ip-segments {
  flex: 1;
}

/* 表格样式调整 */
:deep(.el-table__row) {
  cursor: default;
}

:deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}

:deep(.el-table__cell) {
  padding: 12px 0;
}

:deep(.el-tag) {
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-weight: 600;
}

/* 操作下拉菜单样式 */
:deep(.action-dropdown-menu) {
  min-width: 140px;
  padding: 4px 0;
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

/* 删除按钮样式 */
:deep(.danger-item:not(.is-disabled)) {
  color: #f56c6c !important;
}

:deep(.danger-item:not(.is-disabled):hover) {
  color: #dd6161 !important;
  background-color: #fef0f0 !important;
}

:deep(.danger-item.is-disabled) {
  color: #c0c4cc !important;
  cursor: not-allowed !important;
}

/* 下拉菜单项内容样式 */
.dropdown-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  min-height: 20px;
}

/* 加载图标样式 */
.loading-icon {
  animation: spin 1s linear infinite;
  color: #409eff;
  width: 16px;
  height: 16px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 批量删除按钮样式 */
:deep(.el-button--danger) {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

:deep(.el-button--danger:hover) {
  background-color: #f78989;
  border-color: #f78989;
}

:deep(.el-button--danger.is-disabled) {
  background-color: #fbc4c4;
  border-color: #fab6b6;
  color: #fef0f0;
}

/* 加载状态样式 */
:deep(.el-table__empty-block) {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 响应式调整 */
@media screen and (max-width: 1200px) {
  .header-title {
    max-width: 300px;
  }
}

@media screen and (max-width: 992px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .header-title {
    max-width: 100%;
  }
  
  .header-actions .el-input {
    width: 100% !important;
    margin-right: 0 !important;
    margin-bottom: 12px;
  }
}
</style>