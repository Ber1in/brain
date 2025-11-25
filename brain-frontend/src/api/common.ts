import apiClient from './client'
import type { TagsRequest, TagsResponse, RemoteFsResponse } from '@/types/api'

export const tagApi = {
  // 获取所有标签
  getTags(): Promise<TagsResponse> {
    return apiClient.get('/api/tags')
  },

  // 创建标签
  createTag(data: TagsRequest): Promise<void> {
    return apiClient.post('/api/tag', data)
  },

  // 删除标签
  deleteTag(tagId: string): Promise<void> {
    return apiClient.delete(`/api/tag/${tagId}`)
  },
}

export const remotefsApi = {
  listRemoteDir(path: string): Promise<RemoteFsResponse[]> {
    return apiClient.get('/api/remotefs/list_dir', {
      params: { path }
    })
  },
}