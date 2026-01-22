import apiClient from './client'
import type {
  TagsRequest,
  TagsResponse,
  RemoteFsResponse,
  TaskStatusResponse,
  AppConfig,
  FilteringConditions,
  OperationFilterRequest,
  OperationResponse,
  InstallDetailResponse,
  RbdDetailResponse
} from '@/types/api'

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

export const operationApi = {
  getOperationalAudit(params?: OperationFilterRequest): Promise<OperationResponse[]> {
    return apiClient.get('/api/operational_audit', { params });
  },
};

export const mcrApi = {
  getInstallDetail(path: string): Promise<InstallDetailResponse[]> {
    return apiClient.get('/api/mcr_install_detail', { params: { path } })
  }
}

export const rbdApi = {
  getRbdDetail(rbd_path: string, gws: string): Promise<RbdDetailResponse[]> {
    return apiClient.get('/api/rbd_detail', { params: { rbd_path, gws } });
  }
}