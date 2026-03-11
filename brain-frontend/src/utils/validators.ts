/**
 * 公共验证规则工具
 * 集中管理表单验证规则，减少重复代码
 */

import { ElMessage } from 'element-plus'

/**
 * 验证规则类型定义
 */
export interface ValidationRule {
  required?: boolean
  message?: string
  trigger?: string | string[]
  validator?: (rule: any, value: any, callback: Function) => void
  pattern?: RegExp
  min?: number
  max?: number
  len?: number
  type?: string
}

/**
 * 创建必填验证规则
 */
export const createRequiredRule = (fieldName: string, trigger: string | string[] = 'blur'): ValidationRule => ({
  required: true,
  message: `请输入${fieldName}`,
  trigger
})

/**
 * 创建长度验证规则
 */
export const createLengthRule = (
  fieldName: string,
  options: { min?: number; max?: number; len?: number },
  trigger: string | string[] = 'blur'
): ValidationRule => {
  const { min, max, len } = options
  const rule: ValidationRule = { trigger }
  
  if (len !== undefined) {
    rule.len = len
    rule.message = `${fieldName}长度必须为${len}个字符`
  } else if (min !== undefined && max !== undefined) {
    rule.min = min
    rule.max = max
    rule.message = `${fieldName}长度必须在${min}到${max}个字符之间`
  } else if (min !== undefined) {
    rule.min = min
    rule.message = `${fieldName}长度不能少于${min}个字符`
  } else if (max !== undefined) {
    rule.max = max
    rule.message = `${fieldName}长度不能超过${max}个字符`
  }
  
  return rule
}

/**
 * 创建数字范围验证规则
 */
export const createNumberRangeRule = (
  fieldName: string,
  options: { min?: number; max?: number },
  trigger: string | string[] = 'blur'
): ValidationRule => {
  const { min, max } = options
  const rule: ValidationRule = { type: 'number', trigger }
  
  if (min !== undefined && max !== undefined) {
    rule.validator = (_, value, callback) => {
      if (value === null || value === undefined || value === '') {
        callback(new Error(`请输入${fieldName}`))
      } else if (value < min || value > max) {
        callback(new Error(`${fieldName}必须在${min}到${max}之间`))
      } else {
        callback()
      }
    }
  } else if (min !== undefined) {
    rule.validator = (_, value, callback) => {
      if (value === null || value === undefined || value === '') {
        callback(new Error(`请输入${fieldName}`))
      } else if (value < min) {
        callback(new Error(`${fieldName}不能小于${min}`))
      } else {
        callback()
      }
    }
  } else if (max !== undefined) {
    rule.validator = (_, value, callback) => {
      if (value === null || value === undefined || value === '') {
        callback(new Error(`请输入${fieldName}`))
      } else if (value > max) {
        callback(new Error(`${fieldName}不能大于${max}`))
      } else {
        callback()
      }
    }
  }
  
  return rule
}

/**
 * IP地址验证规则
 */
export const createIPRule = (fieldName: string = 'IP地址', trigger: string | string[] = 'blur'): ValidationRule => ({
  validator: (rule: any, value: string, callback: Function) => {
    if (!value) {
      callback(new Error(`请输入${fieldName}`))
      return
    }
    
    const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/
    if (!ipPattern.test(value)) {
      callback(new Error(`请输入有效的${fieldName}格式`))
      return
    }
    
    const parts = value.split('.')
    for (const part of parts) {
      const num = parseInt(part)
      if (num < 0 || num > 255) {
        callback(new Error(`${fieldName}每个数字段应在0-255之间`))
        return
      }
    }
    
    callback()
  },
  trigger
})

/**
 * 邮箱验证规则
 */
export const createEmailRule = (fieldName: string = '邮箱', trigger: string | string[] = 'blur'): ValidationRule => ({
  pattern: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
  message: `请输入有效的${fieldName}地址`,
  trigger
})

/**
 * 手机号验证规则（中国）
 */
export const createPhoneRule = (fieldName: string = '手机号', trigger: string | string[] = 'blur'): ValidationRule => ({
  pattern: /^1[3-9]\d{9}$/,
  message: `请输入有效的${fieldName}`,
  trigger
})

/**
 * URL验证规则
 */
export const createURLRule = (fieldName: string = 'URL', trigger: string | string[] = 'blur'): ValidationRule => ({
  pattern: /^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([/\w .-]*)*\/?$/,
  message: `请输入有效的${fieldName}`,
  trigger
})

/**
 * 密码强度验证规则
 */
export const createPasswordRule = (
  fieldName: string = '密码',
  options: { minLength?: number; requireUppercase?: boolean; requireLowercase?: boolean; requireNumbers?: boolean; requireSpecial?: boolean } = {},
  trigger: string | string[] = 'blur'
): ValidationRule => {
  const { minLength = 8, requireUppercase = true, requireLowercase = true, requireNumbers = true, requireSpecial = false } = options
  
  return {
    validator: (rule: any, value: string, callback: Function) => {
      if (!value) {
        callback(new Error(`请输入${fieldName}`))
        return
      }
      
      if (value.length < minLength) {
        callback(new Error(`${fieldName}长度不能少于${minLength}个字符`))
        return
      }
      
      if (requireUppercase && !/[A-Z]/.test(value)) {
        callback(new Error(`${fieldName}必须包含至少一个大写字母`))
        return
      }
      
      if (requireLowercase && !/[a-z]/.test(value)) {
        callback(new Error(`${fieldName}必须包含至少一个小写字母`))
        return
      }
      
      if (requireNumbers && !/\d/.test(value)) {
        callback(new Error(`${fieldName}必须包含至少一个数字`))
        return
      }
      
      if (requireSpecial && !/[!@#$%^&*(),.?":{}|<>]/.test(value)) {
        callback(new Error(`${fieldName}必须包含至少一个特殊字符`))
        return
      }
      
      callback()
    },
    trigger
  }
}

/**
 * Ceph位置格式验证（pool/rbd格式）
 */
export const createCephLocationRule = (fieldName: string = '镜像源地址', trigger: string | string[] = 'blur'): ValidationRule => ({
  validator: (rule: any, value: string, callback: Function) => {
    if (!value) {
      callback(new Error(`请输入${fieldName}`))
      return
    }
    
    const slashCount = (value.match(/\//g) || []).length
    if (slashCount === 0) {
      callback(new Error(`${fieldName}必须包含一个斜杠(/)，格式: pool/rbd`))
    } else if (slashCount > 1) {
      callback(new Error(`${fieldName}只能包含一个斜杠(/)，格式: pool/rbd`))
    } else {
      callback()
    }
  },
  trigger
})

/**
 * MAC地址验证规则
 */
export const createMacAddressRule = (fieldName: string = 'MAC地址', trigger: string | string[] = 'blur'): ValidationRule => ({
  pattern: /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/,
  message: `请输入有效的${fieldName}格式（如：00:1A:2B:3C:4D:5E）`,
  trigger
})

/**
 * 数字验证规则（必须是数字）
 */
export const createNumberRule = (fieldName: string = '数字', trigger: string | string[] = 'blur'): ValidationRule => ({
  type: 'number',
  message: `${fieldName}必须是数字`,
  trigger
})

/**
 * 整数验证规则
 */
export const createIntegerRule = (fieldName: string = '整数', trigger: string | string[] = 'blur'): ValidationRule => ({
  validator: (rule: any, value: any, callback: Function) => {
    if (value === null || value === undefined || value === '') {
      callback(new Error(`请输入${fieldName}`))
      return
    }
    
    if (!Number.isInteger(Number(value))) {
      callback(new Error(`${fieldName}必须是整数`))
      return
    }
    
    callback()
  },
  trigger
})

/**
 * 创建自定义验证规则
 */
export const createCustomValidator = (
  validator: (value: any) => boolean | string,
  errorMessage: string,
  trigger: string | string[] = 'blur'
): ValidationRule => ({
  validator: (rule: any, value: any, callback: Function) => {
    const result = validator(value)
    if (result === true) {
      callback()
    } else {
      callback(new Error(typeof result === 'string' ? result : errorMessage))
    }
  },
  trigger
})

/**
 * 常用的验证规则组合
 */
export const commonRules = {
  required: (fieldName: string) => createRequiredRule(fieldName),
  ip: createIPRule(),
  email: createEmailRule(),
  phone: createPhoneRule(),
  url: createURLRule(),
  cephLocation: createCephLocationRule(),
  macAddress: createMacAddressRule(),
  
  // 预设的密码规则
  password: createPasswordRule('密码'),
  strongPassword: createPasswordRule('密码', {
    minLength: 12,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSpecial: true
  })
}