import apiClient from './client'
import type { 
  CasesResponse, 
  DirNeedCollectRequest, 
  BranchAndTagResponse, 
  CheckoutRequest, 
  ExecuteResponse, 
  ExecuteListResponse, 
  ExecuteRequest,
  CaseCombinationsResponse,
  CaseCombinationRequest
} from '@/types/api'

export const testApi = {
  getBranchAndTag(): Promise<BranchAndTagResponse> {
    return apiClient.get('/api/qa_auto/branchs-tags', { cache: false })
  },

  switchBranchOrTag(request: CheckoutRequest): Promise<void> {
    return apiClient.post('/api/qa_auto/switch', request)
  },

  collectTestCases(request: DirNeedCollectRequest): Promise<CasesResponse> {
    return apiClient.post('/api/qa_auto/commands', {
      command: 'collect_cases',
      ...request
    })
  },
  
  executeTestCasesWithResponse(request: ExecuteRequest): Promise<ExecuteResponse> {
    return apiClient.post('/api/qa_auto/execute-cases', request)
  },

  getExecuteHistory(): Promise<ExecuteListResponse> {
    return apiClient.get('/api/qa_auto/execute-history')
  },

  getCustomCombinations(): Promise<CaseCombinationsResponse[]> {
    return apiClient.get('/api/qa_auto/custom-combinations')
  },

  saveCustomCombination(request: CaseCombinationRequest): Promise<void> {
    return apiClient.post('/api/qa_auto/custom-combinations', request)
  },
  
  deleteCustomCombination(combinationId: string): Promise<void> {
    return apiClient.delete(`/api/qa_auto/custom-combinations/${combinationId}`)
  },

  getDirectoryTree(): Promise<{ tree: any[] }> {
    return apiClient.get('/api/qa_auto/directory-tree')
  },
}