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

export interface MVServer {
  id: string
  name: string
  ip_address: string
  description?: string
  host_ip?: string
}

export interface MVServerCreate {
  name: string
  ip_address: string
  description?: string
  host_ip?: string
}

export interface MVServerUpdate {
  name?: string
  ip_address?: string
  description?: string
  host_ip?: string
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