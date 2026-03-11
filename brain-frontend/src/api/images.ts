/**
 * 镜像管理 API（使用通用 CRUD 工厂重构）
 */
import { createCrudApi } from './crud-factory'
import type { Image, ImageCreate, ImageUpdate } from '@/types/api'

// 创建镜像管理的 CRUD API
const imagesCrud = createCrudApi<Image, ImageCreate, ImageUpdate>({
  endpoint: 'images'
})

// 导出与原 API 相同的接口以保持向后兼容
export const imagesApi = {
  getAll: imagesCrud.getAll,
  getById: imagesCrud.getById,
  create: imagesCrud.create,
  update: imagesCrud.update,
  delete: imagesCrud.delete
}