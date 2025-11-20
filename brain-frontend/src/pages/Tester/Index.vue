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
            <span>测试代码版本选择</span>
          </div>
          
          <!-- 当前版本信息 -->
          <div class="current-version">
            <div v-if="!branchList.length && !tagList.length" class="loading-version">
              <el-tag type="info" class="current-tag">
                <el-icon><Loading /></el-icon>
                正在查询本地代码版本...
              </el-tag>
            </div>
            <div v-else class="version-info">
              <div class="version-item" v-if="currentBranch">
                <el-tag type="info" class="current-tag">
                  <el-icon><Position /></el-icon>
                  本地当前分支: 
                  <span class="commit-hash">{{ currentBranch }}</span>
                </el-tag>
              </div>
              <div class="version-item" v-if="currentTag">
                <el-tag type="info" class="current-tag">
                  <el-icon><Position /></el-icon>
                  本地当前标签: 
                  <span class="commit-hash">{{ currentTag }}</span>
                </el-tag>
              </div>
              <div class="version-item" v-if="latestCommit">
                <el-tooltip :content="latestCommit" placement="top">
                  <el-tag type="info" class="current-tag">
                    <el-icon><Position /></el-icon>
                    本地最新commit id: 
                    <span class="commit-hash">{{ formatCommitHash(latestCommit) }}</span>
                  </el-tag>
                </el-tooltip>
              </div>
            </div>
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
              </div>

              <el-button 
                type="primary" 
                @click="handleCheckout" 
                :loading="checkoutLoading"
                :disabled="!canCheckout"
              >
                <el-icon><Switch /></el-icon>
                拉取最新代码
              </el-button>
            </div>
            <div class="selection-info" v-if="selectedBranch">
              <el-tag type="success">
                <el-icon><Check /></el-icon>
                已选择分支: {{ selectedBranch }}
              </el-tag>
            </div>
            <div class="selection-info" v-if="selectedTag">
              <el-tag type="warning">
                <el-icon><Check /></el-icon>
                已选择标签: {{ selectedTag }}
              </el-tag>
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
              :max-height="400"
            >
              <el-table-column prop="time" label="执行时间" width="170" sortable />
              <el-table-column prop="current" label="执行分支/标签" width="200">
                <template #default="{ row }">
                  <el-tooltip v-if="row.current && row.current.length > 20" :content="row.current" placement="top">
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
              <el-table-column prop="latest_commit" label="执行时Commit" width="140">
                <template #default="{ row }">
                  <el-tooltip v-if="row.latest_commit" :content="row.latest_commit" placement="top">
                    <el-tag size="small" type="success" class="commit-tag">
                      {{ formatCommitHash(row.latest_commit) }}
                    </el-tag>
                  </el-tooltip>
                  <span v-else class="no-data">-</span>
                </template>
              </el-table-column>
              <!-- 新增拓扑列 -->
              <el-table-column prop="topo" label="拓扑信息" width="105">
                <template #default="{ row }">
                  <el-link 
                    v-if="row.topo" 
                    :href="generateFileUrl(row.topo)" 
                    target="_blank" 
                    type="primary"
                    :underline="false"
                    class="topo-link"
                  >
                    <el-icon><View /></el-icon>
                    查看拓扑
                  </el-link>
                  <span v-else class="no-data">-</span>
                </template>
              </el-table-column>
              <!-- 新增日志列 -->
              <el-table-column prop="log" label="执行日志" width="100">
                <template #default="{ row }">
                  <el-link 
                    v-if="row.log" 
                    :href="row.log" 
                    target="_blank" 
                    type="success"
                    :underline="false"
                    class="log-link"
                  >
                    <el-icon><Document /></el-icon>
                    查看日志
                  </el-link>
                  <span v-else class="no-data">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="url" label="测试报告" width="100">
                <template #default="{ row }">
                  <el-link 
                    v-if="row.url" 
                    :href="row.url" 
                    target="_blank" 
                    type="primary"
                    :underline="false"
                    class="report-link"
                  >
                    <el-icon><Link /></el-icon>
                    查看报告
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
          <span>测试用例管理</span>
        </div>

        <!-- 左右布局 -->
        <div class="management-layout">
          <!-- 左侧：目录配置 -->
          <div class="left-management">
            <div class="directory-config">
              <div class="dir-controls">
                <el-button 
                  @click="showDirectoryPicker = true" 
                  type="primary" 
                  class="select-dir-btn"
                >
                  <el-icon><FolderOpened /></el-icon>
                  选择目录并扫描用例
                </el-button>
              </div>

              <div class="dir-list">
                <div class="dir-list-title">已扫描目录:</div>
                <div class="dir-tags" v-if="directories.length > 0">
                  <el-tag
                    v-for="(dir, index) in directories"
                    :key="index"
                    type="info"
                    class="dir-tag"
                  >
                    {{ dir }}
                  </el-tag>
                </div>
                <div class="no-directories" v-else>
                  <span class="no-dirs-text">未进行用例扫描</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：用例集合管理 -->
          <div class="right-management">
            <div class="combinations-section">
              <div class="section-title">
                <el-icon><FolderOpened /></el-icon>
                <span>测试用例集合管理</span>
              </div>
              
              <div class="combinations-control">
                <div class="combination-selection">
                  <el-select 
                    v-model="selectedCombinationId" 
                    placeholder="选择保存的自定义用例集合" 
                    style="width: 100%"
                    @change="handleCombinationChange"
                    clearable
                    filterable
                  >
                    <el-option 
                      v-for="combination in combinations" 
                      :key="combination.id" 
                      :label="combination.name" 
                      :value="combination.id"
                    >
                      <div class="combination-option">
                        <span>{{ combination.name }}</span>
                        <el-tag size="small" type="info" class="case-count">
                          {{ combination.cases?.length || 0 }} 用例
                        </el-tag>
                        <span class="create-time">{{ combination.created_at }}</span>
                      </div>
                    </el-option>
                  </el-select>
                  
                  <div class="combination-buttons">
                    <el-button 
                      type="success" 
                      @click="loadCombinationToRight"
                      :disabled="!selectedCombinationId"
                      style="width: 100%"
                    >
                      <el-icon><Lightning /></el-icon>
                      加载集合
                    </el-button>
                    <el-button 
                      type="danger" 
                      @click="deleteCombination"
                      :disabled="!selectedCombinationId"
                      style="width: 100%"
                    >
                      <el-icon><Delete /></el-icon>
                      删除集合
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 测试用例选择区域 -->
        <div class="test-cases-selection">
          <div class="selection-header">
            <h3>测试用例列表</h3>
            <div class="action-buttons">
              <el-button 
                type="primary" 
                @click="saveCurrentCombination" 
                :disabled="rightTestCases.length === 0"
              >
                <el-icon><FolderAdd /></el-icon>
                保存为新集合
              </el-button>
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
                          <el-icon v-else-if="data.type === 'testCase'" class="node-icon">
                            <Position />
                          </el-icon>
                          <el-icon v-else class="node-icon">
                            <QuestionFilled />
                          </el-icon>
                          
                          <span class="node-label">{{ data.label }}</span>
                          
                          <!-- 在所有非测试用例节点后面显示用例数量 -->
                          <span 
                            v-if="data.type !== 'testCase'" 
                            class="count-badge"
                          >
                            ({{ data.testCaseCount || 0 }})
                          </span>
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
                          
                          <span 
                            v-if="data.type !== 'testCase'" 
                            class="count-badge"
                          >
                            ({{ data.testCaseCount || 0 }})
                          </span>
                          
                          <!-- 移除按钮 -->
                          <el-button
                            v-if="data.type === 'testCase'"
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
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 目录选择器对话框 -->
    <el-dialog
      v-model="showDirectoryPicker"
      title="选择目录并扫描用例"
      width="600px"
      class="directory-picker-dialog"
    >
      <div class="directory-picker">
        <div class="picker-header">
          <el-input
            v-model="directorySearch"
            placeholder="搜索目录..."
            clearable
            style="width: 300px"
            :prefix-icon="Search"
          />
          <el-button @click="refreshDirectoryTree" :loading="directoryLoading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
        
        <div class="directory-tree">
          <el-tree
            ref="directoryTreeRef"
            :data="directoryTree"
            :props="directoryProps"
            node-key="path"
            :default-expand-all="false"
            :expand-on-click-node="false"
            :filter-node-method="filterDirectoryNode"
            @node-click="handleDirectoryClick"
            @check-change="handleDirectoryCheckChange"
            show-checkbox
            :check-strictly="true"
            v-loading="directoryLoading"
            highlight-current
            style="margin-top: 16px;"
          >
            <template #default="{ node, data }">
              <div class="directory-node" :class="{ 'disabled-node': data.disabled }">
                <el-icon class="directory-icon">
                  <Folder v-if="data.type === 'directory'" />
                  <Document v-else />
                </el-icon>
                <span class="directory-name">{{ node.label }}</span>
                <el-tag v-if="data.disabled" size="small" type="info" class="disabled-tag">
                  已包含在父目录中
                </el-tag>
              </div>
            </template>
          </el-tree>
        </div>
        
        <div class="current-selection" v-if="selectedDirectories.length > 0">
          <el-alert
            :title="`已选择 ${selectedDirectories.length} 个目录`"
            type="info"
            :closable="false"
            show-icon
          />
          <div class="selected-dirs-list">
            <el-tag
              v-for="(dir, index) in selectedDirectories"
              :key="index"
              closable
              @close="removeSelectedDirectory(dir)"
              type="success"
              class="selected-dir-tag"
            >
              {{ dir }}
            </el-tag>
          </div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="cancelDirectorySelection">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmDirectorySelection"
          :disabled="selectedDirectories.length === 0"
          :loading="collectLoading"
        >
          <template #loading>
            <el-icon class="is-loading"><Loading /></el-icon>
          </template>
          确认并扫描 ({{ selectedDirectories.length }})
        </el-button>
      </template>
    </el-dialog>

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

    <!-- 保存集合对话框 -->
    <el-dialog
      v-model="saveCombinationDialogVisible"
      title="保存测试用例集合"
      width="500px"
    >
      <el-form :model="saveCombinationForm" label-width="80px">
        <el-form-item label="集合名称" required>
          <el-input 
            v-model="saveCombinationForm.name" 
            placeholder="请输入集合名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="用例数量">
          <span>{{ rightTestCases.length }} 个测试用例</span>
        </el-form-item>
        <el-form-item label="用例列表">
          <div class="case-preview">
            <el-tag
              v-for="(testCase, index) in rightTestCases.slice(0, 10)"
              :key="index"
              size="small"
              class="preview-tag"
            >
              {{ getTestCaseName(testCase.fullPath) }}
            </el-tag>
            <div v-if="rightTestCases.length > 10" class="more-cases">
              还有 {{ rightTestCases.length - 10 }} 个用例...
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveCombinationDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="confirmSaveCombination"
          :disabled="!saveCombinationForm.name.trim()"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 服务器选择对话框 -->
    <el-dialog
      v-model="serverDialogVisible"
      title="选择执行服务器和网口"
      width="900px"
      class="server-dialog"
      :close-on-click-modal="false"
    >
      <div class="server-dialog-content">
        <!-- 服务器和网口选择整合在一起 -->
        <div class="server-nic-selection">
          <div class="section-title">
            <el-icon><Monitor /></el-icon>
            <span>选择服务器和网口</span>
          </div>
          
          <!-- 服务器数量统计 -->
          <div class="selection-stats" v-if="sortedAvailableServers.length > 0">
            <el-tag type="info">
              共 {{ sortedAvailableServers.length }} 台服务器
            </el-tag>
            <el-tag type="success">
              已选择 {{ selectedServers.length }} 台
            </el-tag>
          </div>
          
          <div class="server-list-with-nics">
            <div 
              v-for="server in sortedAvailableServers" 
              :key="server.id"
              class="server-item-with-nics"
            >
              <div class="server-checkbox">
                <el-checkbox 
                  v-model="selectedServers" 
                  :label="server.id"
                  @change="handleServerSelectionChange(server)"
                >
                  <div class="server-info">
                    <span class="server-name">{{ server.bmc.hostname }}</span>
                    <span class="server-ip">{{ server.device.ip }}</span>
                    <!-- 总网卡数 -->
                    <el-tag size="small" type="info">
                      共 {{ getTotalNicCount(server) }} 网卡
                    </el-tag>
                    <!-- 根据实际网卡类型显示 -->
                    <el-tag 
                      v-for="(count, type) in getNicTypeCounts(server)" 
                      :key="type"
                      size="small" 
                    >
                      {{ count }} {{ type }}
                    </el-tag>
                  </div>
                </el-checkbox>
              </div>
              
              <!-- 网口选择区域 - 紧跟在服务器后面 -->
              <div 
                class="nic-selection-area" 
                v-if="selectedServers.includes(server.id) && getTestableNicCount(server) > 0"
              >
                <div class="nic-selection-header">
                  <el-icon><Connection /></el-icon>
                  <span>网口选择 - 已选择 {{ getSelectedInterfaceCount(server) }} 个网口</span>
                </div>
                
                <div class="nics-list">
                  <!-- 显示可测试的非MV200网卡 -->
                  <div 
                    v-for="nic in getTestableNics(server)" 
                    :key="nic?.sn || nic?.type"
                    class="nic-item"
                  >
                    <div class="nic-header">
                      <div class="nic-info">
                        <span class="nic-type">{{ nic.type || '未知类型' }}</span>
                        <span class="nic-sn">SN: {{ nic.sn || '未知SN' }}</span>
                        <el-tag v-if="nic.nic_info" size="small" type="primary">
                          {{ nic.nic_info.length }} 个网口
                        </el-tag>
                        <el-tag 
                          v-if="getSelectedInterfaceCountForNic(nic) > 0" 
                          size="small" 
                          type="success"
                        >
                          已选 {{ getSelectedInterfaceCountForNic(nic) }} 个
                        </el-tag>
                      </div>
                      <div class="nic-select-all">
                        <el-checkbox
                          :indeterminate="isNicPartiallySelected(nic)"
                          v-model="nic.allInterfacesSelected"
                          @change="handleNicAllInterfacesChange(nic)"
                        >
                          全选此网卡
                        </el-checkbox>
                      </div>
                    </div>
                    
                    <!-- 网口选择区域 -->
                    <div class="nic-interfaces-selection" v-if="nic.nic_info && nic.nic_info.length > 0">
                      <div class="interfaces-list">
                        <div 
                          v-for="(nicInfo, index) in nic.nic_info" 
                          :key="index"
                          class="nic-interface"
                        >
                          <el-checkbox
                            v-model="nicInfo.selected"
                            @change="handleInterfaceSelectionChange(nic)"
                          >
                            <div class="interface-info">
                              <span class="iface-name">{{ nicInfo.iface || `网口${index + 1}` }}</span>
                              <span class="bdf">{{ nicInfo.bdf || '未知BDF' }}</span>
                            </div>
                          </el-checkbox>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 没有可测试网卡的情况 -->
              <div 
                class="no-testable-nics" 
                v-if="selectedServers.includes(server.id) && getTestableNicCount(server) === 0"
              >
                <el-alert
                  :title="`服务器 ${server.bmc.hostname} 没有可测试的网卡（所有网卡均为MV200类型或无可测试网口）`"
                  type="info"
                  :closable="false"
                  show-icon
                />
              </div>
            </div>
            
            <div v-if="sortedAvailableServers.length === 0" class="no-servers">
              <el-empty description="暂无可用服务器，请先占用服务器" />
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <div class="footer-stats">
            <el-tag type="primary">
              已选择 {{ selectedServers.length }} 台服务器
            </el-tag>
            <el-tag type="success">
              已选择 {{ getTotalSelectedInterfaces() }} 个网口
            </el-tag>
          </div>
          <div class="footer-buttons">
            <el-button 
              @click="serverDialogVisible = false" 
              size="large"
              class="cancel-btn"
            >
              取消
            </el-button>
            <el-button 
              type="primary" 
              @click="handleExecuteConfirm" 
              :loading="executeLoading"
              :disabled="!canExecute"
              size="large"
              class="confirm-btn"
            >
              <template #loading>
                <el-icon class="is-loading"><Loading /></el-icon>
              </template>
              开始执行 ({{ getTotalSelectedInterfaces() }})
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 拓扑详情对话框 -->
    <el-dialog
      v-model="topoDialogVisible"
      title="拓扑信息"
      width="800px"
      class="topo-dialog"
    >
      <div class="topo-content">
        <el-alert
          title="拓扑信息 (YAML格式)"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        />
        <div class="yaml-container">
          <pre class="yaml-content">{{ formattedTopo }}</pre>
        </div>
      </div>
      <template #footer>
        <el-button @click="topoDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyTopoToClipboard">
          复制YAML
        </el-button>
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
  Refresh,
  Monitor,
  Connection,
  FolderOpened,
  FolderAdd,
  Lightning,
  View
} from '@element-plus/icons-vue'
import { testApi } from '@/api/tester'
import { deviceApi } from '@/api/device'
import { useAuthStore } from '@/stores/auth'
import type { 
  BranchAndTagResponse, 
  CheckoutRequest, 
  CasesResponse, 
  ExecuteResponse, 
  ServerDetailResponse,
  ExecuteRequest,
  Server,
  CaseNicInfo,
  CaseCombinationResponse,
  CaseCombinationRequest 
} from '@/types/api'

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
const selectedDirectories = ref<string[]>([])
const leftFilterText = ref('')
const rightFilterText = ref('')
const directories = ref<string[]>([])
const topoDialogVisible = ref(false)
const currentTopo = ref<any>({})

// 测试用例相关数据
const collectedCases = ref<string[]>([]) // 所有收集到的用例
const leftTestCasesTree = ref<any[]>([]) // 左侧树形数据
const rightTestCases = ref<any[]>([]) // 右侧已添加用例
const leftSelectedCases = ref<string[]>([]) // 左侧选中的用例
const rightTestCasesTree = ref<any[]>([]) // 右侧树形数据

// 用例集合相关数据
const combinations = ref<CaseCombinationResponse[]>([])
const selectedCombinationId = ref('')
const saveCombinationDialogVisible = ref(false)
const saveCombinationForm = ref<CaseCombinationRequest>({
  name: '',
  cases: []
})

// 服务器相关数据
const availableServers = ref<ServerDetailResponse[]>([])
const selectedServers = ref<string[]>([])
const serverDialogVisible = ref(false)
const executeLoading = ref(false)

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

// 新增响应式数据
const showDirectoryPicker = ref(false)
const directoryTree = ref<any[]>([])
const directoryLoading = ref(false)
const directorySearch = ref('')
const selectedDirectory = ref('')
const directoryTreeRef = ref<InstanceType<typeof ElTree>>()


const authStore = useAuthStore()

const generateFileUrl = (filePath: string): string => {
  const token = authStore.accessToken
  
  if (!token) {
    ElMessage.warning('请先登录以访问文件')
    return filePath
  }
  
  // 如果路径已经是完整URL，直接返回
  if (filePath.startsWith('http://') || filePath.startsWith('https://')) {
    const separator = filePath.includes('?') ? '&' : '?'
    return `${filePath}${separator}token=${encodeURIComponent(token)}`
  }
  
  // 确保路径以 / 开头
  const normalizedPath = filePath.startsWith('/') ? filePath : `/${filePath}`
  
  // 使用固定的后端文件服务地址（8088端口）
  const baseUrl = `${window.location.protocol}//${window.location.hostname}:8088`
  const fullUrl = `${baseUrl}${normalizedPath}`
  
  const separator = fullUrl.includes('?') ? '&' : '?'
  const result = `${fullUrl}${separator}token=${encodeURIComponent(token)}`
  return result
}

// 格式化拓扑信息为YAML
const formattedTopo = computed(() => {
  if (!currentTopo.value || Object.keys(currentTopo.value).length === 0) {
    return '# 无拓扑信息'
  }
  
  try {
    return convertToYaml(currentTopo.value)
  } catch (error) {
    console.error('格式化拓扑信息失败:', error)
    return '# 拓扑信息格式错误\n' + JSON.stringify(currentTopo.value, null, 2)
  }
})

// 显示拓扑详情
const showTopoDetail = (topo: any) => {
  currentTopo.value = topo
  topoDialogVisible.value = true
}

// 将对象转换为YAML格式
const convertToYaml = (obj: any, indent = 0): string => {
  const indentStr = '  '.repeat(indent)
  let yaml = ''
  
  if (typeof obj !== 'object' || obj === null) {
    return `${indentStr}${obj}`
  }
  
  if (Array.isArray(obj)) {
    if (obj.length === 0) {
      return `${indentStr}[]`
    }
    obj.forEach(item => {
      if (typeof item === 'object' && item !== null) {
        yaml += `${indentStr}-\n${convertToYaml(item, indent + 1)}\n`
      } else {
        yaml += `${indentStr}- ${item}\n`
      }
    })
    return yaml
  }
  
  Object.keys(obj).forEach(key => {
    const value = obj[key]
    if (typeof value === 'object' && value !== null) {
      if (Array.isArray(value)) {
        yaml += `${indentStr}${key}:\n${convertToYaml(value, indent + 1)}`
      } else {
        yaml += `${indentStr}${key}:\n${convertToYaml(value, indent + 1)}`
      }
    } else {
      yaml += `${indentStr}${key}: ${value}\n`
    }
  })
  
  return yaml
}

// 复制YAML到剪贴板
const copyTopoToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(formattedTopo.value)
    ElMessage.success('拓扑信息已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

// 目录树配置
const directoryProps = {
  children: 'children',
  label: 'name',
  disabled: 'disabled'
}

// 监听搜索条件变化
watch(directorySearch, (val) => {
  if (directoryTreeRef.value) {
    directoryTreeRef.value.filter(val)
  }
})

// 过滤目录节点
const filterDirectoryNode = (value: string, data: any) => {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

// 刷新目录树
const refreshDirectoryTree = async () => {
  try {
    directoryLoading.value = true
    // 这里调用后端API获取目录结构
    const response = await testApi.getDirectoryTree()
    directoryTree.value = response.tree
    
    // 初始化禁用状态
    const initializeDisabledState = (nodes: any[]) => {
      nodes.forEach(node => {
        node.disabled = false
        if (node.children) {
          initializeDisabledState(node.children)
        }
      })
    }
    initializeDisabledState(directoryTree.value)
    
  } catch (error) {
    ElMessage.error('加载目录结构失败')
  } finally {
    directoryLoading.value = false
  }
}

// 处理目录点击
const handleDirectoryClick = (data: any) => {
  if (data.type === 'directory' && directoryTreeRef.value && !data.disabled) {
    const node = directoryTreeRef.value.getNode(data.path)
    if (node) {
      const isChecked = directoryTreeRef.value.getCheckedNodes().includes(data)
      directoryTreeRef.value.setChecked(node, !isChecked, false)
    }
  }
}

// 处理目录勾选变化
const handleDirectoryCheckChange = (data: any, checked: boolean) => {
  if (data.type === 'directory') {
    if (checked) {
      handleParentDirectorySelect(data)
    } else {
      handleParentDirectoryDeselect(data)
    }
    
    // 更新目录树状态
    updateDirectoryTreeState()
  }
}

// 处理父目录选择
const handleParentDirectorySelect = (selectedDirectory: any) => {
  // 1. 获取所有子目录路径
  const childPaths = getAllChildPaths(selectedDirectory)
  
  // 2. 移除所有子目录（避免重复扫描）
  removeChildDirectories(childPaths)
  
  // 3. 添加父目录到选中列表
  if (!selectedDirectories.value.includes(selectedDirectory.path)) {
    selectedDirectories.value.push(selectedDirectory.path)
  }
  
  if (childPaths.length > 0) {
    ElMessage.info(`已选择父目录 ${selectedDirectory.path}，自动移除了 ${childPaths.length} 个子目录`)
  }
}

// 处理父目录取消选择
const handleParentDirectoryDeselect = (deselectedDirectory: any) => {
  // 从选中列表中移除
  const index = selectedDirectories.value.indexOf(deselectedDirectory.path)
  if (index > -1) {
    selectedDirectories.value.splice(index, 1)
  }
}

// 获取目录的所有子目录路径
const getAllChildPaths = (node: any): string[] => {
  const paths: string[] = []
  
  const collectPaths = (currentNode: any) => {
    if (currentNode.children && currentNode.children.length > 0) {
      currentNode.children.forEach((child: any) => {
        if (child.type === 'directory') {
          paths.push(child.path)
          collectPaths(child)
        }
      })
    }
  }
  
  collectPaths(node)
  return paths
}

// 移除子目录
const removeChildDirectories = (childPaths: string[]) => {
  let removedCount = 0
  
  childPaths.forEach(childPath => {
    const index = selectedDirectories.value.indexOf(childPath)
    if (index > -1) {
      selectedDirectories.value.splice(index, 1)
      removedCount++
      
      // 同时更新目录树的勾选状态
      if (directoryTreeRef.value) {
        const node = directoryTreeRef.value.getNode(childPath)
        if (node) {
          directoryTreeRef.value.setChecked(node, false, false)
        }
      }
    }
  })
  
  return removedCount
}

// 更新目录树状态
const updateDirectoryTreeState = () => {
  // 首先重置所有目录的禁用状态
  const resetDisabledState = (nodes: any[]) => {
    nodes.forEach(node => {
      if (node.type === 'directory') {
        node.disabled = false
        if (node.children) {
          resetDisabledState(node.children)
        }
      }
    })
  }
  
  resetDisabledState(directoryTree.value)
  
  // 为每个选中的父目录禁用其子目录
  selectedDirectories.value.forEach(selectedPath => {
    const findAndDisableChildren = (nodes: any[]) => {
      nodes.forEach(node => {
        if (node.path === selectedPath) {
          // 禁用所有子目录
          disableChildren(node)
        } else if (node.children) {
          findAndDisableChildren(node.children)
        }
      })
    }
    findAndDisableChildren(directoryTree.value)
  })
}

// 禁用所有子目录
const disableChildren = (node: any) => {
  if (node.children && node.children.length > 0) {
    node.children.forEach((child: any) => {
      if (child.type === 'directory') {
        child.disabled = true
        // 递归禁用孙子目录
        disableChildren(child)
      }
    })
  }
}

// 移除已选目录
const removeSelectedDirectory = (dir: string) => {
  const index = selectedDirectories.value.indexOf(dir)
  if (index > -1) {
    selectedDirectories.value.splice(index, 1)
  }
  
  // 同时更新目录树的勾选状态
  if (directoryTreeRef.value) {
    const node = directoryTreeRef.value.getNode(dir)
    if (node) {
      directoryTreeRef.value.setChecked(node, false)
    }
  }
  
  // 同时从已扫描目录中移除
  const dirIndex = directories.value.indexOf(dir)
  if (dirIndex > -1) {
    directories.value.splice(dirIndex, 1)
  }
  
  // 更新目录树状态
  updateDirectoryTreeState()
}

// 确认目录选择并直接扫描测试用例
const confirmDirectorySelection = async () => {
  if (selectedDirectories.value.length > 0) {
    try {
      collectLoading.value = true
      
      // 清空之前的目录，避免重复
      directories.value = []
      
      // 添加新目录
      selectedDirectories.value.forEach(dir => {
        if (!directories.value.includes(dir)) {
          directories.value.push(dir)
        }
      })
      
      // 直接开始扫描测试用例
      await handleCollectTestCases()
      
      // 关闭对话框
      showDirectoryPicker.value = false
      
    } catch (error) {
      ElMessage.error('扫描测试用例失败')
    } finally {
      collectLoading.value = false
    }
  }
}

// 取消目录选择
const cancelDirectorySelection = () => {
  // 不清空 selectedDirectories，这样下次打开时还能恢复
  showDirectoryPicker.value = false
}

// 监听对话框打开，重置状态
watch(showDirectoryPicker, (val) => {
  if (val) {
    refreshDirectoryTree()
    // 在下一次DOM更新后恢复之前勾选的目录
    nextTick(() => {
      restoreCheckedDirectories()
    })
  } else {
    // 对话框关闭时清空临时选择
    selectedDirectories.value = []
  }
})

const restoreCheckedDirectories = () => {
  if (directoryTreeRef.value && directories.value.length > 0) {
    // 设置勾选状态
    directoryTreeRef.value.setCheckedKeys(directories.value)
    
    // 更新选中的目录列表
    selectedDirectories.value = [...directories.value]
    
    // 更新目录树状态
    updateDirectoryTreeState()
  }
}

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
  if (collectedCases.value.length === 0) {
    return collectedCases.value.length
  }
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

// 服务器相关计算属性
const selectedServersWithNics = computed(() => {
  return availableServers.value.filter(server => 
    selectedServers.value.includes(server.id!)
  )
})

// 当前选择的集合
const currentCombination = computed(() => {
  return combinations.value.find(c => c.id === selectedCombinationId.value)
})

// 计算属性：按IP地址从小到大排序的服务器列表
const sortedAvailableServers = computed(() => {
  return [...availableServers.value].sort((a, b) => {
    const ipA = a.device.ip.split('.').map(Number)
    const ipB = b.device.ip.split('.').map(Number)
    
    // 逐段比较IP地址
    for (let i = 0; i < 4; i++) {
      if (ipA[i] !== ipB[i]) {
        return ipA[i] - ipB[i]
      }
    }
    return 0
  })
})

// 处理服务器选择变化
const handleServerSelectionChange = (server: ServerDetailResponse) => {
  // 当取消选择服务器时，取消选择该服务器的所有网口
  if (!selectedServers.value.includes(server.id!)) {
    if (server.nics) {
      server.nics.forEach(nic => {
        nic.allInterfacesSelected = false
        if (nic.nic_info) {
          nic.nic_info.forEach(nicInfo => {
            nicInfo.selected = false
          })
        }
      })
    }
  }
}

// 获取服务器已选择的网口数量
const getSelectedInterfaceCount = (server: ServerDetailResponse): number => {
  let count = 0
  if (server.nics) {
    server.nics.forEach(nic => {
      if (nic.nic_info) {
        nic.nic_info.forEach(nicInfo => {
          if (nicInfo.selected) {
            count++
          }
        })
      }
    })
  }
  return count
}

// 获取单张网卡已选择的网口数量
const getSelectedInterfaceCountForNic = (nic: any): number => {
  if (!nic.nic_info) return 0
  return nic.nic_info.filter((info: any) => info.selected).length
}

// 获取总共选择的网口数量
const getTotalSelectedInterfaces = (): number => {
  let total = 0
  selectedServersWithNics.value.forEach(server => {
    total += getSelectedInterfaceCount(server)
  })
  return total
}

// 在 canExecute 计算属性中使用新的统计方法
const canExecute = computed(() => {
  return selectedServers.value.length > 0 && getTotalSelectedInterfaces() > 0
})

// 获取可测试网卡数量
const getTestableNicCount = (server: ServerDetailResponse): number => {
  return getTestableNics(server).length
}

// 获取可测试的网卡（非MV200且有网口信息）
const getTestableNics = (server: ServerDetailResponse): any[] => {
  if (!server.nics) return []
  
  return server.nics.filter(nic => {
    // 跳过MV200网卡
    if (isMv200Nic(nic.type)) return false
    // 只显示有网口信息的网卡
    return nic.nic_info && nic.nic_info.length > 0
  })
}

// 检查网卡是否部分选中
const isNicPartiallySelected = (nic: any): boolean => {
  if (!nic.nic_info || nic.nic_info.length === 0) return false
  
  const selectedCount = nic.nic_info.filter((info: any) => info.selected).length
  return selectedCount > 0 && selectedCount < nic.nic_info.length
}

// 处理网卡全选/全不选
const handleNicAllInterfacesChange = (nic: any) => {
  if (nic.nic_info) {
    nic.nic_info.forEach((info: any) => {
      info.selected = nic.allInterfacesSelected
    })
  }
}

// 处理单个网口选择变化
const handleInterfaceSelectionChange = (nic: any) => {
  if (nic.nic_info) {
    const selectedCount = nic.nic_info.filter((info: any) => info.selected).length
    const totalCount = nic.nic_info.length
    
    // 更新全选状态
    nic.allInterfacesSelected = selectedCount === totalCount
  }
}

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
    
    await loadBranchAndTag()
    
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

// 检查是否为MV200网卡
const isMv200Nic = (nicType: string | undefined): boolean => {
  if (!nicType) return false
  const typeLower = nicType.toLowerCase()
  return typeLower.includes('mv200') || typeLower.includes('marvell') || typeLower.includes('88e')
}

const hasSkippedMv200Nics = (server: ServerDetailResponse): boolean => {
  if (!server.nics) return false
  return server.nics.some(nic => isMv200Nic(nic.type))
}

const getTotalNicCount = (server: ServerDetailResponse): number => {
  return server.nics?.length || 0
}

const getMv200NicCount = (server: ServerDetailResponse): number => {
  if (!server.nics) return 0
  return server.nics.filter(nic => isMv200Nic(nic.type)).length
}

const getConfigurableNicCount = (server: ServerDetailResponse): number => {
  return getConfigurableNics(server).length
}

const getConfigurableNics = (server: ServerDetailResponse): any[] => {
  if (!server.nics) return []
  
  return server.nics.filter(nic => {
    // 跳过MV200网卡
    if (isMv200Nic(nic.type)) return false
    // 只显示有网口信息的网卡
    return nic.nic_info && nic.nic_info.length > 0
  })
}

const handleInterfaceConfigChange = (nicInfo: any) => {
  if (!nicInfo.enableConfig) {
    // 当关闭配置时，清空已配置的IP
    nicInfo.ipv4 = ''
    nicInfo.ipv6 = ''
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

// 格式化时间显示
const formatTime = (timeStr: string): string => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  return date.toLocaleDateString()
}

// 获取测试用例的简短名称
const getTestCaseName = (fullPath: string): string => {
  const parts = fullPath.split('::')
  return parts[parts.length - 1] || fullPath
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
    
    // 处理测试用例部分
    if (parts.length === 2) {
      // 格式：file::test_case
      // 这种情况没有类名，直接创建测试用例节点
      const testCasePart = parts[1]
      const testCaseId = currentPath + '::' + testCasePart
      const testCaseNode = {
        id: testCaseId,
        label: testCasePart,
        type: 'testCase',
        fullPath: testCase,
        testCaseCount: 1
      }
      
      if (!currentLevel.children) {
        currentLevel.children = []
      }
      currentLevel.children.push(testCaseNode)
      
    } else if (parts.length === 3) {
      // 格式：file::class::test_case
      const classPart = parts[1]
      const classId = currentPath + '::' + classPart
      let classNode = currentLevel.children?.find((child: any) => child.label === classPart)
      
      if (!classNode) {
        classNode = {
          id: classId,
          label: classPart,
          type: 'class',
          children: [],
          testCaseCount: 0
        }
        if (!currentLevel.children) {
          currentLevel.children = []
        }
        currentLevel.children.push(classNode)
      }
      
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
    } else if (parts.length === 1) {
      // 格式：file (只有文件路径，没有测试用例)
      // 这种情况不应该出现，但为了容错处理
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
  
  // 递归计算每个节点的测试用例数量
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
    
    // 加载用例集合列表
    await loadCombinations()
    
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
    // 直接获取 ExecuteResponse[] 数组
    const history: ExecuteResponse[] = await testApi.getExecuteHistory()
    // 按时间倒序排列（最新的在前面）
    executeHistory.value = history.sort((a, b) => {
      return new Date(b.time || 0).getTime() - new Date(a.time || 0).getTime()
    })
  } catch (error) {
    ElMessage.error('获取执行历史失败')
  } finally {
    historyLoading.value = false
  }
}

// 用例集合相关方法
const loadCombinations = async () => {
  try {
    const response = await testApi.getCustomCombinations()
    // 按创建时间从新到旧排序
    combinations.value = response.sort((a, b) => {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
  } catch (error) {
    ElMessage.error('加载用例集合失败')
  }
}

// 处理集合选择变化
const handleCombinationChange = (combinationId: string) => {
  if (!combinationId) {
    // 清空选择
    selectedCombinationId.value = ''
  }
}

// 获取网卡类型统计（基于实际的 nic.type）
const getNicTypeCounts = (server: ServerDetailResponse): Record<string, number> => {
  const typeCounts: Record<string, number> = {}
  
  if (server.nics) {
    server.nics.forEach(nic => {
      const type = (nic.type && nic.type.includes('metaScale-200') && nic.type.includes('OCP3.0')) 
        ? 'metaScale-200 OCP3.0'
        : (nic.type || '未知类型')
      typeCounts[type] = (typeCounts[type] || 0) + 1
    })
  }
  
  return typeCounts
}

// 保存当前集合
const saveCurrentCombination = () => {
  if (rightTestCases.value.length === 0) {
    ElMessage.warning('请先选择测试用例')
    return
  }
  
  // 生成包含年月日时分秒的默认名称
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  
  saveCombinationForm.value.name = `集合_${year}/${month}/${day}_${hours}:${minutes}:${seconds}`
  saveCombinationDialogVisible.value = true
}

// 确认保存集合
const confirmSaveCombination = async () => {
  try {
    const casePaths = rightTestCases.value.map(item => item.fullPath)
    
    const request: CaseCombinationRequest = {
      name: saveCombinationForm.value.name.trim(),
      cases: casePaths
    }
    
    await testApi.saveCustomCombination(request)
    
    ElMessage.success('用例集合保存成功')
    saveCombinationDialogVisible.value = false
    saveCombinationForm.value.name = ''
    
    // 重新加载集合列表
    await loadCombinations()
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存用例集合失败')
  }
}

// 加载集合到右侧
const loadCombinationToRight = async () => {
  if (!selectedCombinationId.value) {
    ElMessage.warning('请先选择用例集合')
    return
  }
  
  const combination = currentCombination.value
  if (!combination || !combination.cases || combination.cases.length === 0) {
    ElMessage.warning('该集合没有测试用例')
    return
  }
  
  try {
    // 清空右侧现有用例
    rightTestCases.value = []
    
    // 添加集合中的用例到右侧
    combination.cases.forEach((casePath: string) => {
      if (!rightTestCases.value.some(item => item.fullPath === casePath)) {
        rightTestCases.value.push({
          fullPath: casePath
        })
      }
    })
    
    // 如果有扫描过用例，更新左侧树
    if (collectedCases.value.length > 0) {
      const remainingCases = collectedCases.value.filter(casePath => 
        !rightTestCases.value.some(item => item.fullPath === casePath)
      )
      leftTestCasesTree.value = buildTestCasesTree(remainingCases)
    }
    
    ElMessage.success(`已加载集合 "${combination.name}" 的 ${combination.cases.length} 个测试用例`)
    
  } catch (error) {
    ElMessage.error('加载用例集合失败')
  }
}

// 删除集合
const deleteCombination = async () => {
  if (!selectedCombinationId.value) {
    return
  }
  
  const combination = currentCombination.value
  if (!combination) return
  
  try {
    await ElMessageBox.confirm(
      `确定要删除集合 "${combination.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    
    // 调用删除接口
    await testApi.deleteCustomCombination(combination.id)
    
    ElMessage.success('集合删除成功')
    
    // 重新加载集合列表
    await loadCombinations()
    
    // 清空选择
    selectedCombinationId.value = ''
    
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除集合失败')
    }
  }
}

// 修改 handleRunSelected 方法，打开服务器选择对话框
const handleRunSelected = async () => {
  if (rightTestCases.value.length === 0) {
    ElMessage.warning('请先添加测试用例')
    return
  }
  
  try {
    // 加载可用服务器
    await loadAvailableServers()
    
    if (availableServers.value.length === 0) {
      ElMessage.warning('没有可用的服务器，请先占用服务器')
      return
    }
    
    // 重置选择
    selectedServers.value = []
    
    // 打开服务器选择对话框
    serverDialogVisible.value = true
    
  } catch (error) {
    ElMessage.error('加载服务器列表失败')
  }
}

// 确认执行
const handleExecuteConfirm = async () => {
  try {
    executeLoading.value = true
    
    // 构建请求数据
    const selectedCases = rightTestCases.value.map(item => item.fullPath)
    
    // 构建服务器配置 - 按网口级别选择，使用 device_id
    const servers: Server[] = selectedServersWithNics.value.map(server => {
      const selectedNics: CaseNicInfo[] = []
      
      if (server.nics) {
        server.nics.forEach(nic => {
          // 跳过MV200网卡
          if (isMv200Nic(nic.type)) return
          
          // 处理非MV200网卡的每个网口
          if (nic.nic_info) {
            nic.nic_info.forEach(nicInfo => {
              // 只添加被选中的网口
              if (nicInfo.selected) {
                const caseNicInfo: CaseNicInfo = {
                  iface: nicInfo.iface,
                  bdf: nicInfo.bdf,
                  type: nic.type
                }
                selectedNics.push(caseNicInfo)
              }
            })
          }
        })
      }
      
      return {
        device_id: server.id!, // 使用 device_id
        nics: selectedNics.length > 0 ? selectedNics : undefined
      }
    })
    
    const request: ExecuteRequest = {
      cases: selectedCases,
      servers: servers.length > 0 ? servers : undefined
    }
    
    console.log('执行请求数据:', request)
    
    // 调用执行接口
    const loadingMessage = ElMessage.success('开始运行测试用例...')
    
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
    
    // 关闭对话框
    serverDialogVisible.value = false
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '执行测试用例失败')
  } finally {
    executeLoading.value = false
  }
}

const loadAvailableServers = async () => {
  try {
    const servers = await deviceApi.getAll()
    const currentUser = authStore.username  // 直接使用上面定义的 authStore
    
    // 过滤出当前用户占用的服务器
    availableServers.value = servers.filter(server => 
      server.user === currentUser && server.time && server.time > 0
    )
    
    // 为每个网卡的每个网口初始化选择属性
    availableServers.value.forEach(server => {
      if (server.nics) {
        server.nics.forEach(nic => {
          // 初始化全选状态
          nic.allInterfacesSelected = false
          
          if (nic.nic_info) {
            nic.nic_info.forEach(nicInfo => {
              // 初始化 selected 为 false
              if (nicInfo.selected === undefined) {
                nicInfo.selected = false
              }
            })
          }
        })
      }
    })
    
  } catch (error) {
    ElMessage.error('加载服务器列表失败')
  }
}

onMounted(() => {
  loadBranchAndTag()
  loadExecuteHistory()
  loadCombinations()
})
</script>
<style scoped>
.directory-picker-dialog {
  :deep(.el-dialog__body) {
    padding: 20px;
  }
}

.directory-picker {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.picker-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.directory-tree {
  height: 400px;
  overflow: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
}

.directory-node {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.directory-icon {
  color: #409eff;
}

.directory-name {
  font-size: 14px;
  color: #1f2937;
}

.disabled-node {
  opacity: 0.6;
  cursor: not-allowed !important;
}

.disabled-node .directory-name {
  color: #c0c4cc !important;
}

.disabled-tag {
  margin-left: 8px;
  font-size: 10px;
}

:deep(.el-tree-node.is-disabled .el-tree-node__content) {
  cursor: not-allowed !important;
  background-color: #f5f7fa !important;
}

:deep(.el-tree-node.is-disabled .el-tree-node__content:hover) {
  background-color: #f5f7fa !important;
}

.current-selection {
  margin-top: 12px;
}

.selected-dirs-list {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-dir-tag {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.qa-platform {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.top-section {
  display: flex;
  gap: 20px;
  margin-bottom: 30px;
}

.version-section {
  flex: 2;  /* 2份宽度 */
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.history-section {
  flex: 3;  /* 3份宽度 */
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  min-height: 400px;
  max-height: 500px;
}

.history-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.history-content :deep(.el-table .el-table__cell) {
  padding: 8px 4px;
}

/* 链接样式 */
.report-link,
.log-link {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.topo-btn {
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 拓扑对话框样式 */
.topo-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.yaml-container {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #f8fafc;
  max-height: 500px;
  overflow: auto;
}

.yaml-content {
  margin: 0;
  padding: 16px;
  font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: #2d3748;
  white-space: pre-wrap;
  word-break: break-all;
}

:deep(.history-content .el-table) {
  flex: 1;
  display: flex;
  flex-direction: column;
}

:deep(.history-content .el-table .el-table__body-wrapper) {
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
}

:deep(.history-content .el-table .el-table__body-wrapper::-webkit-scrollbar) {
  width: 6px;
}

:deep(.history-content .el-table .el-table__body-wrapper::-webkit-scrollbar-track) {
  background: #f1f1f1;
  border-radius: 3px;
}

:deep(.history-content .el-table .el-table__body-wrapper::-webkit-scrollbar-thumb) {
  background: #c1c1c1;
  border-radius: 3px;
}

:deep(.history-content .el-table .el-table__body-wrapper::-webkit-scrollbar-thumb:hover) {
  background: #a8a8a8;
}

:deep(.history-content .el-table .el-table__header-wrapper) {
  flex-shrink: 0;
}

:deep(.history-content .el-table__empty-block) {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.refresh-btn {
  margin-left: auto;
}

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

.current-version {
  margin-bottom: 16px;
}

.loading-version {
  display: flex;
  align-items: center;
}

.version-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.version-item {
  display: flex;
  align-items: center;
}

.current-tag {
  font-weight: 600;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.current-tag .el-icon {
  margin-right: 0;
  flex-shrink: 0;
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

.collect-section {
  margin-bottom: 30px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.management-layout {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.left-management,
.right-management {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.left-management {
  min-width: 0;
}

.right-management {
  min-width: 0;
}

.directory-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  height: fit-content;
}

.dir-controls {
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

.no-directories {
  padding: 8px 0;
  color: #c0c4cc;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.no-dirs-text {
  display: inline-block;
  padding: 4px 8px;
}

.select-dir-btn {
  width: 100%;
  margin-bottom: 12px;
}

.combinations-section {
  padding: 16px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  height: fit-content;
}

.combinations-control {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.combination-selection {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.combination-buttons {
  display: flex;
  width: 100px;
  gap: 8px;
}

.combination-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.case-count {
  margin-left: 8px;
}

.create-time {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.case-preview {
  max-height: 120px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 8px;
}

.preview-tag {
  margin: 2px;
}

.more-cases {
  font-size: 12px;
  color: #909399;
  text-align: center;
  padding: 4px;
}

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

.action-buttons {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.selection-container {
  display: flex;
  height: 500px;
  background: white;
  min-height: 0;
}

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

.tree-container::-webkit-scrollbar {
  height: 12px;
  width: 12px;
}

.tree-container:empty::before {
  content: "请先扫描测试用例或加载用例集合";
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #c0c4cc;
  font-style: italic;
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

.server-dialog {
  :deep(.el-dialog) {
    height: 80vh !important;
    max-height: 80vh !important;
    display: flex !important;
    flex-direction: column !important;
  }

  :deep(.el-dialog__header) {
    padding: 20px 20px 0 !important;
    margin-right: 0 !important;
    flex-shrink: 0 !important;
  }

  :deep(.el-dialog__body) {
    padding: 20px !important;
    flex: 1 !important;
    overflow-y: auto !important;
    min-height: 0 !important;
  }

  :deep(.el-dialog__footer) {
    padding: 16px 20px !important;
    border-top: 1px solid #e2e8f0 !important;
    background: #f8fafc !important;
    flex-shrink: 0 !important;
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
  justify-content: space-between;
  align-items: center;
  width: 100%;
  gap: 16px;
}

.cancel-btn {
  width: 100px;
}

.confirm-btn {
  width: 120px;
  font-weight: 600;
}

.server-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.server-nic-selection {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.server-list-with-nics {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.server-list-with-nics::-webkit-scrollbar {
  width: 8px;
}

.server-list-with-nics::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.server-list-with-nics::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.server-list-with-nics::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.server-item-with-nics {
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.server-checkbox {
  padding: 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.server-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: 8px;
}

.server-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 14px;
}

.server-ip {
  font-family: 'Monaco', 'Consolas', monospace;
  color: #64748b;
  font-size: 12px;
}

.no-servers {
  padding: 20px;
  text-align: center;
}

.nic-selection-area {
  padding: 16px;
  background: #fafbfc;
  border-top: 1px solid #e2e8f0;
  max-height: 400px;
  overflow-y: auto;
}

.nic-selection-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.nic-selection-header .el-icon {
  color: #409eff;
}

.nics-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: none;
  overflow-y: visible;
}

.nics-list::-webkit-scrollbar {
  width: 6px;
}

.nics-list::-webkit-scrollbar-track {
  background: #f8f9fa;
  border-radius: 3px;
}

.nics-list::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.nics-list::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.nic-item {
  padding: 12px;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.nic-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.nic-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nic-type {
  font-weight: 600;
  color: #1f2937;
  font-size: 14px;
}

.nic-sn {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: #64748b;
}

.nic-select-all {
  margin-right: 8px;
}

.nic-interfaces-selection {
  margin-top: 8px;
  padding: 8px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  max-height: 200px;
  overflow-y: auto;
}

.nic-interfaces-selection::-webkit-scrollbar {
  width: 4px;
}

.nic-interfaces-selection::-webkit-scrollbar-track {
  background: #f8f9fa;
  border-radius: 2px;
}

.nic-interfaces-selection::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 2px;
}

.selection-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.footer-stats {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-shrink: 0;
}

.footer-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}

.interfaces-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.nic-interface {
  padding: 8px 12px;
  background: #f8fafc;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  min-width: 120px;
  flex-shrink: 0;
}

.interface-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-left: 8px;
  text-align: center;
}

.iface-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 12px;
  white-space: nowrap;
}

.bdf {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 10px;
  color: #64748b;
}

:deep(.nic-interface .el-checkbox) {
  display: flex;
  align-items: center;
  width: 100%;
}

:deep(.nic-interface .el-checkbox__label) {
  padding-left: 4px;
  flex: 1;
}

.no-testable-nics {
  padding: 16px;
}

@media (max-width: 1200px) {
  .top-section {
    flex-direction: column;
  }
  
  .version-section,
  .history-section {
    flex: 1;
  }
}

@media (max-width: 768px) {
  .server-list-with-nics {
    max-height: 400px;
  }
  
  .nics-list {
    max-height: 300px;
  }

  .interfaces-list {
    gap: 8px;
  }

  .nic-interface {
    min-width: 100px;
    padding: 6px 8px;
  }

  .iface-name {
    font-size: 11px;
  }
  
  .bdf {
    font-size: 9px;
  }

  .server-dialog {
    :deep(.el-dialog) {
      height: 90vh !important;
      width: 95% !important;
      margin-top: 5vh !important;
    }
  }

  .nic-selection-area {
    max-height: 300px;
  }
  
  .nic-interfaces-selection {
    max-height: 150px;
  }

  .dialog-footer {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .footer-stats {
    justify-content: center;
    order: 2;
  }
  
  .footer-buttons {
    justify-content: space-between;
    order: 1;
  }

  .management-layout {
    flex-direction: column;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }

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

  .dir-controls {
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

  .combination-selection {
    flex-direction: column;
    align-items: flex-start;
  }

  .combination-buttons {
    flex-wrap: wrap;
  }
}

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