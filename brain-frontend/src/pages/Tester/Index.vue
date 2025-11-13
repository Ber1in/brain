<template>
  <div class="qa-platform">
    <el-card>
      <template #header>
        <div class="card-header">
          <h2>质量保证平台</h2>
        </div>
      </template>

      <!-- 代码版本选择和执行历史区域 -->
      <div class="top-section">
        <!-- 代码版本选择区域 -->
        <div class="version-section">
          <div class="section-title">
            <el-icon><Setting /></el-icon>
            <span>代码版本选择</span>
          </div>
          
          <!-- 当前版本信息 -->
          <div class="current-version" v-if="currentVersionDisplay">
            <el-tag type="info" class="current-tag">
              <el-icon><Position /></el-icon>
              本地{{ currentVersionDisplay }}
            </el-tag>
          </div>
          <div class="current-version" v-if="latestCommit">
            <el-tooltip :content="latestCommit" placement="top">
              <el-tag type="info" class="current-tag">
                <el-icon><Position /></el-icon>
                本地最新commit id: 
                <span class="commit-hash">{{ formatCommitHash(latestCommit) }}</span>
              </el-tag>
            </el-tooltip>
          </div>
          <div class="version-control">
            <div class="mode-selector">
              <el-radio-group v-model="checkoutMode" @change="handleModeChange">
                <el-radio-button label="branch">分支</el-radio-button>
                <el-radio-button label="tag">标签</el-radio-button>
              </el-radio-group>
            </div>

            <div class="version-selection">
              <!-- 分支选择 -->
              <div v-if="checkoutMode === 'branch'" class="selection-group">
                <el-select 
                  v-model="selectedBranch" 
                  placeholder="请选择仓库分支或输入分支名称" 
                  style="width: 300px"
                  @change="handleBranchChange"
                  :loading="branchLoading"
                  filterable
                  clearable
                  :filter-method="filterBranch"
                  :reserve-keyword="false"
                >
                  <el-option-group label="分支列表">
                    <el-option 
                      v-for="branch in filteredBranchList" 
                      :key="branch" 
                      :label="branch" 
                      :value="branch"
                    >
                      <div class="branch-option">
                        <span>{{ branch }}</span>
                        <el-tag 
                          v-if="branch === currentBranch" 
                          size="small" 
                          type="success"
                          class="current-indicator"
                        >
                          当前
                        </el-tag>
                      </div>
                    </el-option>
                  </el-option-group>
                </el-select>
                <div class="selection-info" v-if="selectedBranch">
                  <el-tag type="success">
                    <el-icon><Check /></el-icon>
                    已选择分支: {{ selectedBranch }}
                  </el-tag>
                </div>
              </div>

              <!-- 标签选择 -->
              <div v-else class="selection-group">
                <el-select 
                  v-model="selectedTag" 
                  placeholder="请选择仓库标签或输入标签名称" 
                  style="width: 300px"
                  @change="handleTagChange"
                  :loading="tagLoading"
                  filterable
                  clearable
                  :filter-method="filterTag"
                  :reserve-keyword="false"
                >
                  <el-option-group label="标签列表">
                    <el-option 
                      v-for="tag in filteredTagList" 
                      :key="tag" 
                      :label="tag" 
                      :value="tag"
                    >
                      <div class="tag-option">
                        <span>{{ tag }}</span>
                        <el-tag 
                          v-if="tag === currentTag" 
                          size="small" 
                          type="success"
                          class="current-indicator"
                        >
                          当前
                        </el-tag>
                      </div>
                    </el-option>
                  </el-option-group>
                </el-select>
                <div class="selection-info" v-if="selectedTag">
                  <el-tag type="warning">
                    <el-icon><Check /></el-icon>
                    已选择标签: {{ selectedTag }}
                  </el-tag>
                </div>
              </div>

              <el-button 
                type="primary" 
                @click="handleCheckout" 
                :loading="checkoutLoading"
                :disabled="!canCheckout"
              >
                <el-icon><Switch /></el-icon>
                更新代码
              </el-button>
            </div>
          </div>
        </div>

        <!-- 执行历史区域 -->
        <div class="history-section">
          <div class="section-title">
            <el-icon><Clock /></el-icon>
            <span>测试执行历史</span>
            <el-button 
              type="primary" 
              @click="loadExecuteHistory" 
              :loading="historyLoading"
              size="small"
              class="refresh-btn"
            >
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
          
          <div class="history-content">
            <el-table 
              :data="executeHistory" 
              empty-text="暂无执行历史"
              v-loading="historyLoading"
              style="width: 100%"
              height="300"
            >
              <el-table-column prop="time" label="执行时间" width="160" sortable />
              <el-table-column prop="current" label="执行分支/标签" width="250">
                <template #default="{ row }">
                  <el-tooltip v-if="row.current && row.current.length > 30" :content="row.current" placement="top">
                    <el-tag size="small" type="info" class="current-tag">
                      {{ formatBranchTag(row.current) }}
                    </el-tag>
                  </el-tooltip>
                  <el-tag v-else-if="row.current" size="small" type="info" class="current-tag">
                    {{ row.current }}
                  </el-tag>
                  <span v-else class="no-data">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="commit" label="执行时Commit" width="140">
                <template #default="{ row }">
                  <el-tooltip v-if="row.commit" :content="row.commit" placement="top">
                    <el-tag size="small" type="success" class="commit-tag">
                      {{ formatCommitHash(row.commit) }}
                    </el-tag>
                  </el-tooltip>
                  <span v-else class="no-data">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="url" label="执行结果" width="140">
                <template #default="{ row }">
                  <el-link 
                    v-if="row.url" 
                    :href="row.url" 
                    target="_blank" 
                    type="primary"
                    :underline="false"
                  >
                    <el-icon><Link /></el-icon>
                    查看测试报告
                  </el-link>
                  <span v-else class="no-data">-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>
      </div>

      <!-- 测试用例收集区域 -->
      <div class="collect-section">
        <div class="section-title">
          <el-icon><Collection /></el-icon>
          <span>测试用例收集</span>
        </div>

        <div class="directory-config">
          <div class="dir-input-group">
            <el-input 
              v-model="newDirectory" 
              placeholder="输入测试用例目录路径，如: products/api_coverage"
              @keyup.enter="addDirectory"
              style="width: 500px"
            >
              <template #append>
                <el-button @click="addDirectory" :disabled="!newDirectory.trim()">
                  <el-icon><Plus /></el-icon>
                  添加
                </el-button>
              </template>
            </el-input>
          </div>

          <div class="dir-list" v-if="directories.length > 0">
            <div class="dir-list-title">待扫描目录:</div>
            <div class="dir-tags">
              <el-tag
                v-for="(dir, index) in directories"
                :key="index"
                closable
                @close="removeDirectory(index)"
                type="info"
                class="dir-tag"
              >
                {{ dir }}
              </el-tag>
            </div>
          </div>

          <el-button 
            type="success" 
            @click="handleCollectTestCases" 
            :loading="collectLoading"
            :disabled="directories.length === 0"
            class="collect-btn"
          >
            <el-icon><Search /></el-icon>
            扫描测试用例
          </el-button>
        </div>

        <!-- 测试用例选择区域 - 一分为二 -->
        <div class="test-cases-selection" v-if="showTestCasesTree">
          <div class="selection-header">
            <h3>测试用例管理</h3>
            <el-button 
              type="primary" 
              :disabled="rightTestCases.length === 0"
              @click="handleRunSelected"
              class="run-btn"
            >
              <el-icon><VideoPlay /></el-icon>
              运行用例 ({{ rightTestCases.length }})
            </el-button>
          </div>

          <div class="selection-container">
            <!-- 左侧：所有用例树 -->
            <div class="left-panel">
              <div class="panel-header">
                <h4>所有测试用例 ({{ leftTotalCount }})</h4>
                <div class="filter-input">
                    <el-input
                    v-model="leftFilterText"
                    placeholder="过滤用例..."
                    clearable
                    size="small"
                    style="width: 150px"
                    :prefix-icon="Search"
                    />
                </div>
                <span class="count-info">已选择: {{ leftSelectedCount }} 个</span>
              </div>
              <div class="tree-container-wrapper">
                <div class="tree-container">
                  <el-tree
                    ref="leftTreeRef"
                    :data="filteredLeftTestCasesTree"
                    node-key="id"
                    show-checkbox
                    :default-expand-all="false"
                    :expand-on-click-node="true"
                    @check="handleLeftTreeCheck"
                    v-loading="treeLoading"
                    :filter-node-method="filterNode"
                  >
                    <template #default="{ node, data }">
                      <div class="tree-node">
                        <div class="node-content">
                          <el-icon v-if="data.type === 'directory'" class="node-icon">
                            <Folder />
                          </el-icon>
                          <el-icon v-else-if="data.type === 'file'" class="node-icon">
                            <Document />
                          </el-icon>
                          <el-icon v-else-if="data.type === 'class'" class="node-icon">
                            <Collection />
                          </el-icon>
                          <el-icon v-else class="node-icon">
                            <Position />
                          </el-icon>
                          
                          <span class="node-label">{{ data.label }}</span>
                          
                          <el-tag 
                            v-if="data.testCaseCount && data.type !== 'testCase'" 
                            size="small" 
                            type="info"
                            class="count-tag"
                          >
                            {{ data.testCaseCount }}
                          </el-tag>
                        </div>
                      </div>
                    </template>
                  </el-tree>
                </div>
              </div>
            </div>

            <!-- 中间：操作按钮 -->
            <div class="transfer-buttons">
              <el-button 
                type="primary" 
                @click="moveToRight" 
                :disabled="leftSelectedCount === 0"
                class="transfer-btn"
              >
                <el-icon><ArrowRight /></el-icon>
                添加({{ leftSelectedCount }})
              </el-button>
              <el-button 
                @click="moveToLeft" 
                :disabled="rightSelectedCount === 0"
                class="transfer-btn"
              >
                <el-icon><ArrowLeft /></el-icon>
                移除({{ rightSelectedCount }})
              </el-button>
            </div>

            <!-- 右侧：已添加用例树形结构 -->
            <div class="right-panel">
              <div class="panel-header">
                <h4>已添加用例 ({{ rightTestCases.length }})</h4>
                <div class="filter-input">
                    <el-input
                    v-model="rightFilterText"
                    placeholder="过滤用例..."
                    clearable
                    size="small"
                    style="width: 150px"
                    :prefix-icon="Search"
                    />
                </div>
                <span class="count-info">已选择: {{ rightSelectedCount }} 个</span>
              </div>
              <div class="tree-container-wrapper">
                <div class="tree-container">
                  <el-tree
                    ref="rightTreeRef"
                    :data="filteredRightTestCasesTree"
                    node-key="id"
                    show-checkbox
                    :default-expand-all="false"
                    :expand-on-click-node="true"
                    @check="handleRightTreeCheck"
                    :filter-node-method="filterNode"
                  >
                    <template #default="{ node, data }">
                      <div class="tree-node">
                        <div class="node-content">
                          <el-icon v-if="data.type === 'directory'" class="node-icon">
                            <Folder />
                          </el-icon>
                          <el-icon v-else-if="data.type === 'file'" class="node-icon">
                            <Document />
                          </el-icon>
                          <el-icon v-else-if="data.type === 'class'" class="node-icon">
                            <Collection />
                          </el-icon>
                          <el-icon v-else class="node-icon">
                            <Position />
                          </el-icon>
                          
                          <span class="node-label">{{ data.label }}</span>
                          
                          <el-tag 
                            v-if="data.testCaseCount && data.type !== 'testCase'" 
                            size="small" 
                            type="info"
                            class="count-tag"
                          >
                            {{ data.testCaseCount }}
                          </el-tag>
                          
                          <!-- 移除按钮 -->
                          <el-button
                            v-if="data.type === 'testCase' || data.type === 'class'"
                            link
                            type="danger"
                            @click.stop="removeFromRight(data)"
                            class="remove-btn"
                          >
                            <el-icon><Delete /></el-icon>
                          </el-button>
                        </div>
                      </div>
                    </template>
                  </el-tree>
                </div>
                <div class="scroll-indicator">
                  <div class="scroll-track">
                    <div class="scroll-thumb"></div>
                  </div>
                  <span>左右滑动查看更多</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 切换代码版本确认对话框 -->
    <el-dialog
      v-model="checkoutDialogVisible"
      :title="`切换代码版本 - ${checkoutMode === 'branch' ? '分支' : '标签'}`"
      width="500px"
      class="checkout-dialog"
      :close-on-click-modal="false"
    >
      <div class="dialog-content">
        <el-alert
          :title="`确定要切换到 ${checkoutMode === 'branch' ? '分支' : '标签'} ${
            checkoutMode === 'branch' ? selectedBranch : selectedTag
          } 吗？`"
          type="warning"
          :closable="false"
          show-icon
        />
        <div class="confirm-message">
          <p>这将执行以下操作：</p>
          <ul class="operation-list">
            <li>切换到 {{ checkoutMode === 'branch' ? '分支' : '标签' }} <strong>{{ checkoutMode === 'branch' ? selectedBranch : selectedTag }}</strong></li>
            <li>拉取最新的代码</li>
          </ul>
          <div class="current-warning" v-if="isSwitchingToCurrent">
            <el-alert
              title="您选择的是当前版本，无需切换"
              type="info"
              :closable="false"
              show-icon
            />
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="checkoutDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handleCheckoutConfirm" 
            :loading="checkoutLoading"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            确认更新
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox, ElTree } from 'element-plus'
import { 
  Setting, 
  Collection, 
  Plus, 
  Search,
  Switch,
  VideoPlay,
  Folder,
  Document,
  Position,
  Loading,
  Check,
  ArrowRight,
  ArrowLeft,
  Delete,
  Clock,
  Link,
  Refresh
} from '@element-plus/icons-vue'
import { testApi } from '@/api/tester'
import type { BranchAndTagResponse, CheckoutRequest, CasesResponse, ExecuteResponse, ExecuteListResponse } from '@/types/api'

// 响应式数据
const checkoutMode = ref<'branch' | 'tag'>('branch')
const selectedBranch = ref('')
const selectedTag = ref('')
const branchList = ref<string[]>([])
const tagList = ref<string[]>([])
const currentBranch = ref('')
const currentTag = ref('')
const latestCommit = ref('')
const branchSearchText = ref('')
const tagSearchText = ref('')
const newDirectory = ref('')
const leftFilterText = ref('')
const rightFilterText = ref('')
const directories = ref<string[]>(['products/api_coverage'])

// 测试用例相关数据
const collectedCases = ref<string[]>([]) // 所有收集到的用例
const leftTestCasesTree = ref<any[]>([]) // 左侧树形数据
const rightTestCases = ref<any[]>([]) // 右侧已添加用例
const leftSelectedCases = ref<string[]>([]) // 左侧选中的用例
const rightTestCasesTree = ref<any[]>([]) // 右侧树形数据

const leftTreeRef = ref<InstanceType<typeof ElTree>>()
const rightTreeRef = ref<InstanceType<typeof ElTree>>()
const showTestCasesTree = ref(false)

// 加载状态
const branchLoading = ref(false)
const tagLoading = ref(false)
const checkoutLoading = ref(false)
const collectLoading = ref(false)
const checkoutDialogVisible = ref(false)
const treeLoading = ref(false)
const executeHistory = ref<ExecuteResponse[]>([])
const historyLoading = ref(false)

// 计算属性
const canCheckout = computed(() => {
  return (checkoutMode.value === 'branch' && selectedBranch.value) ||
         (checkoutMode.value === 'tag' && selectedTag.value)
})

const currentVersionDisplay = computed(() => {
  if (currentBranch.value) {
    return `当前分支: ${currentBranch.value}`
  } else if (currentTag.value) {
    return `当前标签: ${currentTag.value}`
  }
  return ''
})

const filteredBranchList = computed(() => {
  if (!branchSearchText.value) {
    return branchList.value
  }
  return branchList.value.filter(branch => 
    branch.toLowerCase().includes(branchSearchText.value.toLowerCase())
  )
})

const filteredTagList = computed(() => {
  if (!tagSearchText.value) {
    return tagList.value
  }
  return tagList.value.filter(tag => 
    tag.toLowerCase().includes(tagSearchText.value.toLowerCase())
  )
})

const isSwitchingToCurrent = computed(() => {
  if (checkoutMode.value === 'branch') {
    return selectedBranch.value === currentBranch.value
  } else {
    return selectedTag.value === currentTag.value
  }
})

// 计算属性 - 修改为只计算叶子节点
const leftSelectedCount = computed(() => {
  if (!leftTreeRef.value) return 0
  
  // 获取所有选中的节点
  const allCheckedNodes = leftTreeRef.value.getCheckedNodes(false, true) || []
  
  // 只计算没有子节点的叶子节点，且类型为 'class' 或 'testCase'
  const leafNodes = allCheckedNodes.filter((node: any) => {
    const isLeafNode = !node.children || node.children.length === 0
    const isTestCaseType = node.type === 'testCase' || node.type === 'class'
    return isLeafNode && isTestCaseType
  })
  
  return leafNodes.length
})

const leftTotalCount = computed(() => {
  return collectedCases.value.length - rightTestCases.value.length
})

// 右侧选中数量
const rightSelectedCount = computed(() => {
  if (!rightTreeRef.value) return 0
  
  const allCheckedNodes = rightTreeRef.value.getCheckedNodes(false, true) || []
  const leafNodes = allCheckedNodes.filter((node: any) => {
    const isLeafNode = !node.children || node.children.length === 0
    const isTestCaseType = node.type === 'testCase' || node.type === 'class'
    return isLeafNode && isTestCaseType
  })
  
  return leafNodes.length
})

// 方法
const handleModeChange = () => {
  selectedBranch.value = ''
  selectedTag.value = ''
  branchSearchText.value = ''
  tagSearchText.value = ''
}

const handleBranchChange = (value: string) => {
  selectedTag.value = ''
  branchSearchText.value = ''
}

const handleTagChange = (value: string) => {
  selectedBranch.value = ''
  tagSearchText.value = ''
}

const filterBranch = (query: string) => {
  branchSearchText.value = query
}

const filterTag = (query: string) => {
  tagSearchText.value = query
}

const handleCheckout = () => {
  checkoutDialogVisible.value = true
}

const handleCheckoutConfirm = async () => {
  try {
    checkoutLoading.value = true
    
    const request: CheckoutRequest = {
      branch: checkoutMode.value === 'branch' ? selectedBranch.value : null,
      tag: checkoutMode.value === 'tag' ? selectedTag.value : null
    }
    
    await testApi.switchBranchOrTag(request)
    
    ElMessage.success(`已成功更新到 ${checkoutMode.value === 'branch' ? '分支' : '标签'} ${
      checkoutMode.value === 'branch' ? selectedBranch.value : selectedTag.value
    } 的最新代码`)
    
    checkoutDialogVisible.value = false
    
    if (checkoutMode.value === 'branch') {
      currentBranch.value = selectedBranch.value
      currentTag.value = ''
    } else {
      currentTag.value = selectedTag.value
      currentBranch.value = ''
    }
    
    // 清空测试用例列表
    collectedCases.value = []
    leftTestCasesTree.value = []
    rightTestCases.value = []
    leftSelectedCases.value = []
    rightTestCasesTree.value = []
    showTestCasesTree.value = false
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新代码版本失败')
  } finally {
    checkoutLoading.value = false
  }
}

const addDirectory = () => {
  const dir = newDirectory.value.trim()
  if (dir && !directories.value.includes(dir)) {
    directories.value.push(dir)
    newDirectory.value = ''
  }
}

const removeDirectory = (index: number) => {
  directories.value.splice(index, 1)
}

const loadBranchAndTag = async () => {
  try {
    const data: BranchAndTagResponse = await testApi.getBranchAndTag()
    branchList.value = data.branchs || []
    tagList.value = data.tags || []
    latestCommit.value = data.latest_commit || ''
    
    if (data.current) {
      if (branchList.value.includes(data.current)) {
        currentBranch.value = data.current
        currentTag.value = ''
      } else if (tagList.value.includes(data.current)) {
        currentTag.value = data.current
        currentBranch.value = ''
      }
    }
  } catch (error) {
    ElMessage.error('加载分支标签列表失败')
  }
}

// 格式化 commit hash 显示
const formatCommitHash = (commit: string): string => {
  if (!commit) return ''
  if (commit.length > 12) {
    return commit.substring(0, 12) + '...'
  }
  return commit
}

// 格式化分支/标签显示
const formatBranchTag = (text: string): string => {
  if (!text) return ''
  if (text.length > 30) {
    return text.substring(0, 30) + '...'
  }
  return text
}

// 构建树形结构
const buildTestCasesTree = (cases: string[]) => {
  const root: any = {
    id: 'root',
    label: 'products',
    type: 'directory',
    children: [],
    testCaseCount: 0
  }
  
  cases.forEach(testCase => {
    const path = testCase.replace(/^products\//, '')
    const parts = path.split('::')
    
    let currentLevel = root
    const pathParts = parts[0].split('/')
    
    let currentPath = 'products'
    for (let i = 0; i < pathParts.length; i++) {
      const part = pathParts[i]
      const isLastPath = i === pathParts.length - 1
      const type = isLastPath ? 'file' : 'directory'
      currentPath += '/' + part
      
      let node = currentLevel.children?.find((child: any) => child.label === part)
      if (!node) {
        node = {
          id: currentPath,
          label: part,
          type,
          children: [],
          testCaseCount: 0
        }
        if (!currentLevel.children) {
          currentLevel.children = []
        }
        currentLevel.children.push(node)
      }
      
      currentLevel = node
    }
    
    if (parts.length > 1) {
      const classPart = parts[1]
      const classId = currentPath + '::' + classPart
      let classNode = currentLevel.children?.find((child: any) => child.label === classPart)
      
      if (!classNode) {
        classNode = {
          id: classId,
          label: classPart,
          type: 'class',
          children: [],
          testCaseCount: 0,
          fullPath: testCase
        }
        if (!currentLevel.children) {
          currentLevel.children = []
        }
        currentLevel.children.push(classNode)
      }
      
      if (parts.length > 2) {
        const methodPart = parts[2]
        const methodId = classId + '::' + methodPart
        const methodNode = {
          id: methodId,
          label: methodPart,
          type: 'testCase',
          fullPath: testCase,
          testCaseCount: 1
        }
        
        if (!classNode.children) {
          classNode.children = []
        }
        classNode.children.push(methodNode)
      }
    } else {
      const methodNode = {
        id: currentPath,
        label: pathParts[pathParts.length - 1],
        type: 'testCase',
        fullPath: testCase,
        testCaseCount: 1
      }
      
      if (!currentLevel.children) {
        currentLevel.children = []
      }
      currentLevel.children.push(methodNode)
    }
  })
  
  const calculateTestCaseCount = (node: any): number => {
    if (node.type === 'testCase') {
      return 1
    }
    
    let count = 0
    if (node.children && Array.isArray(node.children)) {
      node.children.forEach((child: any) => {
        count += calculateTestCaseCount(child)
      })
    }
    node.testCaseCount = count
    return count
  }
  
  calculateTestCaseCount(root)
  return [root]
}

const handleCollectTestCases = async () => {
  try {
    collectLoading.value = true
    showTestCasesTree.value = false
    
    const request = {
      dirs: directories.value
    }
    
    const response: CasesResponse = await testApi.collectTestCases(request)
    const cases = response.cases || []
    
    if (cases.length === 0) {
      ElMessage.warning('未扫描到任何测试用例')
      return
    }
    
    collectedCases.value = cases
    leftTestCasesTree.value = buildTestCasesTree(cases)
    showTestCasesTree.value = true
    
    ElMessage.success(`成功扫描 ${cases.length} 个测试用例`)
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '扫描测试用例失败')
  } finally {
    collectLoading.value = false
  }
}

// 左侧树勾选事件
const handleLeftTreeCheck = (checkedData: any, checkedNodes: any) => {
  // 获取所有选中的节点数据
  const allCheckedNodes = leftTreeRef.value?.getCheckedNodes(false, true) || []
  
  // 只筛选出测试用例节点（叶子节点，类型为 'class' 或 'testCase'）
  const testCaseNodes = allCheckedNodes.filter((node: any) => {
    const isLeafNode = !node.children || node.children.length === 0
    const isTestCaseType = node.type === 'testCase' || node.type === 'class'
    return isLeafNode && isTestCaseType
  })
  
  leftSelectedCases.value = testCaseNodes.map((node: any) => node.fullPath || node.id)
  
  // 新增：如果左侧有勾选，清空右侧勾选
  if (testCaseNodes.length > 0 && rightTreeRef.value) {
    rightTreeRef.value.setCheckedKeys([])
  }
}

// 右侧树勾选事件
const handleRightTreeCheck = (checkedData: any, checkedNodes: any) => {
  // 获取所有选中的节点数据
  const allCheckedNodes = rightTreeRef.value?.getCheckedNodes(false, true) || []
  
  // 只筛选出测试用例节点（叶子节点，类型为 'class' 或 'testCase'）
  const testCaseNodes = allCheckedNodes.filter((node: any) => {
    const isLeafNode = !node.children || node.children.length === 0
    const isTestCaseType = node.type === 'testCase' || node.type === 'class'
    return isLeafNode && isTestCaseType
  })
  
  // 新增：如果右侧有勾选，清空左侧勾选
  if (testCaseNodes.length > 0 && leftTreeRef.value) {
    leftTreeRef.value.setCheckedKeys([])
    leftSelectedCases.value = []
  }
}

// 监听右侧用例变化，重新构建右侧树
watch(rightTestCases, (newCases) => {
  if (newCases.length > 0) {
    rightTestCasesTree.value = buildTestCasesTree(newCases.map(item => item.fullPath))
  } else {
    rightTestCasesTree.value = []
  }
}, { deep: true })

// 添加到右侧
const moveToRight = () => {
  if (!leftTreeRef.value) return
  
  // 保存左侧树当前的展开状态
  const leftExpandedKeys = saveTreeExpandedKeys(leftTreeRef.value)
  
  // 获取所有选中的节点
  const allCheckedNodes = leftTreeRef.value.getCheckedNodes(false, true) || []
  
  // 过滤出测试用例节点
  const testCaseNodes = allCheckedNodes.filter((node: any) => {
    const isLeafNode = !node.children || node.children.length === 0
    const isTestCaseType = node.type === 'testCase' || node.type === 'class'
    return isLeafNode && isTestCaseType
  })
  
  // 进一步过滤掉已经在右侧的用例
  const casesToAdd = testCaseNodes
    .map((node: any) => node.fullPath || node.id)
    .filter(casePath => !rightTestCases.value.some(item => item.fullPath === casePath))
  
  if (casesToAdd.length === 0) {
    ElMessage.warning('没有可添加的新测试用例')
    return
  }
  
  casesToAdd.forEach(casePath => {
    rightTestCases.value.push({
      fullPath: casePath
    })
  })
  
  // 更新左侧树：过滤掉已添加到右侧的用例
  const remainingCases = collectedCases.value.filter(casePath => 
    !rightTestCases.value.some(item => item.fullPath === casePath)
  )
  leftTestCasesTree.value = buildTestCasesTree(remainingCases)
  
  // 清空左侧选择
  leftSelectedCases.value = []
  if (leftTreeRef.value) {
    leftTreeRef.value.setCheckedKeys([])
  }
  
  // 恢复左侧树的展开状态
  nextTick(() => {
    restoreTreeExpandedKeys(leftTreeRef.value, leftExpandedKeys)
  })
  
  ElMessage.success(`已添加 ${casesToAdd.length} 个测试用例`)
}

// 移回左侧
const moveToLeft = () => {
  if (!rightTreeRef.value) return
  
  // 保存右侧树当前的展开状态
  const rightExpandedKeys = saveTreeExpandedKeys(rightTreeRef.value)
  
  // 获取右侧选中的节点
  const allCheckedNodes = rightTreeRef.value.getCheckedNodes(false, true) || []
  
  // 过滤出测试用例节点
  const testCaseNodes = allCheckedNodes.filter((node: any) => {
    const isLeafNode = !node.children || node.children.length === 0
    const isTestCaseType = node.type === 'testCase' || node.type === 'class'
    return isLeafNode && isTestCaseType
  })
  
  const casesToRemove = testCaseNodes.map((node: any) => node.fullPath || node.id)
  
  if (casesToRemove.length === 0) {
    ElMessage.warning('请先选择要移除的测试用例')
    return
  }
  
  // 从右侧移除
  rightTestCases.value = rightTestCases.value.filter(item => 
    !casesToRemove.includes(item.fullPath)
  )
  
  // 更新左侧树：将移除的用例加回左侧
  const remainingCases = collectedCases.value.filter(casePath => 
    !rightTestCases.value.some(item => item.fullPath === casePath)
  )
  leftTestCasesTree.value = buildTestCasesTree(remainingCases)
  
  // 清空右侧选择
  if (rightTreeRef.value) {
    rightTreeRef.value.setCheckedKeys([])
  }
  
  // 恢复右侧树的展开状态
  nextTick(() => {
    restoreTreeExpandedKeys(rightTreeRef.value, rightExpandedKeys)
  })
  
  ElMessage.success(`已移除 ${casesToRemove.length} 个测试用例`)
}

// 从右侧单个移除
const removeFromRight = (data: any) => {
  if (data.type === 'testCase' || data.type === 'class') {
    // 保存右侧树当前的展开状态
    const rightExpandedKeys = saveTreeExpandedKeys(rightTreeRef.value)
    
    rightTestCases.value = rightTestCases.value.filter(item => 
      item.fullPath !== (data.fullPath || data.id)
    )
    
    // 更新左侧树：将移除的用例加回左侧
    const remainingCases = collectedCases.value.filter(casePath => 
      !rightTestCases.value.some(item => item.fullPath === casePath)
    )
    leftTestCasesTree.value = buildTestCasesTree(remainingCases)
    
    // 恢复右侧树的展开状态
    nextTick(() => {
      restoreTreeExpandedKeys(rightTreeRef.value, rightExpandedKeys)
    })
    
    ElMessage.success('已移除测试用例')
  }
}

// 保存和恢复树展开状态的方法
const saveTreeExpandedKeys = (treeRef: InstanceType<typeof ElTree> | null): string[] => {
  if (!treeRef) return []
  return treeRef.getCurrentKey() ? [treeRef.getCurrentKey() as string] : [] // 获取当前展开的节点
}

const restoreTreeExpandedKeys = (treeRef: InstanceType<typeof ElTree> | null, keys: string[]) => {
  if (!treeRef || keys.length === 0) return
  // 使用 nextTick 确保在树渲染完成后恢复展开状态
  nextTick(() => {
    keys.forEach(key => {
      const node = treeRef.getNode(key)
      if (node) {
        treeRef.setCurrentKey(key) // 设置当前节点
      }
    })
  })
}

const filteredLeftTestCasesTree = computed(() => {
  return filterTreeData(leftTestCasesTree.value, leftFilterText.value)
})

const filteredRightTestCasesTree = computed(() => {
  return filterTreeData(rightTestCasesTree.value, rightFilterText.value)
})

// 树节点过滤方法
const filterNode = (value: string, data: any) => {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

// 过滤树数据方法
const filterTreeData = (treeData: any[], filterText: string): any[] => {
  if (!filterText) return treeData
  
  const filter = (nodes: any[]): any[] => {
    return nodes
      .map(node => ({ ...node }))
      .filter(node => {
        // 如果节点本身匹配，保留整个节点
        if (node.label.toLowerCase().includes(filterText.toLowerCase())) {
          return true
        }
        
        // 如果子节点有匹配的，保留该节点并过滤子节点
        if (node.children && node.children.length > 0) {
          const filteredChildren = filter(node.children)
          if (filteredChildren.length > 0) {
            node.children = filteredChildren
            return true
          }
        }
        
        return false
      })
  }
  
  return filter(treeData)
}

// 加载执行历史
const loadExecuteHistory = async () => {
  try {
    historyLoading.value = true
    const response: ExecuteListResponse = await testApi.getExecuteHistory()
    const history = response.items || []
    executeHistory.value = history.sort((a, b) => {
      // 按时间倒序排列
      return new Date(b.time || 0).getTime() - new Date(a.time || 0).getTime()
    })
  } catch (error) {
    ElMessage.error('获取执行历史失败')
  } finally {
    historyLoading.value = false
  }
}

// 修改 handleRunSelected 方法，执行成功后刷新历史记录
const handleRunSelected = async () => {
  if (rightTestCases.value.length === 0) {
    ElMessage.warning('请先添加测试用例')
    return
  }
  
  const selectedCases = rightTestCases.value.map(item => item.fullPath)
  
  try {
    await ElMessageBox.confirm(
      `确定要运行 ${selectedCases.length} 个测试用例吗？`,
      '确认运行测试',
      {
        type: 'warning',
        confirmButtonText: '开始运行',
        cancelButtonText: '取消'
      }
    )
    
    // 显示运行中状态
    const loadingMessage = ElMessage.success('开始运行测试用例...')
    
    // 调用后端执行接口
    const request: CasesResponse = {
      cases: selectedCases
    }
    
    const response: ExecuteResponse = await testApi.executeTestCasesWithResponse(request)
    
    // 关闭加载消息
    loadingMessage.close()
    
    // 显示执行结果
    if (response.url) {
      ElMessage.success({
        message: `测试执行成功！执行时间: ${response.time || '未知'}`,
        duration: 5000,
        showClose: true
      })
      
      // 执行成功后刷新历史记录
      await loadExecuteHistory()
    } else {
      ElMessage.success('测试用例执行请求已发送')
    }
    
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '执行测试用例失败')
    }
  }
}

onMounted(() => {
  loadBranchAndTag()
  loadExecuteHistory()
})
</script>

<style scoped>
/* 页面布局样式 */
.qa-platform {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 顶部区域样式 */
.top-section {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
}

.version-section {
  flex: 1;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.history-section {
  flex: 1;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
}

.history-content {
  flex: 1;
  min-height: 300px;
  display: flex;
  flex-direction: column;
}

.refresh-btn {
  margin-left: auto;
}

/* 区域标题样式 */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
}

.section-title .el-icon {
  color: #409eff;
}

/* 当前版本样式 */
.current-version {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.current-tag {
  font-weight: 600;
  padding: 8px 12px;
}

.current-tag .el-icon {
  margin-right: 4px;
}

.commit-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.commit-tag {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.commit-hash {
  font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #67c23a;
  margin-left: 4px;
}

/* 版本控制样式 */
.version-control {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mode-selector {
  margin-bottom: 8px;
}

.version-selection {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.selection-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.selection-info {
  min-height: 32px;
  display: flex;
  align-items: center;
}

.checkout-btn {
  margin-left: auto;
}

/* 下拉选项样式 */
.branch-option,
.tag-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.current-indicator {
  margin-left: 8px;
}

/* 测试用例收集区域 */
.collect-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.directory-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dir-input-group {
  display: flex;
  gap: 12px;
  align-items: center;
}

.dir-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dir-list-title {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
}

.dir-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dir-tag {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.collect-btn {
  align-self: flex-start;
}

/* 测试用例选择区域样式 */
.test-cases-selection {
  margin-top: 20px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  overflow: hidden;
}

.selection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.selection-header h3 {
  margin: 0;
  font-size: 16px;
  color: #1f2937;
}

.selection-container {
  display: flex;
  height: 500px;
  background: white;
  min-height: 0;
}

/* 左右面板样式 */
.left-panel,
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  border: 1px solid #e2e8f0;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.panel-header h4 {
  margin: 0;
  font-size: 14px;
  color: #1f2937;
}

.count-info {
  font-size: 12px;
  color: #64748b;
}

.filter-input {
  flex-shrink: 0;
}

/* 树容器包装器 */
.tree-container-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 0;
  overflow: hidden;
}

.tree-container {
  flex: 1;
  overflow: auto;
  padding: 8px;
  min-width: 0;
  min-height: 0;
  scrollbar-width: thin;
  -ms-overflow-style: auto;
}

/* 自定义滚动条样式 - 确保可见 */
.tree-container::-webkit-scrollbar {
  height: 12px;
  width: 12px;
}

.tree-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 6px;
  border: 1px solid #e1e1e1;
}

.tree-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 6px;
  border: 2px solid #f1f1f1;
}

.tree-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.tree-container::-webkit-scrollbar-corner {
  background: #f1f1f1;
}

/* 传输按钮样式 */
.transfer-buttons {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: 0 20px;
  gap: 16px;
  flex-shrink: 0;
}

.transfer-btn {
  width: 90px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
}

/* 树节点样式 */
:deep(.el-tree) {
  min-width: max-content;
  width: 100%;
  min-height: 0;
}

:deep(.el-tree > .el-tree-node) {
  min-width: max-content;
}

:deep(.el-tree-node) {
  min-width: max-content;
}

:deep(.el-tree-node__content) {
  cursor: pointer;
  height: 34px;
  min-width: max-content;
  width: auto;
}

:deep(.el-tree-node__content:hover) {
  background-color: #f5f7fa;
}

.tree-node {
  width: 100%;
  min-width: 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  min-width: max-content;
  width: 100%;
}

.node-icon {
  color: #64748b;
  font-size: 16px;
  flex-shrink: 0;
}

.node-label {
  font-size: 14px;
  color: #1f2937;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.count-tag {
  margin-left: auto;
  flex-shrink: 0;
}

.remove-btn {
  padding: 4px;
  margin-left: 8px;
  opacity: 0.7;
  flex-shrink: 0;
}

.remove-btn:hover {
  opacity: 1;
}

.run-btn {
  font-weight: 600;
}

/* 历史记录表格样式 */
.no-data {
  color: #c0c4cc;
  font-style: italic;
}

:deep(.el-table) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.el-table__body-wrapper) {
  flex: 1;
  overflow: auto;
}

:deep(.el-table .cell) {
  display: flex;
  align-items: center;
}

:deep(.el-link) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* 对话框样式 */
.checkout-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 20px 0;
    margin-right: 0;
  }

  :deep(.el-dialog__body) {
    padding: 16px 20px;
  }

  :deep(.el-dialog__footer) {
    padding: 0 20px 20px;
  }
}

.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.confirm-message {
  padding: 12px 0;
}

.confirm-message p {
  margin: 0 0 8px 0;
  font-weight: 500;
  color: #374151;
}

.operation-list {
  margin: 0;
  padding-left: 20px;
  color: #6b7280;
}

.operation-list li {
  margin-bottom: 4px;
  line-height: 1.5;
}

.operation-list strong {
  color: #409eff;
}

.current-warning {
  margin-top: 12px;
}

.dialog-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.cancel-btn {
  width: 100px;
}

.confirm-btn {
  width: 120px;
  font-weight: 600;
}

/* 移除滑动指示器相关样式 */
.scroll-indicator {
  display: none;
}

.scroll-track {
  display: none;
}

.scroll-thumb {
  display: none;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .top-section {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .current-version {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .card-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .version-selection {
    flex-direction: column;
    align-items: flex-start;
  }

  .checkout-btn {
    margin-left: 0;
    align-self: flex-start;
  }

  .selection-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .dir-input-group {
    flex-direction: column;
    align-items: flex-start;
  }

  .selection-container {
    height: 400px;
    flex-direction: column;
  }

  .transfer-buttons {
    flex-direction: row;
    padding: 12px 20px;
    order: 3;
  }

  .transfer-btn {
    width: 100px;
  }

  .left-panel,
  .right-panel {
    min-height: 200px;
  }
  
  .tree-container {
    overflow: auto !important;
  }
}

/* 确保表格滚动条正常工作 */
:deep(.el-table__body-wrapper) {
  scrollbar-width: thin;
  -ms-overflow-style: auto;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar) {
  height: 8px;
  width: 8px;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-track) {
  background: #f1f1f1;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-thumb) {
  background: #c1c1c1;
  border-radius: 4px;
}

:deep(.el-table__body-wrapper::-webkit-scrollbar-thumb:hover) {
  background: #a8a8a8;
}
</style>