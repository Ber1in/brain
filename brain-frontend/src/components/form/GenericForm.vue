<template>
  <div class="generic-form">
    <el-card>
      <template #header>
        <h2>{{ title }}</h2>
      </template>

      <el-form 
        :model="formData" 
        :rules="computedRules" 
        ref="formRef" 
        :label-width="labelWidth"
        v-loading="loading"
      >
        <!-- 动态渲染表单字段 -->
        <template v-for="field in fields" :key="field.name">
          <el-form-item 
            :label="field.label" 
            :prop="field.name"
            :required="field.required"
          >
            <!-- 文本输入框 -->
            <el-input
              v-if="field.type === 'text' || field.type === 'textarea'"
              v-model="formData[field.name]"
              :type="field.type === 'textarea' ? 'textarea' : 'text'"
              :placeholder="field.placeholder || `请输入${field.label}`"
              :clearable="field.clearable !== false"
              :rows="field.rows || (field.type === 'textarea' ? 3 : undefined)"
              :maxlength="field.maxlength"
              :show-word-limit="field.showWordLimit"
            >
              <!-- 插槽前缀/后缀 -->
              <template v-if="field.prefix" #prefix>
                <component :is="field.prefix" v-if="isComponent(field.prefix)" />
                <span v-else>{{ field.prefix }}</span>
              </template>
              <template v-if="field.suffix" #suffix>
                <component :is="field.suffix" v-if="isComponent(field.suffix)" />
                <span v-else>{{ field.suffix }}</span>
              </template>
            </el-input>

            <!-- 数字输入框 -->
            <el-input-number
              v-else-if="field.type === 'number'"
              v-model="formData[field.name]"
              :min="field.min"
              :max="field.max"
              :step="field.step"
              :precision="field.precision"
              :controls-position="field.controlsPosition || 'right'"
              :placeholder="field.placeholder || `请输入${field.label}`"
            />

            <!-- 下拉选择框 -->
            <el-select
              v-else-if="field.type === 'select'"
              v-model="formData[field.name]"
              :placeholder="field.placeholder || `请选择${field.label}`"
              :clearable="field.clearable !== false"
              :filterable="field.filterable"
              style="width: 100%"
            >
              <el-option
                v-for="option in field.options"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>

            <!-- 日期选择器 -->
            <el-date-picker
              v-else-if="field.type === 'date'"
              v-model="formData[field.name]"
              :type="field.dateType || 'date'"
              :placeholder="field.placeholder || `请选择${field.label}`"
              style="width: 100%"
            />

            <!-- 开关 -->
            <el-switch
              v-else-if="field.type === 'switch'"
              v-model="formData[field.name]"
              :active-text="field.activeText"
              :inactive-text="field.inactiveText"
            />

            <!-- 自定义渲染 -->
            <slot
              v-else-if="field.type === 'custom'"
              :name="`field-${field.name}`"
              :field="field"
              :value="formData[field.name]"
              :update="(value: any) => formData[field.name] = value"
            />

            <!-- 字段提示信息 -->
            <div v-if="field.tip" class="form-tip">
              {{ field.tip }}
            </div>
          </el-form-item>
        </template>

        <!-- 表单操作按钮 -->
        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="submitting">
            {{ submitText }}
          </el-button>
          <el-button @click="handleCancel" :disabled="submitting">
            {{ cancelText }}
          </el-button>
          
          <!-- 额外的操作按钮插槽 -->
          <slot name="extra-actions" />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useRouter } from 'vue-router'
import type { ValidationRule } from '@/utils/validators'

// 表单字段定义接口
export interface FormField {
  /** 字段名称，对应表单数据的键 */
  name: string
  /** 显示标签 */
  label: string
  /** 字段类型 */
  type: 'text' | 'textarea' | 'number' | 'select' | 'date' | 'switch' | 'custom'
  /** 是否为必填字段 */
  required?: boolean
  /** 占位符文本 */
  placeholder?: string
  /** 字段提示信息 */
  tip?: string
  /** 是否可清空 */
  clearable?: boolean
  /** 最大长度（文本字段） */
  maxlength?: number
  /** 是否显示字数统计 */
  showWordLimit?: boolean
  /** 行数（多行文本） */
  rows?: number
  /** 最小值（数字字段） */
  min?: number
  /** 最大值（数字字段） */
  max?: number
  /** 步长（数字字段） */
  step?: number
  /** 精度（数字字段） */
  precision?: number
  /** 按钮位置（数字字段） */
  controlsPosition?: 'right' | 'left'
  /** 选项列表（下拉选择） */
  options?: Array<{ label: string; value: any }>
  /** 日期选择器类型 */
  dateType?: 'date' | 'datetime' | 'daterange' | 'datetimerange'
  /** 前缀内容或组件 */
  prefix?: string | object
  /** 后缀内容或组件 */
  suffix?: string | object
  /** 自定义验证规则 */
  rules?: ValidationRule[]
  /** 默认值 */
  defaultValue?: any
  /** 是否禁用 */
  disabled?: boolean
}

// 组件属性
interface Props {
  /** 表单标题 */
  title: string
  /** 表单字段配置 */
  fields: FormField[]
  /** 表单初始数据 */
  initialData?: Record<string, any>
  /** 提交处理函数 */
  onSubmit: (data: any) => Promise<any>
  /** 提交按钮文本 */
  submitText?: string
  /** 取消按钮文本 */
  cancelText?: string
  /** 标签宽度 */
  labelWidth?: string
  /** 重定向路径（提交成功后跳转） */
  redirectTo?: string
  /** 是否显示加载状态 */
  loading?: boolean
  /** 额外的表单规则 */
  extraRules?: FormRules
}

const props = withDefaults(defineProps<Props>(), {
  submitText: '提交',
  cancelText: '取消',
  labelWidth: '120px',
  loading: false,
  extraRules: () => ({}),
  initialData: () => ({})
})

const emit = defineEmits<{
  submitted: [result: any]
  cancelled: []
  validationError: [errors: any]
}>()

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const formData = ref<Record<string, any>>({})

// 初始化表单数据
const initializeFormData = () => {
  const data: Record<string, any> = {}
  
  props.fields.forEach(field => {
    // 优先级：initialData > defaultValue
    if (props.initialData && props.initialData[field.name] !== undefined) {
      data[field.name] = props.initialData[field.name]
    } else if (field.defaultValue !== undefined) {
      data[field.name] = field.defaultValue
    } else {
      data[field.name] = field.type === 'number' ? 0 : ''
    }
  })
  
  formData.value = data
}

// 检查是否是组件
const isComponent = (obj: any): boolean => {
  return obj && typeof obj === 'object' && ('render' in obj || 'setup' in obj)
}

// 计算验证规则
const computedRules = computed(() => {
  const rules: FormRules = { ...props.extraRules }
  
  props.fields.forEach(field => {
    if (field.required && !field.rules?.some(rule => rule.required)) {
      rules[field.name] = [
        { required: true, message: `请输入${field.label}`, trigger: 'blur' },
        ...(field.rules || [])
      ]
    } else if (field.rules && field.rules.length > 0) {
      rules[field.name] = field.rules
    }
  })
  
  return rules
})

// 提交处理
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    const valid = await formRef.value.validate()
    if (!valid) return

    submitting.value = true
    const result = await props.onSubmit(formData.value)
    
    ElMessage.success('提交成功')
    emit('submitted', result)
    
    // 重定向
    if (props.redirectTo) {
      if (props.redirectTo.startsWith('http')) {
        window.location.href = props.redirectTo
      } else {
        router.push(props.redirectTo)
      }
    }
  } catch (error: any) {
    // 验证错误
    if (error?.errors) {
      emit('validationError', error.errors)
      ElMessage.warning('请检查表单输入')
    } else {
      // 其他错误
      const message = error?.response?.data?.message || error?.message || '提交失败'
      ElMessage.error(message)
    }
  } finally {
    submitting.value = false
  }
}

// 取消处理
const handleCancel = () => {
  emit('cancelled')
  router.back()
}

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  initializeFormData()
}

// 设置表单数据
const setFormData = (data: Record<string, any>) => {
  formData.value = { ...formData.value, ...data }
}

// 暴露方法给父组件
defineExpose({
  resetForm,
  setFormData,
  validate: () => formRef.value?.validate(),
  clearValidate: () => formRef.value?.clearValidate()
})

// 监听初始数据变化
watch(() => props.initialData, (newData) => {
  if (newData) {
    setFormData(newData)
  }
}, { deep: true })

// 初始化
onMounted(() => {
  initializeFormData()
})
</script>

<style scoped>
.generic-form {
  max-width: 800px;
  margin: 0 auto;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}
</style>