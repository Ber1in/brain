import { createCrudApi } from './crud-factory'
import apiClient from './client'
import type { MVServer, MVServerCreate, MVServerUpdate, MCRRequest, InterfaceCreate, InterfaceInfo, OvsflowRequest, XscnetInfo, ControllerInfo, DeleteDiskResponse } from '@/types/api'

// 使用 crud-factory 创建标准 CRUD 方法
const baseCrud = createCrudApi<MVServer, MVServerCreate, MVServerUpdate>({
  endpoint: 'mv-servers',
  disableCache: true, // MV200 数据频繁变动，禁用缓存
})

export const mv200Api = {
  // 标准 CRUD 方法
  getAll: baseCrud.getAll,
  getById: baseCrud.getById,
  create: baseCrud.create,
  update: baseCrud.update,
  delete: baseCrud.delete,
  getPaginated: baseCrud.getPaginated,

  // MV200 特有的扩展方法
  
  /**
   * 升级 MCR
   */
  upgradeMcr(serverId: string, mcrFilePath: string): Promise<void> {
    const data: MCRRequest = {
      path: mcrFilePath,
      update_options: '--force --ovs-dpdk --spdk --yun-upgrade-option "--dpu-blk-oprom --best-try" --dpuagent'
    }
    return apiClient.post(`/mv-servers/${serverId}/update_mcr`, data)
  },

  /**
   * 创建 XSC
   */
  createXsc(mv200_id: string, data: InterfaceCreate): Promise<InterfaceInfo> {
    return apiClient.post(`/mv-servers/${mv200_id}/xsc`, data)
  },

  /**
   * 添加 XSC OVS 流表
   */
  addXscOvsFlow(mv200_id: string, uuid: number, data: OvsflowRequest): Promise<void> {
    return apiClient.post(`/mv-servers/${mv200_id}/xsc/${uuid}/flowtables`, data)
  },

  /**
   * 移除 XSC OVS 流表
   */
  removeXscOvsFlow(mv200_id: string, uuid: number): Promise<void> {
    return apiClient.delete(`/mv-servers/${mv200_id}/xsc/${uuid}/flowtables`)
  },

  /**
   * 删除 XSC
   */
  deleteXsc(mv200_id: string, uuid: number): Promise<void> {
    return apiClient.delete(`/mv-servers/${mv200_id}/xsc/${uuid}`)
  },

  /**
   * 获取所有 XSC
   */
  getAllXsc(mv200Id: string, uuid?: number): Promise<XscnetInfo[]> {
    const params: Record<string, any> = {}
    if (uuid !== undefined && uuid !== null) {
      params.uuid = uuid
    }
    return apiClient.get(`/mv-servers/${mv200Id}/xsc`, { params })
  },

  /**
   * 获取系统磁盘
   */
  getSystemDisks(mv200Id: string): Promise<ControllerInfo[]> {
    return apiClient.get(`/mv-servers/${mv200Id}/systemdisks`)
  },

  /**
   * 创建系统磁盘
   */
  createSystemDisk(mv200Id: string, data: any): Promise<DeleteDiskResponse> {
    return apiClient.post(`/mv-servers/${mv200Id}/system-disks/create`, data)
  },

  /**
   * 删除系统磁盘
   */
  deleteSystemDisk(serverId: string, data: {
    uuid: string;
    rbd_path: string;
    mon_hosts: string;
    bare_id: string;
    last_disk: boolean;
  }): Promise<DeleteDiskResponse> {
    return apiClient.post(`/mv-servers/${serverId}/system-disks/delete`, data)
  },

  /**
   * 删除 Cloud Init
   */
  deleteCloudInit(serverId: string): Promise<void> {
    return apiClient.delete(`/mv-servers/${serverId}/cloud-init`)
  }
}