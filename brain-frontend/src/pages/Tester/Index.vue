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
          <span>测试用例管理</span>
        </div>

        <!-- 左右布局 -->
        <div class="management-layout">
          <!-- 左侧：目录配置 -->
          <div class="left-management">
            <div class="directory-config">
              <div class="dir-input-group">
                <el-input 
                  v-model="newDirectory" 
                  placeholder="输入测试用例目录路径，如: products/api_coverage"
                  @keyup.enter="addDirectory"
                  style="width: 100%"
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
                    placeholder="选择已有用例集合" 
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
                        <span class="create-time">{{ formatTime(combination.created_at) }}</span>
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
      title="选择执行服务器"
      width="800px"
      class="server-dialog"
      :close-on-click-modal="false"
    >
      <div class="server-dialog-content">
        <el-alert
          title="请选择用于执行测试用例的服务器，并为非MV200网卡配置IP地址"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />

        <!-- 服务器选择 -->
        <div class="server-selection">
          <div class="section-title">
            <el-icon><Monitor /></el-icon>
            <span>选择服务器</span>
          </div>
          <div class="server-list">
            <el-checkbox-group v-model="selectedServers">
              <div 
                v-for="server in availableServers" 
                :key="server.id"
                class="server-item"
              >
                <el-checkbox :label="server.id">
                  <div class="server-info">
                    <span class="server-name">{{ server.bmc.hostname }}</span>
                    <span class="server-ip">{{ server.device.ip }}</span>
                    <el-tag v-if="server.user" size="small" type="success">
                      占用人: {{ server.user }}
                    </el-tag>
                  </div>
                </el-checkbox>
              </div>
            </el-checkbox-group>
            <div v-if="availableServers.length === 0" class="no-servers">
              <el-empty description="暂无可用服务器，请先占用服务器" />
            </div>
          </div>
        </div>

        <!-- 网卡配置 -->
        <div class="nic-configuration" v-if="selectedServers.length > 0">
          <div class="section-title">
            <el-icon><Connection /></el-icon>
            <span>网卡IP配置 (可选)</span>
            <el-tag type="info" size="small">仅需为非MV200网卡配置IP</el-tag>
          </div>
          <div class="nic-config-list">
            <div 
              v-for="server in selectedServersWithNics" 
              :key="server.id"
              class="server-nics"
            >
              <div class="server-header">
                <h4>{{ server.bmc.hostname }} ({{ server.device.ip }})</h4>
                <div class="server-nic-stats">
                  <el-tag size="small" type="info">
                    总共 {{ getTotalNicCount(server) }} 张网卡
                  </el-tag>
                  <el-tag v-if="getMv200NicCount(server) > 0" size="small" type="success">
                    已忽略 {{ getMv200NicCount(server) }} 张MV200网卡
                  </el-tag>
                  <el-tag size="small" type="warning">
                    可配置 {{ getConfigurableNicCount(server) }} 张网卡
                  </el-tag>
                </div>
              </div>
              
              <!-- 修改网卡列表部分 -->
              <div class="nics-list">
                <!-- 显示可配置的非MV200网卡 -->
                <div 
                  v-for="nic in getConfigurableNics(server)" 
                  :key="nic?.sn || nic?.type"
                  class="nic-item"
                >
                  <div class="nic-info">
                    <div class="nic-type">
                      {{ nic.type || '未知类型' }}
                      <el-tag v-if="nic.nic_info" size="small" type="primary" style="margin-left: 8px;">
                        {{ nic.nic_info.length }} 个网口
                      </el-tag>
                    </div>
                    <div class="nic-details">
                      <span class="nic-sn">SN: {{ nic.sn || '未知SN' }}</span>
                    </div>
                  </div>
                  
                  <!-- 网口配置区域 - 每个网口单独配置 -->
                  <div class="nic-interfaces-config" v-if="nic.nic_info && nic.nic_info.length > 0">
                    <div 
                      v-for="(nicInfo, index) in nic.nic_info" 
                      :key="index"
                      class="nic-interface"
                    >
                      <div class="interface-header">
                        <div class="interface-info">
                          <span class="iface-name">{{ nicInfo.iface || `网口${index + 1}` }}</span>
                          <span class="bdf">{{ nicInfo.bdf || '未知BDF' }}</span>
                        </div>
                        <el-switch
                          v-model="nicInfo.enableConfig"
                          @change="handleInterfaceConfigChange(nicInfo)"
                          active-text="配置IP"
                          inactive-text="不配置"
                        />
                      </div>
                      
                      <!-- IP配置区域，只在启用配置时显示 -->
                      <div class="ip-inputs" v-if="nicInfo.enableConfig">
                        <el-input
                          v-model="nicInfo.ipv4"
                          placeholder="IPv4地址"
                          style="width: 200px; margin-right: 10px;"
                        />
                        <el-input
                          v-model="nicInfo.ipv6"
                          placeholder="IPv6地址"
                          style="width: 200px;"
                        />
                        <el-alert
                          v-if="!nicInfo.ipv4 && !nicInfo.ipv6"
                          title="请至少配置一个IP地址（IPv4或IPv6）"
                          type="warning"
                          :closable="false"
                          show-icon
                          style="margin-top: 8px; width: 420px;"
                        />
                      </div>
                    </div>
                  </div>
                  
                  <div v-else class="no-interfaces">
                    <el-alert
                      title="此网卡没有可配置的网口"
                      type="info"
                      :closable="false"
                      show-icon
                    />
                  </div>
                </div>
                
                <!-- 显示没有可配置网卡的情况 -->
                <div v-if="getConfigurableNicCount(server) === 0" class="no-configurable-nics">
                  <el-alert
                    title="此服务器没有需要配置IP的网卡（所有网卡均为MV200类型或无可配置网口）"
                    type="info"
                    :closable="false"
                    show-icon
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
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
            开始执行
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
  Refresh,
  Monitor,
  Connection,
  FolderOpened,
  FolderAdd,
  Lightning
} from '@element-plus/icons-vue'
import { testApi } from '@/api/tester'
import { deviceApi } from '@/api/device'
import { useAuthStore } from '@/stores/auth'
import type { 
  BranchAndTagResponse, 
  CheckoutRequest, 
  CasesResponse, 
  ExecuteResponse, 
  ExecuteListResponse,
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

// 用例集合相关数据
const combinations = ref<CaseCombinationsResponse[]>([])
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

// 修改 canExecute 计算属性，按网口级别检查
const canExecute = computed(() => {
  if (selectedServers.value.length === 0) return false
  
  // 检查所有启用了配置的网口是否都正确配置了IP
  for (const server of selectedServersWithNics.value) {
    for (const nic of server.nics || []) {
      // 跳过MV200网卡
      if (isMv200Nic(nic.type)) continue
      
      if (nic.nic_info) {
        for (const nicInfo of nic.nic_info) {
          // 如果启用了配置但未配置任何IP，则不能执行
          if (nicInfo.enableConfig && !nicInfo.ipv4 && !nicInfo.ipv6) {
            return false
          }
        }
      }
    }
  }
  
  return true
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

// 用例集合相关方法
// 加载用例集合列表
const loadCombinations = async () => {
  try {
    const response = await testApi.getCustomCombinations()
    combinations.value = response
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
  
  saveCombinationForm.value.name = `集合_${year}${month}${day}_${hours}${minutes}${seconds}`
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
    
    // 构建服务器配置 - 按网口级别配置，使用 device_id
    const servers: Server[] = selectedServersWithNics.value.map(server => {
      const configuredNics: CaseNicInfo[] = []
      
      if (server.nics) {
        server.nics.forEach(nic => {
          // 跳过MV200网卡
          if (isMv200Nic(nic.type)) return
          
          // 处理非MV200网卡的每个网口
          if (nic.nic_info) {
            nic.nic_info.forEach(nicInfo => {
              // 只有当启用了配置且配置了至少一个IP时才添加到请求中
              if (nicInfo.enableConfig && (nicInfo.ipv4 || nicInfo.ipv6)) {
                const caseNicInfo: CaseNicInfo = {
                  iface: nicInfo.iface,
                  bdf: nicInfo.bdf
                }
                
                if (nicInfo.ipv4) {
                  caseNicInfo.ipv4 = nicInfo.ipv4
                }
                if (nicInfo.ipv6) {
                  caseNicInfo.ipv6 = nicInfo.ipv6
                }
                
                configuredNics.push(caseNicInfo)
              }
            })
          }
        })
      }
      
      return {
        device_id: server.id!, // 使用 device_id 而不是 device_ip
        nics: configuredNics.length > 0 ? configuredNics : undefined
      }
    })
    
    const request: ExecuteRequest = {
      cases: selectedCases,
      servers: servers.length > 0 ? servers : undefined
    }
    
    console.log('执行请求数据:', request) // 调试用
    
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
    const authStore = useAuthStore()
    const currentUser = authStore.username
    
    // 过滤出当前用户占用的服务器
    availableServers.value = servers.filter(server => 
      server.user === currentUser && server.time && server.time > 0
    )
    
    // 为每个网卡的每个网口初始化配置属性
    availableServers.value.forEach(server => {
      if (server.nics) {
        server.nics.forEach(nic => {
          if (nic.nic_info) {
            nic.nic_info.forEach(nicInfo => {
              // 初始化 enableConfig 为 false
              if (nicInfo.enableConfig === undefined) {
                nicInfo.enableConfig = false
              }
              // 确保 ipv4 和 ipv6 字段存在
              if (!nicInfo.ipv4) nicInfo.ipv4 = ''
              if (!nicInfo.ipv6) nicInfo.ipv6 = ''
            })
          }
        })
      }
    })
    
    console.log('处理后的服务器数据:', availableServers.value)
    // 调试信息：显示每个服务器的 device_id
    availableServers.value.forEach(server => {
      console.log(`服务器 ${server.bmc.hostname} 信息:`, {
        device_id: server.id,
        device_ip: server.device.ip,
        总网卡数: getTotalNicCount(server),
        MV200网卡数: getMv200NicCount(server),
        可配置网卡数: getConfigurableNicCount(server)
      })
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

/* 管理布局样式 */
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

/* 目录配置样式 */
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

/* 用例集合管理区域 */
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

.action-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
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

.server-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 20px 0;
    margin-right: 0;
  }

  :deep(.el-dialog__body) {
    padding: 20px;
    max-height: 70vh;
    overflow-y: auto;
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

.server-nic-stats {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.interfaces-title {
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
  font-size: 14px;
}

/* 服务器选择对话框样式 */
.server-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.server-selection {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
}

.server-list {
  max-height: 200px;
  overflow-y: auto;
}

.server-item {
  padding: 8px 0;
  border-bottom: 1px solid #e2e8f0;
}

.server-item:last-child {
  border-bottom: none;
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

.nic-configuration {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #f8fafc;
}

.nic-config-list {
  max-height: 400px;
  overflow-y: auto;
}

.server-nics {
  margin-bottom: 20px;
  padding: 16px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.server-nics:last-child {
  margin-bottom: 0;
}

.server-header {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.server-header h4 {
  margin: 0;
  color: #1f2937;
}

.nics-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.nic-item {
  padding: 12px;
  background: #f8fafc;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.nic-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.nic-type {
  font-weight: 600;
  color: #1f2937;
}

.nic-details {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
}

.nic-ip-config {
  margin-top: 12px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.nic-interfaces-config {
  margin-top: 12px;
  padding: 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.nic-interface {
  padding: 12px;
  background: #f8fafc;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
  margin-bottom: 12px;
}

.nic-interface:last-child {
  margin-bottom: 0;
}

.interface-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.interface-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.iface-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 14px;
}

.bdf {
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  color: #64748b;
}

.ip-inputs {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.no-interfaces,
.no-configurable-nics {
  margin-top: 12px;
}

.mv200-note {
  margin-top: 8px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .top-section {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
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

  .server-nic-stats {
    flex-direction: column;
    align-items: flex-start;
  }

  .interface-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .ip-inputs {
    flex-direction: column;
    align-items: stretch;
  }
  
  .ip-inputs .el-input {
    width: 100% !important;
    margin-right: 0 !important;
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

  .ip-inputs {
    flex-direction: column;
    align-items: stretch;
  }

  .ip-inputs .el-input {
    width: 100% !important;
    margin-right: 0 !important;
  }

  .combination-selection {
    flex-direction: column;
    align-items: flex-start;
  }

  .combination-buttons {
    flex-wrap: wrap;
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