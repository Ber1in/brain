/**
 * 组件导出文件
 * 统一导出所有公共组件，方便导入使用
 */

// 表单组件
export { default as GenericForm } from './form/GenericForm.vue'
export type { FormField } from './form/GenericForm.vue'

// 表格组件
export { default as GenericTable } from './table/GenericTable.vue'
export type { TableColumn } from './table/GenericTable.vue'

// 其他组件（未来添加）
// export { default as SomeOtherComponent } from './other/SomeOtherComponent.vue'