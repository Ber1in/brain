import apiClient from './client'
import type { Image, ImageCreate, ImageUpdate } from '@/types/api'

export const imagesApi = {
  getAll(): Promise<Image[]> {
    return apiClient.get('/images')
  },

  getById(id: string): Promise<Image> {
    return apiClient.get(`/images/${id}`)
  },

  create(data: ImageCreate): Promise<Image> {
    return apiClient.post('/images', data)
  },

  update(id: string, data: ImageUpdate): Promise<Image> {
    return apiClient.put(`/images/${id}`, data)
  },

  delete(id: string): Promise<void> {
    return apiClient.delete(`/images/${id}`)
  },
}
