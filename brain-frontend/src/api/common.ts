import apiClient from './client'
import type { TagsRequest, TagsResponse, RemoteFsResponse, TaskStatusResponse, AppConfig, FilteringConditions } from '@/types/api'

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

export const tasksApi = {
  getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    return apiClient.get(`/api/tasks/${taskId}`)
  }
}

export const settingsApi = {
  // Get full settings
  getSettings(): Promise<AppConfig> {
    return apiClient.get('/api/settings')
  },

  // Patch partial settings
  patchSettings(data: AppConfig): Promise<AppConfig> {
    return apiClient.patch('/api/settings', data)
  }
}

export const filterApi = {
  getFilteringConditions(): Promise<FilteringConditions> {
    return apiClient.get(`/api/filtering_conditions`)
  },

  updateFilteringConditions(data: FilteringConditions): Promise<FilteringConditions> {
    return apiClient.post('/api/filtering_conditions', data)
  }
}