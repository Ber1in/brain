import apiClient from './client'
import type { 
  CasesResponse, 
  DirNeedCollectRequest, 
  BranchAndTagResponse, 
  CheckoutRequest, 
  ExecuteResponse, 
  ExecuteRequest,
  CaseCombinationsResponse,
  CaseCombinationRequest
} from '@/types/api'

export const testApi = {
  getBranchAndTag(): Promise<BranchAndTagResponse> {
    return apiClient.get('/api/yuntester/branchs-tags', { cache: false })
  },

  switchBranchOrTag(request: CheckoutRequest): Promise<void> {
    return apiClient.post('/api/yuntester/switch', request)
  },

  collectTestCases(request: DirNeedCollectRequest): Promise<CasesResponse> {
    return apiClient.post('/api/yuntester/commands', {
      command: 'collect_cases',
      ...request
    })
  },
  
  executeTestCasesWithResponse(request: ExecuteRequest): Promise<ExecuteResponse> {
    return apiClient.post('/api/yuntester/execute-cases', request)
  },

  getExecuteHistory(): Promise<ExecuteResponse[]> {
    return apiClient.get('/api/yuntester/execute-history')
  },

  getCustomCombinations(): Promise<CaseCombinationsResponse[]> {
    return apiClient.get('/api/yuntester/custom-combinations')
  },

  saveCustomCombination(request: CaseCombinationRequest): Promise<void> {
    return apiClient.post('/api/yuntester/custom-combinations', request)
  },
  
  deleteCustomCombination(combinationId: string): Promise<void> {
    return apiClient.delete(`/api/yuntester/custom-combinations/${combinationId}`)
  },

  getDirectoryTree(): Promise<{ tree: any[] }> {
    return apiClient.get('/api/yuntester/directory-tree')
  },
}