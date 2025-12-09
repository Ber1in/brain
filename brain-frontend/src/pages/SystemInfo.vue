<template>
  <div class="settings-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统设置</span>
          <div class="header-actions">
            <el-button 
              type="primary" 
              @click="saveSettings" 
              :loading="saving"
              class="save-btn"
            >
              保存设置
            </el-button>
          </div>
        </div>
      </template>

      <div class="settings-container">
        <!-- 服务器释放提醒配置 -->
        <el-card class="settings-section" shadow="never">
          <template #header>
            <div class="section-header">
              <div class="section-title">
                <h3>服务器释放提醒配置</h3>
                <el-tag type="warning" size="small">释放时自动推送提醒</el-tag>
              </div>
            </div>
          </template>

          <div class="reminder-config">
            <!-- SMTP配置 -->
            <div class="config-section">
              <h4 class="subsection-header">邮件提醒配置</h4>
              <el-form 
                :model="settingsForm" 
                label-width="140px" 
                class="compact-form"
                ref="settingsFormRef"
              >
                <!-- SMTP主机 -->
                <el-form-item 
                  label="SMTP主机" 
                  prop="smtp.host"
                  :rules="[{ required: true, message: '请输入SMTP主机地址', trigger: 'blur' }]"
                >
                  <el-input 
                    v-model="settingsForm.smtp.host" 
                    placeholder="smtp.example.com"
                    readonly
                    disabled
                    style="width: 300px;"
                    size="medium"
                    >
                    <template #prefix>
                        <el-icon><Connection /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>

                <!-- SMTP端口 -->
                <el-form-item 
                  label="SMTP端口" 
                  prop="smtp.port"
                  :rules="[
                    { required: true, message: '请输入SMTP端口', trigger: 'blur' },
                    { type: 'number', min: 1, max: 65535, message: '端口号必须在1-65535之间', trigger: 'blur' }
                  ]"
                >
                  <el-input-number
                    v-model="settingsForm.smtp.port"
                    placeholder="端口号"
                    readonly
                    disabled
                    style="width: 200px;"
                    size="medium"
                  />
                  <div class="form-tip">
                    常用端口：587（TLS），465（SSL），25（不加密）
                  </div>
                </el-form-item>

                <!-- SMTP用户名 -->
                <el-form-item 
                  label="SMTP用户名" 
                  prop="smtp.user"
                  :rules="[{ required: true, message: '请输入SMTP用户名', trigger: 'blur' }]"
                >
                  <el-input 
                    v-model="settingsForm.smtp.user"
                    placeholder="用户名"
                    readonly
                    disabled
                    style="width: 300px;"
                    size="medium"
                  >
                    <template #prefix>
                      <el-icon><User /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-form>
            </div>

            <!-- 飞书群消息配置 -->
            <div class="config-section">
              <div class="subsection-header">
                <h4 class="subsection-title">默认推送飞书群</h4>
                <el-tooltip
                  effect="dark"
                  content="服务器释放时推送告警信息的默认群组，如服务器无自定义推送飞书群的标签，则使用推送至此默认飞书群"
                  placement="top"
                >
                  <el-icon class="tooltip-icon"><QuestionFilled /></el-icon>
                </el-tooltip>
              </div>
              
              <!-- 默认Webhook -->
              <div class="default-webhook">
                <el-form 
                  :model="settingsForm" 
                  label-width="140px"
                  class="compact-form"
                >
                  <el-form-item 
                    label="默认Webhook" 
                    prop="default_webhook"
                  >
                    <div class="webhook-input compact">
                      <span class="webhook-prefix">https://webhook.yunsilicon.com/open-apis/bot/v2/hook/</span>
                      <el-input 
                        v-model="defaultWebhookId" 
                        placeholder="请输入群机器人ID"
                        clearable
                        style="width: 300px;"
                        size="medium"
                        @input="updateDefaultWebhook"
                      />
                    </div>
                  </el-form-item>
                </el-form>
              </div>

              <!-- 自定义接收推送的飞书群 -->
              <div class="tag-webhook-section">
                <div class="subsection-header">
                  <div class="tag-section-title">
                    <h4 class="tag-subtitle">自定义推送飞书群</h4>
                    <el-tooltip
                      effect="dark"
                      content="如果服务器有这个标签，会优先将提醒消息推送至标签对应的飞书群"
                      placement="top"
                      class="tag-tooltip"
                    >
                      <el-icon class="tooltip-icon"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </div>
                </div>

                <div class="tag-webhook-table-wrapper">
                  <el-table 
                    :data="settingsForm.release_notices" 
                    size="small" 
                    border 
                    class="tag-table"
                    :show-header="true"
                  >
                    <el-table-column prop="tag" label="标签名称" width="180">
                      <template #default="{ row, $index }">
                        <el-form-item 
                          :prop="`release_notices[${$index}].tag`"
                          :rules="[{ required: true, message: '请选择标签', trigger: 'change' }]"
                          style="margin-bottom: 0;"
                        >
                          <el-select
                            v-model="row.tag"
                            placeholder="请选择标签"
                            clearable
                            filterable
                            style="width: 160px;"
                            size="small"
                          >
                            <el-option
                              v-for="tag in getAvailableTagsForIndex($index)"
                              :key="tag.id"
                              :label="tag.name"
                              :value="tag.name"
                            >
                              <div class="tag-option">
                                <el-tag
                                  size="small"
                                  :style="getTagStyle(tag.color)"
                                  class="option-tag"
                                >
                                  {{ tag.name }}
                                </el-tag>
                              </div>
                            </el-option>
                          </el-select>
                        </el-form-item>
                      </template>
                    </el-table-column>
                    
                    <el-table-column prop="webhook" label="飞书机器人Webhook" min-width="500">
                      <template #default="{ row, $index }">
                        <div class="webhook-cell">
                          <el-form-item 
                            :prop="`release_notices[${$index}].webhook`"
                            style="margin-bottom: 0;"
                          >
                            <div class="webhook-input compact">
                              <span class="webhook-prefix">https://webhook.yunsilicon.com/open-apis/bot/v2/hook/</span>
                              <el-input 
                                v-model="tagWebhookIds[$index]"
                                placeholder="请输入群机器人ID"
                                clearable
                                style="width: 300px;"
                                size="small"
                                @input="(value) => updateTagWebhook($index, value)"
                              />
                            </div>
                          </el-form-item>
                        </div>
                      </template>
                    </el-table-column>
                    
                    <el-table-column label="操作" width="60" fixed="right" align="center">
                      <template #default="{ $index }">
                        <el-button
                          type="danger"
                          text
                          size="small"
                          @click="removeReleaseNotice($index)"
                          circle
                        >
                          <el-icon><Delete /></el-icon>
                        </el-button>
                      </template>
                    </el-table-column>
                  </el-table>
                  
                  <!-- 添加行按钮 -->
                  <div class="add-row" @click="addReleaseNotice" v-if="hasMoreTagsAvailable">
                    <el-button type="text" class="add-row-btn">
                      <el-icon><Plus /></el-icon>
                      <span>添加自定义配置</span>
                    </el-button>
                  </div>
                  
                  <div v-else class="no-more-tags">
                    <el-icon><InfoFilled /></el-icon>
                    <span>所有标签都已配置完毕</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage, type FormInstance } from 'element-plus'
import { 
  Connection, 
  User, 
  Plus, 
  Delete,
  QuestionFilled,
  InfoFilled
} from '@element-plus/icons-vue'
import { settingsApi, tagApi } from '@/api/common'
import type { AppConfig, SMTPConfig, ReleaseNotice, TagResponse } from '@/types/api'

// 表单引用
const settingsFormRef = ref<FormInstance>()

// 状态
const saving = ref(false)
const originalSettings = ref<AppConfig | null>(null)
const availableTags = ref<TagResponse[]>([])

// 固定Webhook前缀
const WEBHOOK_PREFIX = 'https://webhook.yunsilicon.com/open-apis/bot/v2/hook/'

// 分离的Webhook ID
const defaultWebhookId = ref('')
const tagWebhookIds = ref<string[]>([])

// 表单数据
const settingsForm = reactive<AppConfig>({
  default_webhook: '',
  smtp: {
    host: '',
    port: 587,
    user: '',
    password: ''
  },
  yuntester_platform: '',
  file_server: '',
  platform_port: 0,
  debug: false,
  ldap_server: '',
  admin_password: '',
  release_notices: []
})

// 计算可用的标签（排除已选择的标签）
const usedTags = computed(() => {
  if (!settingsForm.release_notices) return []
  return settingsForm.release_notices
    .filter(notice => notice.tag && notice.tag.trim() !== '')
    .map(notice => notice.tag)
})

// 获取某个索引可用的标签
const getAvailableTagsForIndex = (index: number) => {
  const currentTag = settingsForm.release_notices?.[index]?.tag || ''
  return availableTags.value.filter(tag => {
    // 如果是当前已选的标签，允许保留
    if (tag.name === currentTag) return true
    // 否则检查是否被其他行使用
    return !usedTags.value.includes(tag.name)
  })
}

// 判断是否还有可用标签
const hasMoreTagsAvailable = computed(() => {
  return availableTags.value.length > usedTags.value.length
})

// 从完整Webhook中提取ID
const extractWebhookId = (webhook: string): string => {
  if (!webhook) return ''
  if (webhook.startsWith(WEBHOOK_PREFIX)) {
    return webhook.substring(WEBHOOK_PREFIX.length)
  }
  return webhook
}

// 用ID构建完整Webhook
const buildWebhook = (id: string): string => {
  if (!id) return ''
  return `${WEBHOOK_PREFIX}${id}`
}

// 更新默认Webhook
const updateDefaultWebhook = (id: string) => {
  settingsForm.default_webhook = buildWebhook(id)
}

// 更新标签Webhook
const updateTagWebhook = (index: number, id: string) => {
  if (settingsForm.release_notices && settingsForm.release_notices[index]) {
    settingsForm.release_notices[index].webhook = buildWebhook(id)
  }
}

// 获取标签样式
const getTagStyle = (color: string) => {
  const hexColor = color.toUpperCase()
  
  // 计算文字颜色（根据背景色亮度决定用黑色还是白色文字）
  const rgb = parseInt(color.replace('#', ''), 16)
  const r = (rgb >> 16) & 0xff
  const g = (rgb >> 8) & 0xff
  const b = (rgb >> 0) & 0xff
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  const textColor = brightness > 128 ? '#000000' : '#ffffff'
  
  return {
    backgroundColor: hexColor,
    borderColor: hexColor,
    color: textColor
  }
}

// 加载标签列表
const loadTags = async () => {
  try {
    const response = await tagApi.getTags()
    availableTags.value = response.tags || []
  } catch (error) {
    console.error('加载标签失败:', error)
  }
}

// 加载设置
const loadSettings = async () => {
  try {
    const data = await settingsApi.getSettings()
    originalSettings.value = data
    
    // 只更新我们需要显示的字段，其他字段保持原值
    settingsForm.default_webhook = data.default_webhook
    settingsForm.smtp = { ...data.smtp }
    settingsForm.release_notices = data.release_notices ? [...data.release_notices] : []
    
    // 确保release_notices不为null
    if (!settingsForm.release_notices) {
      settingsForm.release_notices = []
    }
    
    // 提取默认Webhook的ID
    defaultWebhookId.value = extractWebhookId(data.default_webhook)
    
    // 提取标签Webhook的ID
    tagWebhookIds.value = data.release_notices 
      ? data.release_notices.map(notice => extractWebhookId(notice.webhook))
      : []
    
    // 确保tagWebhookIds长度与release_notices一致
    if (settingsForm.release_notices.length > 0 && tagWebhookIds.value.length === 0) {
      tagWebhookIds.value = Array(settingsForm.release_notices.length).fill('')
    }
    
  } catch (error: any) {
    ElMessage.error('加载设置失败: ' + (error.response?.data?.detail || '网络错误'))
  }
}

// 保存设置
const saveSettings = async () => {
  if (!settingsFormRef.value) return

  try {
    await settingsFormRef.value.validate()
    
    saving.value = true
    
    // 准备提交的数据
    const submitData: Partial<AppConfig> = {
      default_webhook: settingsForm.default_webhook,
      smtp: {
        host: settingsForm.smtp.host,
        port: settingsForm.smtp.port,
        user: settingsForm.smtp.user
      },
      release_notices: settingsForm.release_notices 
        ? settingsForm.release_notices.filter(notice => 
            notice.tag && notice.tag.trim() !== '' && notice.webhook && notice.webhook.trim() !== ''
          )
        : null
    }
    
    await settingsApi.patchSettings(submitData as AppConfig)
    ElMessage.success('设置保存成功')
    
    // 重新加载设置以获取更新后的数据
    await loadSettings()
    
  } catch (error: any) {
    if (error.name !== 'ValidationError') {
      ElMessage.error('保存设置失败: ' + (error.response?.data?.detail || '网络错误'))
    }
  } finally {
    saving.value = false
  }
}

// 添加标签Webhook配置
const addReleaseNotice = () => {
  if (!settingsForm.release_notices) {
    settingsForm.release_notices = []
  }
  
  // 找到第一个可用的标签
  const availableTag = availableTags.value.find(tag => !usedTags.value.includes(tag.name))
  
  settingsForm.release_notices.push({
    tag: availableTag ? availableTag.name : '',
    webhook: ''
  })
  
  tagWebhookIds.value.push('')
}

// 删除标签Webhook配置 - 直接删除，无确认弹窗
const removeReleaseNotice = (index: number) => {
  if (settingsForm.release_notices) {
    settingsForm.release_notices.splice(index, 1)
    tagWebhookIds.value.splice(index, 1)
  }
}

onMounted(() => {
  loadSettings()
  loadTags()
})
</script>

<style scoped>

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  background: white;
  z-index: 1000;
  padding: 10px 0;
  margin: -10px 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  position: sticky;
  top: 20px;
  z-index: 1001;
}

.save-btn {
  background-color: #409eff;
  border-color: #409eff;
  color: white;
}

.save-btn:hover {
  background-color: #337ecc;
  border-color: #337ecc;
}

.settings-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.section-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.reminder-config {
  padding: 16px 20px;
}

.config-section {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #e5e7eb;
}

.config-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.subsection-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 8px;
}

.subsection-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.tag-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tag-subtitle {
  font-size: 15px;
  font-weight: 600;
  color: #4b5563;
  margin: 0;
}

/* 紧凑表单样式 */
.compact-form {
  margin: 0;
}

.compact-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.compact-form :deep(.el-form-item__label) {
  padding-right: 12px;
  font-weight: 500;
  color: #374151;
  font-size: 14px;
}

.form-tip {
  font-size: 12px;
  color: #6b7280;
  margin-top: 6px;
  line-height: 1.4;
}

/* 工具提示图标样式 */
.tooltip-icon {
  color: #909399;
  cursor: help;
  font-size: 16px;
  transition: color 0.2s ease;
}

.tooltip-icon:hover {
  color: #409eff;
}

.tag-tooltip {
  margin-left: 4px;
}

/* Webhook输入框样式 - 更紧凑 */
.webhook-input.compact {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 4px;
}

.webhook-prefix {
  font-size: 11px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 0 6px;
  border-radius: 4px;
  border: 1px solid #e5e7eb;
  font-family: 'Monaco', 'Consolas', monospace;
  white-space: nowrap;
  height: 30px;
  line-height: 28px;
  display: flex;
  align-items: center;
}

.webhook-input.compact :deep(.el-input) {
  flex-shrink: 0;
}

/* 标签Webhook配置样式 */
.tag-webhook-section {
  margin-top: 24px;
}

.tag-webhook-table-wrapper {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
}

.tag-table {
  width: 100%;
}

.tag-table :deep(.el-table__header-wrapper) {
  background-color: #f8fafc;
}

.tag-table :deep(.el-table__cell) {
  padding: 4px 0 !important;
}

.tag-table :deep(.el-table .cell) {
  padding: 0 8px !important;
}

.tag-table :deep(.el-table__row) {
  height: 42px;
}

/* 表格内表单项目高度调整 */
.tag-table :deep(.el-form-item) {
  margin-bottom: 0;
  display: flex;
  align-items: center;
  height: 32px;
}

.tag-table :deep(.el-form-item__content) {
  line-height: 1;
}

.tag-table :deep(.el-input__wrapper) {
  height: 32px;
  padding: 1px 11px;
}

.tag-table :deep(.el-input__inner) {
  height: 28px;
  line-height: 28px;
}

/* Webhook单元格样式 */
.webhook-cell {
  padding: 4px 0;
}

/* 添加行按钮 - 更紧凑 */
.add-row {
  text-align: center;
  padding: 8px 12px;
  border-top: 1px solid #ebeef5;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.add-row:hover {
  background: #f5f7fa;
}

.add-row-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #409eff;
  font-size: 13px;
  height: 24px;
}

.add-row-btn:hover {
  color: #337ecc;
}

.add-row-btn .el-icon {
  font-size: 14px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

/* 没有更多标签提示 - 更紧凑 */
.no-more-tags {
  text-align: center;
  padding: 8px 12px;
  border-top: 1px solid #ebeef5;
  background: white;
  color: #909399;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 40px;
}

.no-more-tags .el-icon {
  color: #c0c4cc;
  font-size: 14px;
}

/* 操作按钮样式优化 */
.tag-table :deep(.el-button--text) {
  padding: 4px;
  font-size: 12px;
}

.tag-table :deep(.el-button--text:hover) {
  background-color: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}

/* 标签选项样式 */
.tag-option {
  display: flex;
  align-items: center;
}

.option-tag {
  border: none;
  font-size: 12px;
  padding: 2px 8px;
  height: 22px;
  line-height: 18px;
}

/* 表单样式优化 */
:deep(.el-input .el-input__wrapper) {
  border-radius: 6px;
}

:deep(.el-input-number .el-input__wrapper) {
  border-radius: 6px;
}

:deep(.el-select .el-input__wrapper) {
  border-radius: 6px;
}
</style>