<template>
  <div class="xsc-interface-create">
    <el-card>
      <template #header>
        <h2>创建XSC网口</h2>
      </template>
      
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="MV200" prop="mv200_id">
          <el-select
            v-model="form.mv200_id"
            placeholder="选择MV200"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="server in mv200Servers"
              :key="server.id"
              :label="server.name"
              :value="server.id"
            >
              <span>{{ server.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 13px">
                {{ server.ip_address }}
              </span>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item label="IP地址/掩码" prop="ip">
          <div class="ip-input-group">
            <div class="ip-segments">
              <el-input
                ref="ipInput1"
                v-model="ipSegments[0]"
                placeholder=""
                maxlength="3"
                @input="validateIpSegment(0, $event)"
                @blur="combineIP"
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
                @blur="combineIP"
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
                @blur="combineIP"
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
                @blur="combineIP"
                style="width: 60px; text-align: center;"
              />
            </div>
            <span style="margin: 0 8px;">/</span>
            <el-input-number
              v-model="subnetMask"
              :min="0"
              :max="32"
              placeholder="掩码"
              style="width: 100px;"
              @blur="combineIP"
            />
          </div>
          <div class="form-tip">例: 192.168.10.101/24</div>
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
              @blur="combineGateway"
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
              @blur="combineGateway"
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
              @blur="combineGateway"
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
              @blur="combineGateway"
              style="width: 60px; text-align: center;"
            />
          </div>
        </el-form-item>

        <el-form-item label="VLAN ID" prop="vlan_tag">
          <el-input-number
            v-model="form.vlan_tag"
            :min="0"
            :max="4094"
            placeholder="输入VLAN ID"
            style="width: 150px;"
            :controls="false"
          />
        </el-form-item>

        <el-form-item label="MTU" prop="mtu">
          <el-input-number
            v-model="form.mtu"
            :min="68"
            :max="9000"
            placeholder="输入MTU值"
            style="width: 150px;"
          />
        </el-form-item>

        <el-form-item label="MAC地址">
          <el-input 
            v-model="form.mac" 
            placeholder="自定义网口的MAC地址（可选）" 
            clearable
            style="width: 250px;"
            @input="validateMacAddress"
          />
          <div v-if="macError" class="error-tip">{{ macError }}</div>
        </el-form-item>

        <el-form-item label="DNS服务器">
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
                  @blur="combineDns(dnsIndex)"
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
                  @blur="combineDns(dnsIndex)"
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
                  @blur="combineDns(dnsIndex)"
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
                  @blur="combineDns(dnsIndex)"
                  style="width: 60px; text-align: center;"
                />
              </div>
              <el-button
                type="danger"
                link
                :icon="Delete"
                @click="removeDns(dnsIndex)"
                :disabled="dnsList.length === 1"
                style="margin-left: 12px;"
              />
            </div>
            <el-button
              type="primary"
              link
              :icon="Plus"
              @click="addDns"
            >
              添加DNS
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="描述">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="3" 
            placeholder="输入网口描述信息"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading">
            创建
          </el-button>
          <el-button @click="$router.push('/xsc-interface')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import { networkApi } from '@/api/network'
import { mv200Api } from '@/api/mv200'
import type { InterfaceCreate, MVServer } from '@/types/api'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const mv200Servers = ref<MVServer[]>([])
const macError = ref('') // MAC地址错误提示

// IP地址相关
const ipSegments = ref(['', '', '', ''])
const subnetMask = ref(24)

// 网关相关
const gatewaySegments = ref(['', '', '', ''])

// DNS相关 - 每个DNS是一个包含4个段的数组
const dnsList = ref<string[][]>([['', '', '', '']])

// Refs for inputs
const ipInput1 = ref()
const ipInput2 = ref()
const ipInput3 = ref()
const ipInput4 = ref()

const gatewayInput1 = ref()
const gatewayInput2 = ref()
const gatewayInput3 = ref()
const gatewayInput4 = ref()

const dnsInputRefs = ref<Record<string, any>>({})

const form = reactive<InterfaceCreate>({
  mv200_id: '',
  ip: '',
  gateway: '',
  vlan_tag: undefined,
  mtu: 1500,
  mac: undefined,
  dns: [],
  description: ''
})

// MAC地址实时验证
const validateMacAddress = () => {
  if (!form.mac || form.mac.trim() === '') {
    macError.value = ''
    return
  }
  
  const macPattern = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/
  if (!macPattern.test(form.mac)) {
    macError.value = 'MAC地址格式不正确，请使用 XX:XX:XX:XX:XX:XX 或 XX-XX-XX-XX-XX-XX 格式，不区分大小写'
  } else {
    macError.value = ''
  }
}

// 设置DNS输入框ref
const setDnsInputRef = (dnsIndex: number, segmentIndex: number, el: any) => {
  if (el) {
    dnsInputRefs.value[`dns_${dnsIndex}_${segmentIndex}`] = el
  }
}

// 处理IP地址粘贴
const handleIpPaste = async (event: ClipboardEvent) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  await parseAndSetIp(pastedText, ipSegments.value, 'ip')
}

// 处理网关粘贴
const handleGatewayPaste = async (event: ClipboardEvent) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  await parseAndSetIp(pastedText, gatewaySegments.value, 'gateway')
}

// 处理DNS粘贴
const handleDnsPaste = async (dnsIndex: number, event: ClipboardEvent) => {
  event.preventDefault()
  const pastedText = event.clipboardData?.getData('text') || ''
  await parseAndSetIp(pastedText, dnsList.value[dnsIndex], 'dns', dnsIndex)
}

// 解析并设置IP地址
const parseAndSetIp = async (text: string, segments: string[], type: 'ip' | 'gateway' | 'dns', dnsIndex?: number) => {
  text = text.trim()
  
  console.log('粘贴的内容:', text)
  
  const ipRegex = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/
  const match = text.match(ipRegex)
  
  if (match) {
    segments[0] = match[1]
    segments[1] = match[2]
    segments[2] = match[3]
    segments[3] = match[4]
    
    console.log('解析后的IP段:', segments)
    
    await nextTick()
    
    if (type === 'ip') {
      combineIP()
    } else if (type === 'gateway') {
      combineGateway()
    } else if (type === 'dns' && dnsIndex !== undefined) {
      combineDns(dnsIndex)
    }
    
  } else {
    ElMessage.warning('粘贴的内容不是有效的IP地址格式，请使用 xxx.xxx.xxx.xxx 格式')
  }
}

// IP段验证 - 只支持小数点跳转
const validateIpSegment = (index: number, value: string) => {
  // 只允许数字
  let cleanValue = value.replace(/[^\d]/g, '')
  ipSegments.value[index] = cleanValue
  
  // 监听键盘事件来处理小数点跳转
}

// 网关段验证 - 只支持小数点跳转
const validateGatewaySegment = (index: number, value: string) => {
  let cleanValue = value.replace(/[^\d]/g, '')
  gatewaySegments.value[index] = cleanValue
}

// DNS段验证 - 只支持小数点跳转
const validateDnsSegment = (dnsIndex: number, segmentIndex: number, value: string) => {
  let cleanValue = value.replace(/[^\d]/g, '')
  dnsList.value[dnsIndex][segmentIndex] = cleanValue
}

// 组合IP地址和掩码
const combineIP = () => {
  const ip = ipSegments.value.join('.')
  console.log('组合IP:', ip)
  if (ip && subnetMask.value !== null && ip !== '...') {
    form.ip = `${ip}/${subnetMask.value}`
  } else {
    form.ip = ''
  }
  console.log('最终form.ip:', form.ip)
}

// 组合网关地址
const combineGateway = () => {
  const gateway = gatewaySegments.value.join('.')
  console.log('组合网关:', gateway)
  if (gateway && gateway !== '...') {
    form.gateway = gateway
  } else {
    form.gateway = ''
  }
  console.log('最终form.gateway:', form.gateway)
}

// 组合DNS地址
const combineDns = (dnsIndex: number) => {
  const dns = dnsList.value[dnsIndex].join('.')
  console.log('组合DNS:', dns)
  if (dns && dns !== '...') {
    form.dns[dnsIndex] = dns
  } else {
    form.dns[dnsIndex] = ''
  }
  console.log('最终form.dns:', form.dns)
}


// 键盘事件处理
const handleKeydown = (event: KeyboardEvent, index: number, type: 'ip' | 'gateway' | 'dns', dnsIndex?: number) => {
  // 如果是小数点键
  if (event.key === '.' || event.key === 'Period') {
    event.preventDefault() // 阻止默认行为，避免输入小数点
    
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

// IP地址验证
const validateIP = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback(new Error('请输入IP地址和掩码'))
    return
  }
  
  const ipPattern = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
  if (!ipPattern.test(value)) {
    callback(new Error('请输入有效的IP地址格式'))
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
  if (!value) {
    callback(new Error('请输入网关地址'))
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

// MAC地址验证（可选）
const validateMAC = (rule: any, value: string, callback: any) => {
  if (!value) {
    callback()
    return
  }
  
  const macPattern = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/
  if (!macPattern.test(value)) {
    callback(new Error('请输入有效的MAC地址格式，如: 00:11:22:33:44:55 或 00-11-22-33-44-55'))
    return
  }
  
  callback()
}

const rules: FormRules = {
  mv200_id: [
    { required: true, message: '请选择MV200', trigger: 'blur' }
  ],
  ip: [
    { required: true, validator: validateIP, trigger: 'blur' }
  ],
  gateway: [
    { required: true, validator: validateGateway, trigger: 'blur' }
  ],
  vlan_tag: [
    { required: true, message: '请输入VLAN ID', trigger: 'blur' },
    { type: 'number', min: 0, max: 4094, message: 'VLAN ID必须在0-4094之间', trigger: 'blur' }
  ],
  mtu: [
    { type: 'number', min: 68, max: 9000, message: 'MTU必须在68-9000之间', trigger: 'blur' }
  ],
  mac: [
    { validator: validateMAC, trigger: 'blur' }
  ]
}

// 添加DNS
const addDns = () => {
  dnsList.value.push(['', '', '', ''])
  form.dns.push('')
}

// 移除DNS
const removeDns = (index: number) => {
  if (dnsList.value.length > 1) {
    dnsList.value.splice(index, 1)
    form.dns.splice(index, 1)
  }
}

// 加载MV200服务器列表
const loadMv200Servers = async () => {
  try {
    const servers = await mv200Api.getAll()
    mv200Servers.value = servers
  } catch (error) {
    ElMessage.error('加载MV200列表失败')
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    // 如果有MAC地址错误，阻止提交
    if (macError.value) {
      ElMessage.error('请修正MAC地址格式后再提交')
      return
    }

    const valid = await formRef.value.validate()
    if (!valid) return

    loading.value = true

    // 处理DNS列表，过滤空值
    form.dns = form.dns.filter(dns => dns && dns.trim() !== '' && dns !== '...')
    
    // 如果MAC地址为空，设置为undefined，不传该参数
    if (!form.mac || form.mac.trim() === '') {
      form.mac = undefined
    }

    await networkApi.create(form)
    ElMessage.success('创建成功')
    router.push('/xsc-interface')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadMv200Servers()
})
</script>

<style scoped>
.ip-input-group {
  display: flex;
  align-items: center;
}

.ip-segments {
  display: flex;
  align-items: center;
}

.ip-dot {
  margin: 0 4px;
  color: #606266;
  font-weight: bold;
}

.dns-input-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dns-item {
  display: flex;
  align-items: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.error-tip {
  font-size: 12px;
  color: #f56c6c;
  margin-top: 4px;
}

/* 输入框居中文本 */
:deep(.ip-segments .el-input__inner) {
  text-align: center;
  padding-left: 4px;
  padding-right: 4px;
  font-size: 13px;
}
</style>