export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token: string
}

export interface LoginCredentials {
  username: string
  password: string
  grant_type?: string
  scope?: string
  client_id?: string
  client_secret?: string
}

export interface Image {
  id: string
  name: string
  ceph_location: string
  mon_host: string
  description?: string
}

export interface ImageCreate {
  name: string
  ceph_location: string
  mon_host: string
  description?: string
}

export interface ImageUpdate {
  name?: string
  ceph_location?: string
  mon_host?: string
  description?: string
}

export interface MCRVersionInfo {
  driver: string;
  firmware: string;
  dpuagent: string;
}

export interface MVServer {
  id: string
  name: string
  ip_address: string
  description?: string
  sn?: string
  mac?: string
  gateway?: string
  nic_sn?: string
  versions?: MCRVersionInfo;
  clouddisk_enable: boolean;
  recovery_mode?: string
}

export interface MVServerCreate {
  name: string
  ip_address: string
  description?: string
}

export interface MVServerUpdate {
  name?: string
  ip_address?: string
  description?: string
  auto: boolean;
  clouddisk_enable: boolean;
  recovery_mode?: string
}

export interface SystemDisk {
  id: string
  image_id: string
  mv200_id: string
  mv200_ip: string
  size_gb: number
  mon_host: string
  rbd_path: string
  blk_id: number
  description?: string
  creator?: string
  efi_uuid?: string
}

export interface SystemDiskCreate {
  image_id: string
  mv200_id: string
  size_gb: number
  description?: string
}

export interface SystemDiskUpdate {
  description?: string
}

export interface SystemUser {
  name: string
  password: string
}

export interface BareMetalCreate {
  system_disk: SystemDiskCreate
  system_user: SystemUser
}

export interface ValidationError {
  loc: Array<string | number>
  msg: string
  type: string
}

export interface HTTPValidationError {
  detail: ValidationError[]
}

export interface BareMetalServer {
  id: string
  name: string
  description?: string
  host_ip: string
  gateway: string
  mac: string
}

export interface BareMetalServerCreate {
  name: string
  description?: string
  host_ip: string
  gateway: string
  mac: string
}

export interface BareMetalServerUpdate {
  name?: string
  description?: string
  host_ip?: string
  gateway?: string
  mac?: string
  os_user?: string;
  os_password?: string;
}

export interface CredentialsVerifyResponse {
  valid: boolean;
  has_saved_credentials: boolean;
  message: string;
}

export interface ServerCredentials {
  user: string;
  pwd: string;
}

export interface UploadToImage {
  dest_name?: string
  dest_pool?: string
  description?: string
}

export interface BootEntriesResponse {
  entries: Record<string, string>
  current: string
  next?: string | null
  default?: string
}

export interface DeleteDiskResponse {
  efi_status: number
  cloudinit_status: number
}

// XSC网口相关类型
export interface InterfaceInfo {
  mv200_id: string
  ip: string
  vlan_tag: number
  gateway: string
  mtu?: number
  mac?: string
  dns?: string[]
  description?: string
  id: string
  ifname?: string
  creator?: string
}

export interface InterfaceCreate {
  mv200_id: string
  ip: string
  vlan_tag: number
  gateway: string
  mtu?: number
  mac?: string
  dns?: string[]
  description?: string
}

export interface InterfaceUpdate {
  id: string
  description?: string
}

export interface InterfaceDelete {
  mv200_id: string
  id: string
}

// 在现有类型定义的基础上添加以下内容

export interface BMC {
  ip?: string | null  // 可以为空，后端会自动生成
  hostname: string
}

export interface DeviceRequest {
  sn?: string
  ip: string  // 或者使用 IPv4Address 如果已定义
  username: string
  password: string
}

export interface DeviceResponse {
  sn?: string
  ip: string
  username: string
  vendor?: string
  product?: string
  mac?: string
  gateway?: string
  arch?: string
  cpu_vendor?: string
  cpu_mode?: string
}

export interface NicInfo {
  mac?: string
  bdf?: string
  iface?: string
}

export interface NicBase {
  type: string
  sn: string
}

export interface AIDPU_Nic {
  type: string
  nic_info?: Array<NicInfo>
  sn: string
  soc_ip: string
  aidpu_sn?: string
  firmware_version?: string
  nic_sn?: string
  management_ip?: string
}

export interface ServerDetailResponse {
  bmc: BMC
  device: DeviceResponse
  nics?: Array<NicBase | AIDPU_Nic>
  tags?: string[]
  notes?: string
  user?: string
  time?: string
  created_at?: string
  updated_at?: string
  id?: string
}

export interface ServerRequest {
  bmc: BMC
  device: DeviceRequest
  nics?: Array<NicBase | AIDPU_Nic>
  tags?: string[]
  notes?: string
}

export interface ServerUpdateRequest {
  auto?: boolean
  device: DeviceRequest
  bmc: BMC
  nics?: Array<NicBase | AIDPU_Nic>
  tags?: string[]
  notes?: string
  time?: string
}

export interface ServerCredentials {
  user: string
  pwd: string
}

export interface TagsRequest {
  name: string
}

export interface TagResponse {
  id: string
  name: string
  color: string
}

export interface TagsResponse {
  tags: TagResponse[]
}

export interface CheckoutRequest {
  branch?: string | null;
  tag?: string | null;
}

export interface ExecuteResponse {
  url?: string
  time?: string
  current?: string
  latest_commit?: string
}

export interface BranchAndTagResponse {
  branchs?: string[] | null;
  tags?: string[] | null;
  current: string
  latest_commit: string
}

export interface DirNeedCollectRequest {
  dirs: string[];
}

export interface CasesResponse {
  cases?: string[] | null;
}

export interface CaseNicInfo {
  iface: string
  bdf: string
  type?: string
}

export interface Server {
  device_id: string;
  nics?: CaseNicInfo[];
}

export interface ExecuteRequest {
  cases?: string[];
  servers?: Server[];
}

export interface CaseCombinationsResponse {
  id: string;
  name: string;
  created_at: string;
  cases?: string[];
}

export interface CaseCombinationRequest {
  name: string;
  cases?: string[];
}