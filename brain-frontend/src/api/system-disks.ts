import apiClient from './client'
import type { SystemDisk, BareMetalCreate, SystemDiskUpdate, UploadToImage, DeleteDiskResponse } from '@/types/api'

export const systemDisksApi = {
  getAll(): Promise<SystemDisk[]> {
    return apiClient.get('/system-disks')
  },

  getById(id: string): Promise<SystemDisk> {
    return apiClient.get(`/system-disks/${id}`)
  },

  create(data: BareMetalCreate): Promise<DeleteDiskResponse> {
    return apiClient.post('/system-disks', data)
  },

  update(id: string, data: SystemDiskUpdate): Promise<SystemDisk> {
    return apiClient.put(`/system-disks/${id}`, data)
  },

  delete(id: string): Promise<DeleteDiskResponse> {
    return apiClient.delete(`/system-disks/${id}`)
  },

  uploadToImage(id: string, data: UploadToImage): Promise<void> {
    return apiClient.post(`/system-disks/${id}/upload`, data)
  },

  rebuildFromImage(id: string, imageId: string): Promise<DeleteDiskResponse> {
    return apiClient.post(`/system-disks/${id}/rebuild`, null, {
      params: { image_id: imageId }
    })
  }
}