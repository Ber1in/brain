<template>
  <div class="system-disks">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>裸金属云系统磁盘</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索ID、镜像名、SOC IP、裸金属服务器、创建人或描述"
              clearable
              style="width: 410px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-button type="primary" @click="$router.push('/system-disks/create')">
              创建云系统盘
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="filteredDisks" 
        v-loading="loading" 
        style="width: 100%"
        :default-sort="{ prop: 'mv200_ip', order: 'ascending' }"
      >
        <el-table-column prop="id" label="ID" width="200" />
        <el-table-column label="镜像名称">
          <template #default="{ row }">
            <template v-if="imageMap.get(row.image_id)">
              <div class="highlight-name">{{ getImageName(row.image_id) }}</div>
              <div class="highlight-ip">({{ row.mon_host }})</div>
            </template>
            <template v-else>
              <div class="highlight-deleted">源镜像已删除</div>
            </template>
          </template>
        </el-table-column>
        <el-table-column 
          prop="mv200_ip" 
          label="SOC IP"
          sortable
          :sort-method="ipSortMethod"
        >
          <template #default="{ row }">
            <div class="highlight-name">{{ getMV200Name(row.mv200_id) }}</div>
            <div class="highlight-ip">({{ row.mv200_ip }})</div>
          </template>
        </el-table-column>
        <el-table-column 
          label="裸金属服务器"
          sortable
          :sort-method="hostIpSortMethod"
        >
          <template #default="{ row }">
            <div class="highlight-name">{{ getHostName(row.mv200_id) }}</div>
            <div class="highlight-ip">({{ getHostIP(row.mv200_id) }})</div>
          </template>
        </el-table-column>
        <el-table-column prop="size_gb" label="磁盘大小(GB)" width="120">
          <template #default="{ row }">
            <span class="highlight-size">{{ row.size_gb }} GB</span>
          </template>
        </el-table-column>
        <el-table-column label="Flatten" width="120">
          <template #header>
            <span>Flatten</span>
            <el-tooltip 
              effect="dark" 
              content="已经flatten过的系统盘会脱离对镜像的依赖，性能会有所提升"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span :class="row.flatten ? 'highlight-true' : 'highlight-false'">
              {{ row.flatten ? '是' : '否' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column 
          prop="creator" 
          label="创建人" 
          width="90"
          sortable
        >
          <template #default="{ row }">
            <span class="highlight-creator">{{ row.creator }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button type="primary" link>
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="edit">
                    <el-icon><Edit /></el-icon>
                    <span>编辑</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="upload" divided>
                    <el-icon><Upload /></el-icon>
                    <span>保存为镜像</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="rebuild">
                    <el-icon><Refresh /></el-icon>
                    <span>重置镜像</span>
                  </el-dropdown-item>
                  <el-dropdown-item 
                    command="flatten" 
                    :disabled="row.flatten"
                  >
                    <el-tooltip 
                      v-if="row.flatten" 
                      effect="dark" 
                      content="当前云硬盘已经flatten" 
                      placement="top"
                    >
                      <div class="dropdown-item-content">
                        <el-icon><Operation /></el-icon>
                        <span>Flatten</span>
                      </div>
                    </el-tooltip>
                    <div v-else class="dropdown-item-content">
                      <el-icon><Operation /></el-icon>
                      <span>Flatten</span>
                    </div>
                  </el-dropdown-item>

                  <el-dropdown-item command="delete" divided class="danger-item">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 保存为镜像对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="保存系统盘为新镜像"
      width="500px"
    >
      <el-form :model="uploadForm" label-width="120px">
        <el-form-item label="名称">
          <el-input
            v-model="uploadForm.dest_name"
            placeholder="请输入新镜像名称（可选）"
            clearable
          />
          <div class="form-tip">如不填写，系统将自动生成镜像名称</div>
        </el-form-item>
        <el-form-item label="存储池">
          <el-input
            v-model="uploadForm.dest_pool"
            placeholder="请输入目标存储池（可选）"
            clearable
          />
          <div class="form-tip">如不填写，将保存到镜像默认存储池 images</div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入镜像描述（可选）"
            clearable
          />
        </el-form-item>
      </el-form>
      
      <div class="warning-message">
        <el-alert
          title="重要提示"
          type="warning"
          :closable="false"
          description="请确认该系统盘不在使用中，若系统盘依旧存在IO，保存的新镜像数据可能不完整。"
          show-icon
        />
      </div>
      
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload" :loading="uploadLoading">
          确认保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 重置镜像对话框 -->
    <el-dialog
      v-model="rebuildDialogVisible"
      title="重置系统盘镜像"
      width="500px"
    >
      <el-form :model="rebuildForm" label-width="120px">
        <el-form-item label="选择镜像">
          <el-select
            v-model="rebuildForm.image_id"
            placeholder="请选择镜像"
            style="width: 100%"
            clearable
          >
            <el-option
              v-for="image in images"
              :key="image.id"
              :label="`${image.name} (${image.mon_host})`"
              :value="image.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <div class="warning-message">
        <el-alert
          title="重要提示"
          type="warning"
          :closable="false"
          description="重置镜像操作，将会丢失当前系统盘内所有数据。此操作不可逆，请谨慎操作！"
          show-icon
        />
      </div>
      
      <template #footer>
        <el-button @click="rebuildDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRebuild" :loading="rebuildLoading" style="background-color: #e6a23c; border-color: #e6a23c;">
          确认重置
        </el-button>
      </template>
    </el-dialog>

    <!-- Flatten确认对话框 -->
    <el-dialog
      v-model="flattenDialogVisible"
      title="确认Flatten操作"
      width="400px"
    >
      <div class="warning-message">
        <el-alert
          title="重要提示"
          type="warning"
          :closable="false"
          description="Flatten操作完成后将不再依赖镜像，提升系统盘性能。但Flatten过程中磁盘性能可能有所下降"
          show-icon
        />
      </div>
      <div class="confirm-message">
        <p>确定要对系统磁盘 <strong>"{{ currentDisk?.id }}"</strong> 执行Flatten操作吗？</p>
      </div>
      
      <template #footer>
        <el-button @click="flattenDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmFlatten" 
          :loading="flattenLoading"
        >
          确认Flatten
        </el-button>
      </template>
    </el-dialog>

    <!-- 启动项认证对话框 -->
    <el-dialog
      v-model="bootAuthDialogVisible"
      title="操作系统身份认证"
      width="400px"
    >
      <div class="dialog-tip">
        <el-alert
          title="需要操作系统管理员权限来检查启动项状态"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>
      <el-form :model="bootAuthForm" label-width="80px">
        <el-form-item label="用户名" required>
          <el-input
            v-model="bootAuthForm.user"
            placeholder="请输入操作系统用户名"
            clearable
          />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input
            v-model="bootAuthForm.pwd"
            type="password"
            placeholder="请输入操作系统密码"
            clearable
            show-password
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="handleBootAuthCancel">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleBootAuthConfirm" 
          :loading="bootAuthLoading"
          :disabled="!bootAuthForm.user || !bootAuthForm.pwd"
        >
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { QuestionFilled, MoreFilled, Edit, Upload, Refresh, Delete, Operation, InfoFilled, Search } from '@element-plus/icons-vue'
import { systemDisksApi } from '@/api/system-disks'
import { imagesApi } from '@/api/images'
import { mv200Api } from '@/api/mv200'
import { bareApi } from '@/api/bare'
import type { SystemDisk, Image, MVServer, BareMetalServer, BootEntriesResponse } from '@/types/api'

const loading = ref(false)
const disks = ref<SystemDisk[]>([])
const images = ref<Image[]>([])
const mv200Servers = ref<MVServer[]>([])
const bares = ref<BareMetalServer[]>([])
const searchKeyword = ref('')

const uploadDialogVisible = ref(false)
const uploadLoading = ref(false)
const currentDisk = ref<SystemDisk | null>(null)
const uploadForm = reactive({
  dest_name: '',
  dest_pool: '',
  description: ''
})

const rebuildDialogVisible = ref(false)
const rebuildLoading = ref(false)
const rebuildForm = reactive({
  image_id: ''
})

const flattenDialogVisible = ref(false)
const flattenLoading = ref(false)

const bootAuthDialogVisible = ref(false)
const bootAuthLoading = ref(false)
const currentBareServer = ref<BareMetalServer | null>(null)
const bootAuthForm = reactive({
  user: '',
  pwd: ''
})
let bootAuthResolve: ((value: any) => void) | null = null

const ipSortMethod = (a: SystemDisk, b: SystemDisk) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const ipA = ipToNumber(a.mv200_ip);
  const ipB = ipToNumber(b.mv200_ip);
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

const hostIpSortMethod = (a: SystemDisk, b: SystemDisk) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const getHostIP = (disk: SystemDisk) => {
    const server = mv200Map.value.get(disk.mv200_id);
    if (!server || !server.bare_id) return '0.0.0.0';
    const bare_info = bareMap.value.get(server.bare_id);
    return bare_info ? bare_info.host_ip : '0.0.0.0';
  };
  
  const ipA = ipToNumber(getHostIP(a));
  const ipB = ipToNumber(getHostIP(b));
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

const ipSort = (ipA: string, ipB: string) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  return ipToNumber(ipA) - ipToNumber(ipB);
};

const imageMap = computed(() => {
  const map = new Map<string, string>()
  images.value.forEach(image => {
    map.set(image.id, image.name)
  })
  return map
})

const mv200Map = computed(() => {
  const map = new Map<string, MVServer>()
  mv200Servers.value.forEach(server => {
    map.set(server.id, server)
  })
  return map
})

const bareMap = computed(() => {
  const map = new Map<string, BareMetalServer>()
  bares.value.forEach(bare => {
    map.set(bare.id, bare)
  })
  return map
})

const filteredDisks = computed(() => {
  let filtered = disks.value
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = disks.value.filter(disk => {
      if (disk.id.toLowerCase().includes(keyword)) return true
      
      const imageName = getImageName(disk.image_id).toLowerCase()
      if (imageName.includes(keyword)) return true
      
      if (disk.mv200_ip.toLowerCase().includes(keyword)) return true
      
      const hostName = getHostName(disk.mv200_id).toLowerCase()
      const hostIP = getHostIP(disk.mv200_id).toLowerCase()
      if (hostName.includes(keyword) || hostIP.includes(keyword)) return true
      
      if (disk.creator && disk.creator.toLowerCase().includes(keyword)) return true
      
      if (disk.description && disk.description.toLowerCase().includes(keyword)) return true
      
      return false
    })
  }
  
  return filtered
})

const getImageName = (imageId: string) => {
  return imageMap.value.get(imageId) || "镜像已删除"
}

const getMV200Name = (serverId: string) => {
  const server = mv200Map.value.get(serverId)
  return server?.name || serverId
}

const getHostName = (mv200_id: string) => {
  const server = mv200Map.value.get(mv200_id)
  if (!server || !server.bare_id) return '-'
  
  const bare_info = bareMap.value.get(server.bare_id)
  return bare_info ? bare_info.name : '-'
}

const getHostIP = (mv200_id: string) => {
  const server = mv200Map.value.get(mv200_id)
  if (!server || !server.bare_id) return '-'
  
  const bare_info = bareMap.value.get(server.bare_id)
  return bare_info ? bare_info.host_ip : '-'
}

const loadData = async () => {
  loading.value = true
  try {
    const disksResponse = await systemDisksApi.getAll()
    
    if (!disksResponse || disksResponse.length === 0) {
      disks.value = []
      images.value = []
      mv200Servers.value = []
      bares.value = []
      return
    }
    
    const [imagesResponse, serversResponse, baresResponse] = await Promise.all([
      imagesApi.getAll(),
      mv200Api.getAll(),
      bareApi.getAll(),
    ])
    
    disks.value = disksResponse.sort((a, b) => ipSort(a.mv200_ip, b.mv200_ip))
    images.value = imagesResponse
    mv200Servers.value = serversResponse
    bares.value = baresResponse

  } catch (error) {
    ElMessage.error('加载数据失败')
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
}

const handleCommand = (command: string, disk: SystemDisk) => {
  switch (command) {
    case 'edit':
      handleEdit(disk)
      break
    case 'upload':
      handleUploadToImage(disk)
      break
    case 'rebuild':
      handleRebuildFromImage(disk)
      break
    case 'flatten':
      handleFlatten(disk)
      break
    case 'delete':
      handleDelete(disk)
      break
  }
}

const handleEdit = (disk: SystemDisk) => {
  window.location.href = `/system-disks/edit/${disk.id}`
}
const handleDelete = async (disk: SystemDisk) => {
  try {
    loading.value = true
    
    // 创建带复选框的确认对话框
    const isForceDelete = await new Promise<boolean>((resolve) => {
      ElMessageBox.confirm(
        `
          <div>
            <div style="margin-bottom: 16px;">确定要删除系统磁盘 ${disk.id}（关联SOC：${disk.mv200_ip}）吗？</div>
            <div style="display: flex; align-items: center; margin-bottom: 8px; padding: 8px; background: #fffbf0; border-radius: 4px;">
              <input type="checkbox" id="forceDeleteCheckbox" style="margin-right: 8px;">
              <label for="forceDeleteCheckbox" style="color: #b88230; font-weight: 500;">
                强制删除
              </label>
            </div>
            <div style="color: #e6a23c; font-size: 12px; line-height: 1.4;">
              注意：勾选强制删除将忽略系统盘使用状态，可能会影响正在运行的系统
            </div>
          </div>
        `,
        '确认删除',
        {
          type: 'warning',
          dangerouslyUseHTMLString: true,
          showCancelButton: true,
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          beforeClose: (action, instance, done) => {
            if (action === 'confirm') {
              const checkbox = document.getElementById('forceDeleteCheckbox') as HTMLInputElement
              const forceDelete = checkbox?.checked || false
              instance.confirmButtonLoading = true
              setTimeout(() => {
                done()
                instance.confirmButtonLoading = false
                resolve(forceDelete) // 在这里解析Promise
              }, 300)
            } else {
              done()
              resolve(false) // 取消时返回false
            }
          }
        }
      ).catch(() => {
        resolve(false) // 捕获取消操作
      })
    })
    
    // 如果是强制删除，直接执行删除操作，不检查使用状态
    if (isForceDelete) {
      const response = await systemDisksApi.delete(disk.id, isForceDelete)
      ElMessage.success('强制删除成功')
      
      if (response.efi_status === 1 || response.cloudinit_status === 1) {
        let warningMessage = '强制删除成功，但存在以下相关残留问题：\n'
        
        if (response.efi_status === 1) {
          warningMessage += '• 自动清理EFI启动项失败，需要重启系统完成自动清理\n'
        }
        
        if (response.cloudinit_status === 1) {
          warningMessage += '• cloud-init数据源清理失败\n'
        }
        
        ElMessage.warning({
          message: warningMessage,
          duration: 8000,
          showClose: true
        })
      }
      
      await loadData()
      return
    }
    
    // 如果不是强制删除，检查系统盘是否在使用
    let isInUse = false
    
    try {
      const mvServer = mv200Map.value.get(disk.mv200_id)
      if (mvServer && mvServer.bare_id) {
        const bareServer = bareMap.value.get(mvServer.bare_id)
        if (bareServer) {
          let bootEntriesResponse: BootEntriesResponse | null = null
          
          try {
            if (bareServer.os_user && bareServer.os_password) {
              bootEntriesResponse = await bareApi.getBootEntries(bareServer.id, true)
            } else {
              const authResult = await showBootAuthDialog(bareServer)
              if (!authResult) {
                loading.value = false
                return
              }
              bootEntriesResponse = authResult
            }
            
            const currentBootEntry = bootEntriesResponse.entries[bootEntriesResponse.current]
            const diskEfiUuid = disk.efi_uuid

            if (currentBootEntry && diskEfiUuid && currentBootEntry.includes(diskEfiUuid)) {
              isInUse = true
            }
            
          } catch (error) {
            console.warn('获取启动项失败:', error)
            const authResult = await showBootAuthDialog(bareServer)
            if (!authResult) {
              loading.value = false
              return
            }
            bootEntriesResponse = authResult
            
            const currentBootEntry = bootEntriesResponse.entries[bootEntriesResponse.current]
            const diskEfiUuid = disk.efi_uuid
            
            if (currentBootEntry && diskEfiUuid && currentBootEntry.includes(diskEfiUuid)) {
              isInUse = true
            }
          }
        }
      }
    } catch (error) {
      console.warn('检查启动项时出错:', error)
    }
    
    // 如果系统盘正在使用且不是强制删除，提示并返回
    if (isInUse) {
      ElMessage.error('当前云系统盘正在使用中，请切换操作系统后重试，或使用强制删除')
      loading.value = false
      return
    }
    
    // 执行删除操作（非强制删除）
    const response = await systemDisksApi.delete(disk.id, isForceDelete)
    
    ElMessage.success('删除成功')
    
    if (response.efi_status === 1 || response.cloudinit_status === 1) {
      let warningMessage = '删除成功，但存在以下相关残留问题：\n'
      
      if (response.efi_status === 1) {
        warningMessage += '• 自动清理EFI启动项失败，需要重启系统完成自动清理\n'
      }
      
      if (response.cloudinit_status === 1) {
        warningMessage += '• cloud-init数据源清理失败\n'
      }
      
      ElMessage.warning({
        message: warningMessage,
        duration: 8000,
        showClose: true
      })
    }
    
    await loadData()
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  } finally {
    loading.value = false
  }
}

const showBootAuthDialog = (server: BareMetalServer): Promise<any> => {
  return new Promise((resolve) => {
    currentBareServer.value = server
    bootAuthForm.user = ''
    bootAuthForm.pwd = ''
    bootAuthResolve = resolve
    bootAuthDialogVisible.value = true
  })
}

const handleBootAuthConfirm = async () => {
  if (!currentBareServer.value) return
  
  try {
    bootAuthLoading.value = true
    const response = await bareApi.getBootEntries(
      currentBareServer.value.id, 
      false,
      bootAuthForm.user, 
      bootAuthForm.pwd
    )
    
    // 保存成功的凭据到服务器
    try {
      await bareApi.updateServerCredentials(currentBareServer.value.id, {
        user: bootAuthForm.user,
        pwd: bootAuthForm.pwd
      })
      console.log('账号密码已保存')
      
      // 更新本地缓存
      if (bareMap.value.has(currentBareServer.value.id)) {
        const updatedServer = { ...currentBareServer.value }
        updatedServer.os_user = bootAuthForm.user
        updatedServer.os_password = bootAuthForm.pwd
        bareMap.value.set(currentBareServer.value.id, updatedServer)
      }
    } catch (saveError) {
      console.warn('保存账号密码失败:', saveError)
      // 不阻止主流程，只是记录警告
    }
    
    bootAuthDialogVisible.value = false
    if (bootAuthResolve) {
      bootAuthResolve(response)
    }
  } catch (error) {
    ElMessage.error('认证失败，请检查用户名和密码')
    console.error('认证失败:', error)
  } finally {
    bootAuthLoading.value = false
  }
}

const handleBootAuthCancel = () => {
  bootAuthDialogVisible.value = false
  if (bootAuthResolve) {
    bootAuthResolve(null)
  }
}

const handleUploadToImage = (disk: SystemDisk) => {
  currentDisk.value = disk
  uploadForm.dest_name = ''
  uploadDialogVisible.value = true
}

const confirmUpload = async () => {
  if (!currentDisk.value) return
  
  try {
    uploadLoading.value = true
    
    await systemDisksApi.uploadToImage(currentDisk.value.id, {
      dest_name: uploadForm.dest_name || undefined,
      dest_pool: uploadForm.dest_pool || undefined,
      description: uploadForm.description || undefined
    })
    
    ElMessage.success('保存为镜像操作已提交，请稍后查看镜像列表')
    uploadDialogVisible.value = false
    
  } catch (error) {
    ElMessage.error('保存为镜像失败')
    console.error('保存为镜像失败:', error)
  } finally {
    uploadLoading.value = false
  }
}

const handleRebuildFromImage = (disk: SystemDisk) => {
  currentDisk.value = disk
  rebuildForm.image_id = ''
  rebuildDialogVisible.value = true
}

const confirmRebuild = async () => {
  if (!currentDisk.value) return
  
  if (!rebuildForm.image_id) {
    ElMessage.warning('请选择镜像')
    return
  }
  
  try {
    rebuildLoading.value = true

    const response = await systemDisksApi.rebuildFromImage(currentDisk.value.id, rebuildForm.image_id)
    
    ElMessage.success('重置镜像操作已提交，系统盘将使用新镜像重建')
    if (response.efi_status === 1 || response.cloudinit_status === 1) {
      let warningMessage = '刷新成功，但存在以下相关残留问题：\n'
      
      if (response.efi_status === 1) {
        warningMessage += '• 自动刷新EFI启动项失败，需要重启系统完成自动刷新\n'
      }
      
      if (response.cloudinit_status === 1) {
        warningMessage += '• cloud-init数据源刷新失败\n'
      }
      
      ElMessage.warning({
        message: warningMessage,
        duration: 8000,
        showClose: true
      })
    }
    rebuildDialogVisible.value = false
    
    await loadData()
    
  } catch (error) {
    ElMessage.error('重置镜像失败')
    console.error('重置镜像失败:', error)
  } finally {
    rebuildLoading.value = false
  }
}

const handleFlatten = (disk: SystemDisk) => {
  currentDisk.value = disk
  flattenDialogVisible.value = true
}

const confirmFlatten = async () => {
  if (!currentDisk.value) return
  
  try {
    flattenLoading.value = true
    
    await systemDisksApi.flatten(currentDisk.value.id)
    
    ElMessage.success('Flatten操作已提交')
    flattenDialogVisible.value = false
    
    await loadData()
    
  } catch (error) {
    ElMessage.error('Flatten操作失败')
    console.error('Flatten操作失败:', error)
  } finally {
    flattenLoading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.warning-message {
  margin-top: 16px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.confirm-message {
  text-align: center;
  margin: 20px 0;
}

.confirm-message p {
  font-size: 16px;
  line-height: 1.5;
}

.confirm-message strong {
  color: #67c23a;
}

.dialog-tip {
  margin-bottom: 20px;
}

.highlight-name {
  color: #67c23a;
  font-weight: 600;
}

.highlight-ip {
  color: #409eff;
  font-weight: 500;
  font-family: 'Courier New', monospace;
}

.highlight-deleted {
  color: #c0c4cc;
  font-weight: 500;
  font-style: italic;
}

.highlight-size {
  color: #e6a23c;
  font-weight: 600;
}

.highlight-true {
  color: #67c23a;
  font-weight: 600;
}

.highlight-creator {
  color: #13c2c2;
  font-weight: 500;
}

.highlight-false {
  color: #f56c6c;
  font-weight: 600;
}

:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  color: #f56c6c;
  background-color: #fef0f0;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
}

:deep(.el-dropdown-menu__item.is-disabled) {
  color: #c0c4cc;
  cursor: not-allowed;
}

:deep(.el-dropdown-menu__item.is-disabled:hover) {
  background-color: transparent;
}

.dropdown-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

:deep(.el-dropdown-menu__item.is-disabled) {
  color: #c0c4cc;
  cursor: not-allowed;
}

:deep(.el-dropdown-menu__item.is-disabled:hover) {
  background-color: transparent;
}
</style>