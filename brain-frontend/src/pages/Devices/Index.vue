<template>
  <div class="device-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>服务器管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchKeyword"
              placeholder="搜索服务器名称、IP、网卡信息、标签、备注、占用人"
              clearable
              style="width: 400px; margin-right: 16px;"
              @input="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            
            <!-- 批量操作按钮 -->
            <el-dropdown @command="handleBatchCommand" :disabled="selectedDevices.length === 0">
              <el-button type="primary">
                批量操作<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item 
                    command="batchRelease" 
                    class="batch-release-item"
                    :disabled="!canBatchRelease"
                  >
                    <el-icon><Unlock /></el-icon>
                    <span>释放占用</span>
                    <el-tooltip 
                      v-if="!canBatchRelease && selectedDevices.length > 0"
                      effect="dark" 
                      :content="getBatchReleaseTooltip()"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  <el-dropdown-item command="batchPowerCycle" divided class="batch-power-item">
                    <el-icon><Refresh /></el-icon>
                    <span>冷重启</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="batchPowerReset" class="batch-power-item">
                    <el-icon><RefreshRight /></el-icon>
                    <span>热重启</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="batchDelete" divided class="danger-item">
                    <el-icon><Delete /></el-icon>
                    <span>删除</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            
            <el-button type="primary" @click="$router.push('/devices/create')" style="margin-left: 12px;">
              纳管服务器
            </el-button>
          </div>
        </div>
      </template>

      <el-table 
        :data="filteredDevices" 
        v-loading="loading"
        :default-sort="{ prop: 'device.ip', order: 'ascending' }"
        @selection-change="handleSelectionChange"
      >
        <!-- 多选列 -->
        <el-table-column type="selection" width="35" />

        <el-table-column 
          prop="bmc.hostname" 
          label="服务器名称"
          sortable
          width="120"
        >
          <template #default="{ row }">
            <el-link 
              type="primary" 
              @click="handleDetail(row)"
              class="hostname-link underlined-link"
              :underline="false"
            >
              {{ row.bmc.hostname }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column 
          prop="device.ip" 
          label="管理IP"
          sortable
          :sort-method="ipSortMethod"
          width="110"
        >
          <template #default="{ row }">
            <span class="highlight-ip">{{ row.device.ip }}</span>
          </template>
        </el-table-column>
        <el-table-column 
          label="网卡信息"
          min-width="170"
        >
          <template #default="{ row }">
            <div v-if="getNicSummary(row).length > 0" class="nic-summary-compact">
              <div 
                v-for="(summary, index) in getNicSummary(row)" 
                :key="summary.type"
                class="nic-item"
                :style="getNicItemStyle(summary.type)"
              >
                <span class="nic-count">{{ summary.count }}</span>
                <span class="nic-type">{{ summary.displayType }}</span>
              </div>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column 
          label="标签"
          min-width="200"
        >
          <template #default="{ row }">
            <div v-if="row.tags && row.tags.length > 0" class="tags-container">
              <el-tag 
                v-for="tag in row.tags" 
                :key="tag" 
                size="small"
                closable
                @close="(e) => handleRemoveTag(e, tag, row)"
                class="tag-item"
                :style="getTagStyle(tag)"
              >
                {{ tag }}
              </el-tag>
              <el-button 
                type="primary" 
                text 
                size="small" 
                @click="showAddTagDialog(row)"
                class="add-tag-btn"
              >
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>
            <div v-else class="no-tags">
              <span class="empty-text">-</span>
              <el-button 
                type="primary" 
                text 
                size="small" 
                @click="showAddTagDialog(row)"
              >
                <el-icon><Plus /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column 
          prop="notes" 
          label="备注"
          show-overflow-tooltip
          min-width="240"
        >
          <template #default="{ row }">
            <span v-if="row.notes">{{ row.notes }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column 
          label="MCR版本"
          width="105"
        >
          <template #default="{ row }">
            <div v-if="row.task_id" class="mcr-status">
              <template v-if="!taskStatusMap[row.task_id]">
                <!-- 状态查询中 -->
                <el-icon class="loading-spinner"><Loading /></el-icon>
                <span class="status-text">查询中...</span>
              </template>
              <template v-else>
                <el-tooltip
                  placement="top"
                  popper-class="mcr-status-tooltip"
                >
                  <template #content>
                    <div class="mcr-tooltip-content">
                      <div>MCR: {{ getMcrPackage(row) }}</div>
                      <div>选项: {{ getTaskOption(row) }}</div>
                      <div>步骤: {{ getStageText(getTaskStage(row)) }}</div>
                      <div v-if="getTaskDetail(row)" class="detail-section">
                        <div>详情:</div>
                        <pre class="detail-text">{{ cleanAnsiCodes(getTaskDetail(row)) }}</pre>
                      </div>
                    </div>
                  </template>
                  <el-tag 
                    :type="getMcrStatusType(row)" 
                    size="small"
                    class="mcr-status-tag"
                  >
                    {{ getMcrStatusText(row) }}
                  </el-tag>
                </el-tooltip>
                <el-icon 
                  v-if="getMcrStatus(row) === 'running'" 
                  class="loading-spinner"
                >
                  <Loading />
                </el-icon>
              </template>
            </div>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <el-table-column 
          prop="user" 
          label="占用人"
          sortable
          width="90"
        >
          <template #default="{ row }">
            <el-tag v-if="isDeviceOccupied(row)" type="success" size="small">{{ row.user }}</el-tag>
            <el-tag v-else type="info" size="small">未占用</el-tag>
          </template>
        </el-table-column>
        <el-table-column 
          label="占用截至时间"
          sortable
          :sort-method="timeSortMethod"
          width="150"
        >
          <template #default="{ row }">
            <span v-if="isDeviceOccupied(row) && row.time">{{ getEndTimeDisplay(row) }}</span>
            <span v-else class="empty-text">-</span>
          </template>
        </el-table-column>
        <!-- 关注列 -->
        <el-table-column label="关注" width="80" align="center">
          <template #header>
            <span>关注</span>
            <el-tooltip 
              effect="dark" 
              content="关注服务器，将会接收到服务器释放的提醒邮件"
              placement="top"
            >
              <el-icon style="margin-left: 4px; cursor: help;">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <el-button 
              :type="isFollowing(row) ? 'danger' : 'default'" 
              :icon="isFollowing(row) ? 'StarFilled' : 'Star'"
              @click="handleFollow(row)"
              :loading="followLoading[row.id!]"
              size="small"
              circle
              class="follow-heart-btn"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-dropdown @command="(command) => handleCommand(command, row)" size="small">
              <el-button type="primary" link>
                <el-icon :size="16"><MoreFilled /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu class="action-dropdown-menu">
                  <el-dropdown-item command="detail" class="dropdown-item">
                    <el-icon><View /></el-icon>
                    <span>详情</span>
                  </el-dropdown-item>
                  <el-dropdown-item command="edit" class="dropdown-item">
                    <el-icon><Edit /></el-icon>
                    <span>编辑</span>
                  </el-dropdown-item>
                  
                  <!-- 新增：修改启动项 -->
                  <el-dropdown-item 
                    command="bootEntry" 
                    class="dropdown-item boot-entry-item"
                    @click="handleBootEntryDialog(row)"
                  >
                    <el-icon><Setting /></el-icon>
                    <span>修改启动项</span>
                  </el-dropdown-item>

                  <!-- 新增：电源操作 -->
                  <el-dropdown-item 
                    command="powerCycle" 
                    class="dropdown-item power-cycle-item"
                  >
                    <el-icon><Refresh /></el-icon>
                    <span>冷重启</span>
                  </el-dropdown-item>
                  <el-dropdown-item 
                    command="powerReset" 
                    class="dropdown-item power-reset-item"
                  >
                    <el-icon><RefreshRight /></el-icon>
                    <span>热重启</span>
                  </el-dropdown-item>

                  <!-- 新增：更新MCR包 -->
                  <el-dropdown-item 
                    command="updateMcr" 
                    class="dropdown-item update-mcr-item"
                    @click="handleUpdateMcrDialog(row)"
                  >
                    <el-icon><Upload /></el-icon>
                    <span>更新MCR包</span>
                  </el-dropdown-item>
                  
                  <!-- 占用服务器按钮 -->
                  <el-dropdown-item 
                    command="occupy" 
                    :disabled="isDeviceOccupied(row) && !isCurrentUserOccupier(row)"
                    class="occupy-item occupy-server-item dropdown-item"
                  >
                    <el-icon><Timer /></el-icon>
                    <span>
                      {{ getOccupyButtonText(row) }}
                    </span>
                    <el-tooltip 
                      v-if="isDeviceOccupied(row) && !isCurrentUserOccupier(row)"
                      effect="dark" 
                      content="当前服务器已被占用，请联系占用人"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  
                  <!-- 释放占用按钮 -->
                  <el-dropdown-item 
                    command="release" 
                    :disabled="!isDeviceOccupied(row) || !isCurrentUserOccupier(row)"
                    class="occupy-item end-occupy-item dropdown-item"
                  >
                    <el-icon><Unlock /></el-icon>
                    <span>释放占用</span>
                    <el-tooltip 
                      v-if="!isDeviceOccupied(row)"
                      effect="dark" 
                      content="服务器未被占用"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                    <el-tooltip 
                      v-else-if="isDeviceOccupied(row) && !isCurrentUserOccupier(row)"
                      effect="dark" 
                      content="当前用户不是占用人，请联系占用人"
                      placement="top"
                    >
                      <el-icon style="margin-left: 4px;"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided class="danger-item dropdown-item">
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

    <!-- 占用/修改时间对话框 -->
    <el-dialog
      v-model="occupyDialogVisible"
      :title="occupyDialogTitle"
      width="480px"
      class="occupy-dialog"
      :close-on-click-modal="false"
    >
      <div class="dialog-header">
        <div class="device-info">
          <el-icon class="server-icon"><Monitor /></el-icon>
          <div class="info-content">
            <div class="hostname">{{ currentDevice?.bmc.hostname }}</div>
            <div class="ip-address">{{ currentDevice?.device.ip }}</div>
          </div>
        </div>
        <div class="user-info">
          <el-avatar :size="32" style="background-color: #409eff;">
            {{ currentUser?.charAt(0).toUpperCase() }}
          </el-avatar>
          <span class="username">{{ currentUser }}</span>
        </div>
      </div>

      <div v-if="isModifyMode && currentDevice?.time" class="original-time">
        <el-icon><Clock /></el-icon>
        <span>原截止时间：</span>
        <strong>{{ getEndTimeDisplay(currentDevice) }}</strong>
      </div>

      <el-form :model="occupyForm" class="occupy-form" label-width="auto">
        <div class="form-section">
          <div class="section-title">
            <el-icon><Calendar /></el-icon>
            <span>{{ isModifyMode ? '设置新的结束时间' : '设置占用结束时间' }}</span>
          </div>
          
          <el-form-item class="compact-item">
            <template #label>
              <span class="form-label">结束时间</span>
              <span class="required">*</span>
            </template>
            <el-date-picker
              v-model="occupyForm.endTime"
              type="datetime"
              placeholder="选择占用结束时间"
              style="width: 100%"
              :disabled-date="disabledDate"
              :disabled-hours="disabledHours"
              :disabled-minutes="disabledMinutes"
              :disabled-seconds="disabledSeconds"
              :shortcuts="timeShortcuts"
              class="enhanced-picker"
            />
          </el-form-item>

        <el-form-item class="compact-item">
          <template #label>
            <span class="form-label">占用时长</span>
          </template>
          <div class="duration-display">
            <el-tag 
              :type="getDurationType()" 
              class="duration-tag"
              :class="getDurationSize()"
            >
              <el-icon><Watch /></el-icon>
              {{ calculateDuration() }}
            </el-tag>
            <div v-if="occupyForm.endTime" class="duration-detail">
              <span class="end-time">截止: {{ getEndTimeDisplayFromForm() }}</span>
              <span class="duration-tip" v-if="getDurationSeconds() > 259200">
                <el-icon><Warning /></el-icon>
                超过3天限制
              </span>
            </div>
          </div>
        </el-form-item>
        </div>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="occupyDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handleOccupy" 
            :loading="occupyLoading"
            :disabled="!occupyForm.endTime"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            {{ isModifyMode ? '确认修改' : '确认占用' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 添加标签对话框 -->
    <el-dialog
      v-model="showAddTagDialogVisible"
      title="管理标签"
      width="500px"
      :before-close="handleTagDialogClose"
    >
      <div class="tag-dialog-content">
        <div class="tag-selection">
          <el-select
            v-model="selectedTags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="选择或输入标签"
            style="width: 100%"
            :loading="tagsLoading"
            @blur="handleTagDialogBlur"
            @change="handleTagDialogChange"
          >
            <el-option
              v-for="tag in availableTags"
              :key="tag.id"
              :label="tag.name"
              :value="tag.name"
            />
          </el-select>
        </div>
        
        <div class="existing-tags" v-if="availableTags.length > 0">
          <div class="dialog-tip">已有标签</div>
          <div class="tags-list">
            <el-tag
              v-for="tag in availableTags"
              :key="tag.id"
              class="tag-item"
              :style="getTagStyle(tag.name)"
              @click="toggleTag(tag.name)"
            >
              {{ tag.name }}
            </el-tag>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="handleTagDialogClose">取消</el-button>
        <el-button type="primary" @click="handleAddTags" :loading="addingTags">
          确认更新
        </el-button>
      </template>
    </el-dialog>

    <!-- 新增：修改启动项对话框 -->
    <el-dialog
      v-model="bootEntryDialogVisible"
      title="修改启动项"
      width="700px"
      class="boot-entry-dialog"
      :close-on-click-modal="false"
    >
      <div class="boot-entries-content" v-loading="bootEntriesLoading">
        <div class="dialog-header">
          <div class="device-info">
            <el-icon class="server-icon"><Monitor /></el-icon>
            <div class="info-content">
              <div class="hostname">{{ currentDevice?.bmc.hostname }}</div>
              <div class="ip-address">{{ currentDevice?.device.ip }}</div>
            </div>
          </div>
          <div class="user-info">
            <el-avatar :size="32" style="background-color: #409eff;">
              {{ currentUser?.charAt(0).toUpperCase() }}
            </el-avatar>
            <span class="username">{{ currentUser }}</span>
          </div>
        </div>
        <!-- 启动项选择 -->
        <div class="boot-selection">
          <div class="section-title">
            <el-icon><Setting /></el-icon>
            <span>选择下次启动项</span>
          </div>

          <div v-if="bootEntriesList.length > 0" class="boot-entries-list">
            <div
              v-for="entry in bootEntriesList"
              :key="entry.key"
              class="boot-entry-item"
              :class="{
                'current-entry': entry.isCurrent,
                'selected-entry': selectedBootEntry === entry.key
              }"
              @click="selectedBootEntry = entry.key"
            >
              <div class="boot-entry-content">
                <div class="boot-entry-main">
                  <el-radio 
                    v-model="selectedBootEntry" 
                    :label="entry.key"
                    class="boot-radio"
                  >
                    <div class="boot-entry-text">{{ entry.value }}</div>
                  </el-radio>
                  <div class="boot-entry-tags">
                    <el-tag v-if="entry.isCurrent" type="success" size="small">当前</el-tag>
                    <el-tag v-if="entry.isNext" type="warning" size="small">下次</el-tag>
                    <el-tag v-if="entry.isDefault" type="info" size="small">默认</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="no-boot-entries">
            <el-empty description="暂无启动项信息" />
          </div>

          <!-- 启动选项 -->
          <div class="boot-options">
            <el-checkbox v-model="setAsDefaultBoot" class="default-boot-checkbox">
              设置为默认启动项
            </el-checkbox>
            <div class="option-tip">
              勾选后，此启动项将作为服务器的默认启动项
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="bootEntryDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handleSetBootEntry" 
            :loading="bootEntryLoading"
            :disabled="!selectedBootEntry"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            确认修改
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 新增：批量操作对话框 -->
    <el-dialog
      v-model="batchDialogVisible"
      :title="batchDialogTitle"
      width="500px"
      class="batch-dialog"
      :close-on-click-modal="false"
    >
      <div class="batch-dialog-content">
        <!-- 批量操作确认信息 -->
        <div class="batch-confirm-info">
          <el-alert
            :title="getBatchConfirmMessage()"
            :type="getBatchAlertType()"
            :closable="false"
            show-icon
          />
          <div v-if="batchOperation === 'batchRelease'" class="warning-tip">
            <el-icon><Warning /></el-icon>
            <span>注意：只能释放当前用户占用的服务器，已自动过滤非当前用户占用的服务器</span>
          </div>
          <div v-if="batchOperation === 'batchDelete'" class="warning-tip">
            <el-icon><Warning /></el-icon>
            <span>注意：删除后服务器将不受云管控制, 请谨慎操作！</span>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="batchDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            :type="getBatchConfirmButtonType()"
            @click="handleBatchConfirm" 
            :loading="batchLoading"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            {{ getBatchConfirmButtonText() }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 新增：电源重启确认对话框 -->
    <el-dialog
      v-model="powerDialogVisible"
      :title="powerDialogTitle"
      width="400px"
      class="power-dialog"
      :close-on-click-modal="false"
    >
      <div class="power-dialog-content">
        <div class="dialog-tip">
          <el-alert
            :title="powerType === 'cycle' ? '冷重启将完全断电后重新启动服务器' : '热重启将保持通电状态重新启动服务器'"
            type="warning"
            :closable="false"
            show-icon
          />
        </div>
        <div class="confirm-message">
          <p v-if="isBatchPowerOperation">
            确定要对 <strong>{{ selectedDevices.length }} 台服务器</strong> 执行{{ powerType === 'cycle' ? '冷重启' : '热重启' }}吗？
          </p>
          <p v-else>
            确定要对服务器 <strong>"{{ currentDevice?.bmc.hostname }}"</strong> 执行{{ powerType === 'cycle' ? '冷重启' : '热重启' }}吗？
          </p>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button 
            @click="powerDialogVisible = false" 
            size="large"
            class="cancel-btn"
          >
            取消
          </el-button>
          <el-button 
            type="primary" 
            @click="handlePowerConfirm" 
            :loading="powerLoading"
            size="large"
            class="confirm-btn"
          >
            <template #loading>
              <el-icon class="is-loading"><Loading /></el-icon>
            </template>
            确认重启
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 新增：更新MCR包对话框 -->
    <el-dialog
      v-model="updateMcrDialogVisible"
      title="更新MCR包"
      width="800px"
      class="update-mcr-dialog"
      :close-on-click-modal="false"
    >
      <div class="update-mcr-content" v-loading="mcrLoading">
        <div class="dialog-header">
          <div class="device-info">
            <el-icon class="server-icon"><Monitor /></el-icon>
            <div class="info-content">
              <div class="hostname">{{ currentDevice?.bmc.hostname }}</div>
              <div class="ip-address">{{ currentDevice?.device.ip }}</div>
            </div>
          </div>
          <div class="current-path">
            <el-input
              v-model="currentPathInput"
              @keyup.enter="handlePathInputEnter"
              @blur="handlePathInputBlur"
              class="path-input"
            />
          </div>
        </div>

        <div class="file-browser">
          <div class="section-title">
            <div class="title-left">
              <el-icon><Folder /></el-icon>
              <span>选择MCR包文件</span>
              <el-input
                v-model="fileFilterText"
                placeholder="筛选文件或文件夹..."
                clearable
                style="width: 150px; margin-left: 16px;"
                size="small"
                :prefix-icon="Search"
              />
              <el-tag v-if="selectedMcrFile" type="success" size="small" style="margin-left: 16px;">
                已选择: {{ getFileName(selectedMcrFile) }}
              </el-tag>
            </div>
          </div>

          <div class="file-list">
            <div 
              v-for="item in filteredFileList" 
              :key="item.name"
              class="file-item"
              :class="{
                'directory-item': item.type === 'directory',
                'file-item-selected': item.type === 'file' && selectedMcrFile === getFullPath(item.name),
                'mcr-file': item.type === 'file' && isMcrFile(item.name)
              }"
              @click="handleFileItemClick(item)"
            >
              <div class="file-icon">
                <el-icon v-if="item.type === 'directory'">
                  <Folder />
                </el-icon>
                <el-icon v-else-if="isMcrFile(item.name)" class="mcr-file-icon">
                  <Document />
                </el-icon>
                <el-icon v-else>
                  <Document />
                </el-icon>
              </div>
              <div class="file-info">
                <div class="file-name" :class="{ 'mcr-file-name': isMcrFile(item.name) }">
                  {{ item.name }}
                  <el-tag v-if="isMcrFile(item.name)" type="warning" size="small" class="mcr-tag">
                    MCR
                  </el-tag>
                </div>
              </div>
              <div class="file-action" v-if="item.type === 'directory'">
                <el-icon><ArrowRight /></el-icon>
              </div>
            </div>

            <div v-if="fileList.length === 0" class="empty-files">
              <el-empty description="该目录为空" />
            </div>
          </div>
  
          <div v-if="filteredFileList.length === 0" class="empty-files">
            <el-empty :description="fileFilterText ? '未找到匹配的文件' : '该目录为空'" />
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <!-- 左侧添加更新选项 -->
          <div class="update-options-left">
            <span class="options-label">更新选项：</span>
            <el-radio-group v-model="updateOption" size="large">
              <el-radio label="all">全部更新</el-radio>
              <el-radio label="fw">仅更新固件</el-radio>
              <el-radio label="no-fw">不更新固件</el-radio>
            </el-radio-group>
          </div>
          
          <!-- 右侧按钮 -->
          <div class="footer-buttons">
            <el-button 
              @click="updateMcrDialogVisible = false" 
              size="large"
              class="cancel-btn"
            >
              取消
            </el-button>
            <el-button 
              type="primary" 
              @click="handleResetMcr" 
              :loading="upgradeMcrLoading"
              :disabled="!selectedMcrFile"
              size="large"
              class="confirm-btn"
            >
              <el-tooltip
                v-if="!selectedMcrFile"
                effect="dark"
                content="请选择MCR包"
                placement="top"
              >
                <span>确认更新</span>
              </el-tooltip>
              <span v-else>确认更新</span>
              
              <template #loading>
                <el-icon class="is-loading"><Loading /></el-icon>
              </template>
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  MoreFilled, 
  Edit, 
  Delete, 
  Search, 
  View, 
  Timer, 
  Unlock, 
  InfoFilled, 
  Plus,
  Monitor,
  Clock,
  Calendar,
  Watch,
  Loading,
  Setting,
  Refresh,
  RefreshRight,
  ArrowDown,
  Warning,
  StarFilled,
  Star,
  Upload,
  Folder,
  Document,
  ArrowRight,
  QuestionFilled
} from '@element-plus/icons-vue'
import { deviceApi } from '@/api/device'
import { remotefsApi, tagApi, tasksApi } from '@/api/common'
import type { ServerDetailResponse, ServerUpdateRequest, TagResponse, BootEntriesResponse, TaskStatusResponse } from '@/types/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const devices = ref<ServerDetailResponse[]>([])
const searchKeyword = ref('')
const selectedDevices = ref<ServerDetailResponse[]>([])

// 当前用户信息
const currentUser = computed(() => authStore.username)

// 占用服务器相关
const occupyDialogVisible = ref(false)
const occupyLoading = ref(false)
const currentDevice = ref<ServerDetailResponse | null>(null)
const occupyForm = reactive({
  endTime: null as Date | null
})

// 标签管理相关
const showAddTagDialogVisible = ref(false)
const selectedTags = ref<string[]>([])
const availableTags = ref<TagResponse[]>([])
const tagsLoading = ref(false)
const addingTags = ref(false)
const editingDevice = ref<ServerDetailResponse | null>(null)

// 启动项管理相关
const bootEntryDialogVisible = ref(false)
const bootEntryLoading = ref(false)
const bootEntriesLoading = ref(false)
const bootEntriesData = ref<BootEntriesResponse | null>(null)
const selectedBootEntry = ref<string>('')
const setAsDefaultBoot = ref(false)

// 批量操作相关
const batchDialogVisible = ref(false)
const batchLoading = ref(false)
const batchOperation = ref<string>('')

// 电源操作相关
const powerDialogVisible = ref(false)
const powerLoading = ref(false)
const powerType = ref<'cycle' | 'reset'>('cycle')
const isBatchPowerOperation = ref(false)

// 关注相关
const followLoading = ref<Record<string, boolean>>({})

// MCR包更新相关
const updateMcrDialogVisible = ref(false)
const mcrLoading = ref(false)
const upgradeMcrLoading = ref(false)
const fileList = ref<any[]>([])
const currentPath = ref('/auto/asic-dump/meta_release')
const selectedMcrFile = ref('')
const fileFilterText = ref('')
const directoryCache = ref<Record<string, any[]>>({})
const updateOption = ref<'all' | 'fw' | 'no-fw'>('all')
const currentPathInput = ref('')
const taskStatusMap = ref<Record<string, TaskStatusResponse>>({})
const taskStatusTimers = ref<Record<string, number>>({})

// MCR状态相关方法
const getMcrStatus = (device: ServerDetailResponse): string => {
  if (!device.task_id) return ''
  return taskStatusMap.value[device.task_id]?.status || ''
}

const getMcrStatusText = (device: ServerDetailResponse) => {
  const status = getMcrStatus(device)
  const stage = taskStatusMap.value[device.task_id!]?.stage || ''
  
  const statusMap: Record<string, string> = {
    'pending': '等待中',
    'running': getStageText(stage),
    'finished': '更新完成',
    'failed': '更新失败',
    'reboot_timeout': '重启超时'  // 新增状态
  }
  
  return statusMap[status] || status
}

// 获取 MCR 包信息
const getMcrPackage = (device: ServerDetailResponse): string => {
  if (!device.task_id) return '-'
  return taskStatusMap.value[device.task_id]?.mcr || '-'
}

const getTaskOption = (device: ServerDetailResponse): string => {
  if (!device.task_id) return '-'
  const option = taskStatusMap.value[device.task_id]?.option || '-'
  if (option === "fw") {
    return "仅更新固件"
  } else if (option === "no-fw") {
    return "不更新固件"
  } else if (option === "all") {
    return "全部更新"
  }
  return option
}

const getStageText = (stage: string) => {
  const stageMap: Record<string, string> = {
    'getting_mcr': '下载MCR包',
    'uninstalling_mcr': '卸载旧MCR',
    'installing_mcr': '安装新MCR',
    'upgrading_fw': '升级固件',    // 新增阶段
    'erasing_bdf': '擦拭设备',      // 新增阶段
    'reboot': '热重启',              // 新增阶段
    'waiting': '等待中'
  }
  return stageMap[stage] || stage
}

const getMcrStatusType = (device: ServerDetailResponse) => {
  const status = getMcrStatus(device)
  const typeMap: Record<string, any> = {
    'pending': 'info',
    'running': 'warning',
    'finished': 'success',
    'failed': 'danger',
    'reboot_timeout': 'danger'  // 新增状态类型
  }
  return typeMap[status] || 'info'
}

const getTaskStage = (device: ServerDetailResponse): string => {
  if (!device.task_id) return ''
  return taskStatusMap.value[device.task_id]?.stage || ''
}

// 获取任务详情
const getTaskDetail = (device: ServerDetailResponse): string => {
  if (!device.task_id) return ''
  return taskStatusMap.value[device.task_id]?.detail || ''
}

// 清理ANSI颜色代码和处理转义字符
const cleanAnsiCodes = (text: string): string => {
  try {
    // 使用JSON.parse来处理所有转义字符
    let cleaned = JSON.parse(`"${text}"`)
    
    // 移除ANSI颜色代码
    cleaned = cleaned.replace(/\u001b\[\d+(;\d+)*m/g, '')
    
    // 清理多余的换行
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n')
    
    return cleaned.trim()
  } catch (error) {
    // 如果JSON解析失败，回退到简单处理
    return text
      .replace(/\\n/g, '\n')
      .replace(/\u001b\[\d+(;\d+)*m/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  }
}

// 查询任务状态
const queryTaskStatus = async (device: ServerDetailResponse) => {
  if (!device.task_id) return
  
  try {
    const taskStatus: TaskStatusResponse = await tasksApi.getTaskStatus(device.task_id)
    
    // 更新状态映射
    taskStatusMap.value[device.task_id] = taskStatus
    
    // 检查任务是否超时（超过1小时）
    const taskStartTime = new Date(taskStatus.timestamp).getTime()
    const currentTime = new Date().getTime()
    const taskDuration = currentTime - taskStartTime
    const oneHour = 60 * 60 * 1000 // 1小时的毫秒数
    
    if (taskDuration > oneHour && taskStatus.status === 'running') {
      console.warn(`任务 ${device.task_id} 已运行超过1小时，停止轮询`)
      // 更新状态为超时
      taskStatusMap.value[device.task_id] = {
        ...taskStatus,
        status: 'failed',
        detail: '任务执行超时（超过1小时）'
      }
      
      // 清除定时器
      if (taskStatusTimers.value[device.id!]) {
        clearTimeout(taskStatusTimers.value[device.id!])
        delete taskStatusTimers.value[device.id!]
      }
      return
    }
    
    // 如果状态是running，根据阶段设置不同的轮询间隔
    if (taskStatus.status === 'running') {
      let queryInterval = 1000 // 默认1秒间隔
      
      if (taskStatus.stage === 'getting_mcr') {
        // 对于getting_mcr阶段，前5秒使用1秒间隔，之后使用5秒间隔
        const gettingMcrDuration = currentTime - taskStartTime
        queryInterval = gettingMcrDuration < 5000 ? 1000 : 5000
      } else if (taskStatus.stage === 'uninstalling_mcr' || taskStatus.stage === 'installing_mcr') {
        // 对于卸载和安装阶段，使用10秒间隔
        queryInterval = 10000
      } else if (taskStatus.stage === 'reboot') {
        // 重启阶段，使用20秒间隔
        queryInterval = 20000
      }
      // 其他阶段使用默认的1秒间隔
      
      // 清除之前的定时器
      if (taskStatusTimers.value[device.id!]) {
        clearTimeout(taskStatusTimers.value[device.id!])
      }
      
      // 设置新的定时器
      taskStatusTimers.value[device.id!] = setTimeout(() => {
        queryTaskStatus(device)
      }, queryInterval)
    } else {
      // 状态不是running，清除定时器
      if (taskStatusTimers.value[device.id!]) {
        clearTimeout(taskStatusTimers.value[device.id!])
        delete taskStatusTimers.value[device.id!]
      }
    }
  } catch (error) {
    console.error(`查询任务状态失败: ${device.task_id}`, error)
    
    // 查询失败时，根据当前阶段设置重试间隔
    let retryInterval = 1000 // 默认1秒
    
    const currentStatus = taskStatusMap.value[device.task_id]
    if (currentStatus) {
      if (currentStatus.stage === 'getting_mcr') {
        const taskStartTime = new Date(currentStatus.timestamp).getTime()
        const currentTime = new Date().getTime()
        const gettingMcrDuration = currentTime - taskStartTime
        retryInterval = gettingMcrDuration < 5000 ? 1000 : 5000
      } else if (currentStatus.stage === 'uninstalling_mcr' || currentStatus.stage === 'installing_mcr') {
        retryInterval = 10000
      } else if (currentStatus.stage === 'reboot') {
        retryInterval = 20000
      }
      // 其他阶段使用默认的1秒间隔
    }
    
    // 查询失败也清除之前的定时器
    if (taskStatusTimers.value[device.id!]) {
      clearTimeout(taskStatusTimers.value[device.id!])
    }
    
    // 设置重试
    taskStatusTimers.value[device.id!] = setTimeout(() => {
      queryTaskStatus(device)
    }, retryInterval)
  }
}

// 添加监听，当 currentPath 变化时更新输入框
watch(currentPath, (newPath) => {
  currentPathInput.value = newPath
}, { immediate: true })

// 方法：处理路径输入框回车
const handlePathInputEnter = async () => {
  const newPath = currentPathInput.value.trim()
  
  // 如果路径没有变化，不做任何操作
  if (newPath === currentPath.value) {
    return
  }
  
  try {
    // 检查输入的是否是MCR文件路径
    const fileName = newPath.split('/').pop() || ''
    if (isMcrFile(fileName)) {
      // 如果是MCR文件路径，加载其父目录并选中该文件
      const parentPath = newPath.substring(0, newPath.lastIndexOf('/')) || '/'
      
      // 先检查父目录是否存在
      await loadDirectory(parentPath)
      
      // 检查该文件是否存在于当前目录中
      const fileExists = fileList.value.some(item => 
        item.type === 'file' && item.name === fileName
      )
      
      if (fileExists) {
        currentPath.value = parentPath
        fileFilterText.value = '' // 清空筛选
        selectedMcrFile.value = newPath // 选中该MCR文件
        
        // 滚动到选中的文件（可选）
        nextTick(() => {
          const selectedElement = document.querySelector('.file-item-selected')
          if (selectedElement) {
            selectedElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        })
      } else {
        throw new Error('MCR文件不存在')
      }
    } else {
      // 如果是目录路径，正常加载
      await loadDirectory(newPath)
      currentPath.value = newPath
      fileFilterText.value = '' // 清空筛选
      selectedMcrFile.value = '' // 清理已选择的MCR包
    }
  } catch (error: any) {
    // 如果加载失败，恢复原来的路径
    currentPathInput.value = currentPath.value
    ElMessage.error(error.message || '路径不存在或无法访问')
  }
}

// 方法：处理输入框失去焦点
const handlePathInputBlur = () => {
  // 失去焦点时恢复当前路径
  currentPathInput.value = currentPath.value
}

// 计算属性：筛选后的文件列表
const filteredFileList = computed(() => {
  if (!fileFilterText.value) {
    return fileList.value
  }
  
  const keyword = fileFilterText.value.toLowerCase()
  return fileList.value.filter(item => 
    item.name.toLowerCase().includes(keyword)
  )
})

// 添加获取完整路径的方法（因为item没有path属性）
const getFullPath = (fileName: string) => {
  return currentPath.value === '/' ? `/${fileName}` : `${currentPath.value}/${fileName}`
}


// 计算属性：路径面包屑
const currentPathParts = computed(() => {
  const parts = currentPath.value.split('/').filter(part => part !== '')
  return ['', ...parts] // 第一个固定为 auto
})

// 方法：检查是否为MCR文件
const isMcrFile = (fileName: string) => {
  return fileName.startsWith('mcr_') && fileName.endsWith('.tar.gz')
}

// 方法：获取文件名（从完整路径中提取）
const getFileName = (filePath: string) => {
  return filePath.split('/').pop() || filePath
}

// 方法：处理更新MCR包对话框
const handleUpdateMcrDialog = async (device: ServerDetailResponse) => {
  currentDevice.value = device
  currentPath.value = '/auto/asic-dump/meta_release'
  selectedMcrFile.value = ''
  updateMcrDialogVisible.value = true
  
  // 加载初始目录
  await loadDirectory(currentPath.value)
}

// 方法：加载目录
const loadDirectory = async (path: string) => {
  // 检查缓存
  if (directoryCache.value[path]) {
    fileList.value = directoryCache.value[path]
    return
  }

  try {
    mcrLoading.value = true
    const response = await remotefsApi.listRemoteDir(path)
    
    // 如果不是根目录，添加返回上一级选项
    if (path !== '/auto') {
      response.unshift({
        name: '..',
        type: 'directory',
        // 可以添加其他需要的属性
      })
    }
    
    fileList.value = response
    
    // 存入缓存
    directoryCache.value[path] = response
    
    fileList.value.sort((a, b) => {
      // .. 始终在最前面
      if (a.name === '..') return -1
      if (b.name === '..') return 1
      
      if (a.type !== b.type) {
        return a.type === 'directory' ? -1 : 1
      }
      return a.name.localeCompare(b.name)
    })
  } catch (error: any) {
    ElMessage.error(`加载目录失败: ${error.response?.data?.detail || '网络错误'}`)
    fileList.value = []
  } finally {
    mcrLoading.value = false
  }
}

watch(updateMcrDialogVisible, (visible) => {
  if (!visible) {
    fileFilterText.value = ''
  }
})

// 方法：处理文件/目录点击
const handleFileItemClick = async (item: any) => {
  if (item.name === '..') {
    // 返回上一级时清理已选择的MCR包
    selectedMcrFile.value = ''
    const pathParts = currentPath.value.split('/').filter(part => part !== '')
    if (pathParts.length > 1) {
      pathParts.pop()
      const parentPath = '/' + pathParts.join('/')
      currentPath.value = parentPath
      fileFilterText.value = '' // 清空筛选
      await loadDirectory(parentPath)
    }
    return
  }
  
  if (item.type === 'directory') {
    // 进入子目录时清理已选择的MCR包
    selectedMcrFile.value = ''
    const newPath = getFullPath(item.name)
    currentPath.value = newPath
    fileFilterText.value = '' // 清空筛选
    await loadDirectory(newPath)
  } else if (item.type === 'file' && isMcrFile(item.name)) {
    // 选择MCR文件
    selectedMcrFile.value = getFullPath(item.name)
  } else {
    // 点击非MCR文件时清理已选择的MCR包
    selectedMcrFile.value = ''
  }
}

// 方法：重置MCR包
const handleResetMcr = async () => {
  if (!currentDevice.value || !selectedMcrFile.value) return

  try {
    upgradeMcrLoading.value = true
    
    await ElMessageBox.confirm(
      `确定要使用 MCR 包 "${getFileName(selectedMcrFile.value)}" 更新服务器 "${currentDevice.value.bmc.hostname}" 吗？\n更新选项: ${getUpdateOptionText(updateOption.value)}`,
      '确认更新MCR包',
      {
        type: 'warning',
        confirmButtonText: '确定更新',
        cancelButtonText: '取消'
      }
    )

    // 调用重置MCR接口
    const response = await deviceApi.upgradeMcr(currentDevice.value.id!, selectedMcrFile.value, updateOption.value)
    
    // 更新当前设备的task_id
    const deviceIndex = devices.value.findIndex(d => d.id === currentDevice.value!.id)
    if (deviceIndex > -1) {
      devices.value[deviceIndex].task_id = response.task_id
      // 设置初始状态
      taskStatusMap.value[response.task_id] = {
        id: response.task_id,
        server_id: currentDevice.value.id!,
        status: 'pending',
        stage: 'waiting',
        detail: '任务已创建，等待执行',
        timestamp: new Date().toISOString()
      }
      // 启动状态查询
      setTimeout(() => {
        queryTaskStatus(devices.value[deviceIndex])
      }, 1000) // 1秒后开始查询
    }
    
    ElMessage.success('MCR包更新任务已开始')
    updateMcrDialogVisible.value = false
    
    // 重置状态
    selectedMcrFile.value = ''
    currentPath.value = '/auto'
    updateOption.value = 'all'
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error(error.response?.data?.detail || '更新MCR包失败')
  } finally {
    upgradeMcrLoading.value = false
  }
}

// 组件卸载时清除所有定时器
onUnmounted(() => {
  Object.values(taskStatusTimers.value).forEach(timer => {
    clearTimeout(timer)
  })
  taskStatusTimers.value = {}
  taskStatusMap.value = {}
})

// 添加更新选项文本显示
const getUpdateOptionText = (option: string) => {
  const optionsMap = {
    'all': '全部更新',
    'fw': '只更新固件',
    'no-fw': '不更新固件'
  }
  return optionsMap[option as keyof typeof optionsMap] || option
}

// 检查当前用户是否已关注某台服务器
const isFollowing = (device: ServerDetailResponse) => {
  const recipients = device.recipients || []
  return recipients.includes(currentUser.value)
}

// 关注/取消关注服务器
const handleFollow = async (device: ServerDetailResponse) => {
  try {
    followLoading.value[device.id!] = true
    
    await deviceApi.focusServer(device.id!, !isFollowing(device))
    
    if (!isFollowing(device)) {
      // 关注成功
      ElMessage.success(`关注成功，将会接收该服务器的占用释放提醒邮件`)
    } else {
      // 取消关注成功
      ElMessage.success('取消关注, 不再接收该服务器的占用释放提醒邮件')
    }
    
    // 重新加载数据以更新关注状态
    await loadData()
    
  } catch (error: any) {
    const action = isFollowing(device) ? '取消关注' : '关注'
    ElMessage.error(`${action}失败: ${error.response?.data?.detail || '请求失败'}`)
  } finally {
    followLoading.value[device.id!] = false
  }
}

class NicColorManager {
  private colorMap: Map<string, string> = new Map()
  private availableColors: string[] = [
    '#eb2f96', // 品红色
    '#1890ff', // 亮蓝色
    '#fa8c16', // 橙色
    '#52c41a', // 鲜绿色
    '#722ed1', // 紫色
    '#f56c6c', // 红色
    '#a0d911', // 黄绿色
    '#2f54eb', // 深蓝色
    '#fa541c', // 红橙色
    '#36cfc9', // 青色
    '#389e0d', // 深绿色
    '#e6a23c', // 黄橙色
    '#096dd9', // 宝蓝色
    '#faad14', // 金黄色
    '#7b1fa2', // 深紫色
    '#13c2c2', // 青蓝色
    '#d46b08', // 棕橙色
    '#909399'  // 灰色
  ]
  private usedColors: Set<string> = new Set()

  // 为网卡类型分配颜色
  assignColor(nicType: string): string {
    // 如果已经为该类型分配过颜色，直接返回
    if (this.colorMap.has(nicType)) {
      return this.colorMap.get(nicType)!
    }

    // 寻找可用的颜色
    let assignedColor: string | null = null
    
    // 首先尝试从未使用的颜色中选择
    for (const color of this.availableColors) {
      if (!this.usedColors.has(color)) {
        assignedColor = color
        this.usedColors.add(color)
        break
      }
    }

    // 如果所有颜色都被使用了，使用哈希算法分配（确保一致性）
    if (!assignedColor) {
      assignedColor = this.getColorByHash(nicType)
    }

    // 保存映射关系
    this.colorMap.set(nicType, assignedColor)
    return assignedColor
  }

  // 通过哈希算法为类型分配颜色（确保同一类型总是得到相同颜色）
  private getColorByHash(nicType: string): string {
    let hash = 0
    for (let i = 0; i < nicType.length; i++) {
      hash = nicType.charCodeAt(i) + ((hash << 5) - hash)
    }
    
    // 使用哈希值在可用颜色中选择
    const index = Math.abs(hash) % this.availableColors.length
    return this.availableColors[index]
  }

  // 获取指定类型的颜色
  getColor(nicType: string): string {
    return this.assignColor(nicType)
  }

  // 重置颜色管理器（可选）
  reset() {
    this.colorMap.clear()
    this.usedColors.clear()
  }

  // 获取所有已分配的颜色映射
  getColorMap(): Map<string, string> {
    return new Map(this.colorMap)
  }
}

// 创建单例实例
const nicColorManager = new NicColorManager()

// 计算电源操作对话框标题
const powerDialogTitle = computed(() => {
  const typeText = powerType.value === 'cycle' ? '冷重启' : '热重启'
  if (isBatchPowerOperation.value) {
    return `批量${typeText}`
  }
  return `${typeText}服务器`
})

// 计算批量操作对话框标题
const batchDialogTitle = computed(() => {
  const titles: Record<string, string> = {
    'batchRelease': '批量释放服务器',
    'batchPowerCycle': '批量冷重启',
    'batchPowerReset': '批量热重启'
  }
  return titles[batchOperation.value] || '批量操作'
})

// 获取批量操作确认信息
const getBatchConfirmMessage = () => {
  const messages: Record<string, string> = {
    'batchRelease': `确认要释放 ${selectedDevices.value.length} 台服务器吗？`,
    'batchPowerCycle': `确认要对 ${selectedDevices.value.length} 台服务器执行冷重启吗？`,
    'batchPowerReset': `确认要对 ${selectedDevices.value.length} 台服务器执行热重启吗？`,
    'batchDelete': `确认要删除 ${selectedDevices.value.length} 台服务器吗？`
  }
  return messages[batchOperation.value] || ''
}

// 获取批量操作警告类型
const getBatchAlertType = () => {
  const types: Record<string, any> = {
    'batchRelease': 'warning',
    'batchPowerCycle': 'warning',
    'batchPowerReset': 'warning',
    'batchDelete': 'error'
  }
  return types[batchOperation.value] || 'info'
}

// 获取批量操作确认按钮类型
const getBatchConfirmButtonType = () => {
  const types: Record<string, any> = {
    'batchRelease': 'warning',
    'batchPowerCycle': 'warning',
    'batchPowerReset': 'warning',
    'batchDelete': 'danger'
  }
  return types[batchOperation.value] || 'primary'
}

// 获取批量操作确认按钮文本
const getBatchConfirmButtonText = () => {
  const texts: Record<string, string> = {
    'batchRelease': '确认释放',
    'batchPowerCycle': '确认重启',
    'batchPowerReset': '确认重启',
    'batchDelete': '确认删除'
  }
  return texts[batchOperation.value] || '确认'
}

// 处理选择变化
const handleSelectionChange = (selection: ServerDetailResponse[]) => {
  selectedDevices.value = selection
}

// 清空选择
const clearSelection = () => {
  selectedDevices.value = []
}

// 处理批量操作命令
const handleBatchCommand = (command: string) => {
  if (command === 'batchRelease' && !canBatchRelease.value) {
    // 如果不满足批量释放条件，显示提示但不执行操作
    const invalidCount = selectedDevices.value.filter(device => 
      !isDeviceOccupied(device) || !isCurrentUserOccupier(device)
    ).length
    ElMessage.warning(`无法执行批量释放：勾选了 ${invalidCount} 台非当前用户所占用的服务器`)
    return
  }
  
  if (command === 'batchPowerCycle' || command === 'batchPowerReset') {
    // 电源操作使用单独的对话框
    const operation = command === 'batchPowerCycle' ? 'cycle' : 'reset'
    handleBatchPowerOperation(operation)
  } else {
    // 其他批量操作使用原来的对话框
    batchOperation.value = command
    batchDialogVisible.value = true
  }
}

// 处理批量操作确认
const handleBatchConfirm = async () => {
  if (selectedDevices.value.length === 0) return

  try {
    batchLoading.value = true

    // 执行批量操作（电源操作已单独处理）
    switch (batchOperation.value) {
      case 'batchRelease':
        await handleBatchRelease()
        break
      case 'batchDelete':
        await handleBatchDelete()
        break
    }

    batchDialogVisible.value = false
    clearSelection()
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '批量操作失败')
  } finally {
    batchLoading.value = false
  }
}

const handleBatchDelete = async () => {
  const promises = selectedDevices.value.map(device => 
    deviceApi.delete(device.id!)
  )

  await Promise.all(promises)
  ElMessage.success(`成功删除 ${selectedDevices.value.length} 台服务器`)
  loadData()
}

// 批量释放
const handleBatchRelease = async () => {
  // 过滤出当前用户占用的设备
  const releasableDevices = selectedDevices.value.filter(device => 
    isDeviceOccupied(device) && isCurrentUserOccupier(device)
  )
  
  if (releasableDevices.length === 0) {
    ElMessage.warning('没有可释放的服务器')
    return
  }
  
  const promises = releasableDevices.map(device => 
    deviceApi.update(device.id!, {
      auto: false,
      time: 0,
      device: {
        ip: device.device.ip,
        username: device.device.username,
        password: ''
      },
      bmc: {
        hostname: device.bmc.hostname,
        ip: device.bmc.ip
      },
      tags: device.tags || [],
      notes: device.notes || ''
    })
  )

  await Promise.all(promises)
  
  // 显示实际释放的数量
  const totalSelected = selectedDevices.value.length
  const actualReleased = releasableDevices.length
  const skipped = totalSelected - actualReleased
  
  let message = `成功释放 ${actualReleased} 台服务器`
  if (skipped > 0) {
    message += `（自动跳过 ${skipped} 台非当前用户占用的服务器）`
  }
  
  ElMessage.success(message)
  loadData()
}

// 处理批量电源操作
const handleBatchPowerOperation = (operation: 'cycle' | 'reset') => {
  powerType.value = operation
  isBatchPowerOperation.value = true
  powerDialogVisible.value = true
}

// 确认电源操作
const handlePowerConfirm = async () => {
  try {
    powerLoading.value = true

    if (isBatchPowerOperation.value) {
      // 批量电源操作
      const promises = selectedDevices.value.map(device => 
        powerType.value === 'cycle' 
          ? deviceApi.powerCycle(device.id!)
          : deviceApi.powerReset(device.id!)
      )

      await Promise.all(promises)
      const operationText = powerType.value === 'cycle' ? '冷重启' : '热重启'
      ElMessage.success(`成功对 ${selectedDevices.value.length} 台服务器执行${operationText}`)
    } else {
      // 单个电源操作
      if (currentDevice.value) {
        if (powerType.value === 'cycle') {
          await deviceApi.powerCycle(currentDevice.value.id!)
        } else {
          await deviceApi.powerReset(currentDevice.value.id!)
        }
        const operationText = powerType.value === 'cycle' ? '冷重启' : '热重启'
        ElMessage.success(`${operationText}命令已发送`)
      }
    }

    powerDialogVisible.value = false
    if (isBatchPowerOperation.value) {
      clearSelection()
    }
    
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '重启操作失败')
  } finally {
    powerLoading.value = false
  }
}

// 处理单个设备的电源操作
const handlePowerOperation = async (device: ServerDetailResponse, operation: 'cycle' | 'reset') => {
  currentDevice.value = device
  powerType.value = operation
  isBatchPowerOperation.value = false
  powerDialogVisible.value = true
}

const canBatchRelease = computed(() => {
  if (selectedDevices.value.length === 0) return false
  
  // 检查所有选中的设备是否都是当前用户占用的
  return selectedDevices.value.every(device => 
    isDeviceOccupied(device) && isCurrentUserOccupier(device)
  )
})

// 获取批量释放操作的提示信息
const getBatchReleaseTooltip = () => {
  const invalidDevices = selectedDevices.value.filter(device => 
    !isDeviceOccupied(device) || !isCurrentUserOccupier(device)
  )
  
  if (invalidDevices.length > 0) {
    return `勾选了 ${invalidDevices.length} 台非当前用户所占用的服务器`
  }
  
  return '只能释放当前用户占用的服务器'
}

// 计算启动项列表
const bootEntriesList = computed(() => {
  const bootEntries = bootEntriesData.value
  if (!bootEntries || !bootEntries.entries) return []

  const { entries, current, next, default: defaultOs } = bootEntries
  const result = []

  for (const [key, value] of Object.entries(entries)) {
    result.push({
      key,
      value,
      isCurrent: key === current,
      isNext: key === next,
      isDefault: key === defaultOs
    })
  }

  return result
})

// 加载启动项信息
const loadBootEntries = async (deviceId: string) => {
  try {
    bootEntriesLoading.value = true
    const data = await deviceApi.getBootEntries(deviceId)
    bootEntriesData.value = data
    
    // 默认选中当前启动项
    if (data.current) {
      selectedBootEntry.value = data.current
    }
  } catch (error) {
    console.error('加载启动项信息失败:', error)
    ElMessage.error('加载启动项信息失败')
  } finally {
    bootEntriesLoading.value = false
  }
}

// 处理启动项对话框
const handleBootEntryDialog = async (device: ServerDetailResponse) => {
  currentDevice.value = device
  selectedBootEntry.value = ''
  setAsDefaultBoot.value = false
  bootEntryDialogVisible.value = true
  
  // 加载启动项信息
  await loadBootEntries(device.id!)
}

// 设置启动项
const handleSetBootEntry = async () => {
  if (!currentDevice.value || !selectedBootEntry.value) return

  try {
    bootEntryLoading.value = true
    
    const bootEntryName = bootEntriesData.value?.entries[selectedBootEntry.value]
    
    await ElMessageBox.confirm(
      `确定要设置下次启动项为 "${bootEntryName}" 吗？${
        setAsDefaultBoot.value ? '同时会设置为默认启动项。' : ''
      }`,
      '确认设置启动项',
      {
        type: 'warning',
        confirmButtonText: '确定设置',
        cancelButtonText: '取消'
      }
    )

    // 调用设置启动项接口
    await deviceApi.setBootEntry(currentDevice.value.id!, selectedBootEntry.value, setAsDefaultBoot.value)
    
    ElMessage.success('启动项设置成功')
    bootEntryDialogVisible.value = false
    
    // 重置状态
    selectedBootEntry.value = ''
    setAsDefaultBoot.value = false
    
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') {
      // 用户取消操作
      return
    }
    ElMessage.error(error.response?.data?.detail || '设置启动项失败')
  } finally {
    bootEntryLoading.value = false
  }
}

// 获取标签样式
const getTagStyle = (tagName: string) => {
  const tag = availableTags.value.find(t => t.name === tagName)
  if (!tag || !tag.color) return {}
  
  const hexColor = tag.color.toUpperCase()
  
  // 计算文字颜色（根据背景色亮度决定用黑色还是白色文字）
  const rgb = parseInt(tag.color.replace('#', ''), 16)
  const r = (rgb >> 16) & 0xff
  const g = (rgb >> 8) & 0xff
  const b = (rgb >> 0) & 0xff
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  const textColor = brightness > 128 ? '#000000' : '#ffffff'
  
  return {
    backgroundColor: hexColor,
    borderColor: hexColor,
    color: textColor
  }
}

// 获取网卡信息统计
const getNicSummary = (device: ServerDetailResponse) => {
  if (!device.nics || device.nics.length === 0) return []
  
  const typeCount: Record<string, number> = {}
  
  device.nics.forEach(nic => {
    if (nic.type) {
      // 通过第一个-切割，取左边的部分
      let displayType = nic.type.split('-')[0].trim()
      
      // 预先为这个类型分配颜色（确保颜色一致性）
      nicColorManager.getColor(displayType)
      
      typeCount[displayType] = (typeCount[displayType] || 0) + 1
    }
  })
  
  return Object.entries(typeCount)
    .map(([type, count]) => ({
      type,
      displayType: type,
      count
    }))
    .sort((a, b) => {
      // 首先按类型名称字母顺序排序
      if (a.type !== b.type) {
        return a.type.localeCompare(b.type)
      }
      // 如果类型相同，按数量降序排列
      return b.count - a.count
    })
}

// 获取网卡类型颜色
const getNicTypeColor = (nicType: string) => {
  return nicColorManager.getColor(nicType)
}

const getNicItemStyle = (nicType: string) => {
  const color = getNicTypeColor(nicType)
  
  // 计算文字颜色（根据背景色亮度决定用黑色还是白色文字）
  const hex = color.replace('#', '')
  const r = parseInt(hex.substr(0, 2), 16)
  const g = parseInt(hex.substr(2, 2), 16)
  const b = parseInt(hex.substr(4, 2), 16)
  const brightness = (r * 299 + g * 587 + b * 114) / 1000
  const textColor = brightness > 128 ? '#000000' : '#ffffff'
  
  return {
    backgroundColor: `${color}15`, // 添加透明度
    borderColor: color,
    color: textColor
  }
}

const getTagNames = (): string[] => {
  return availableTags.value.map(tag => tag.name)
}

// 创建新标签
const createTag = async (tagName: string) => {
  try {
    await tagApi.createTag({ name: tagName })
    // 创建成功后重新加载标签列表
    await loadTags()
    ElMessage.success(`标签 "${tagName}" 创建成功`)
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || `创建标签 "${tagName}" 失败`)
    throw error // 重新抛出错误，让调用者处理
  }
}

// 处理标签对话框变化
const handleTagDialogChange = async (selectedTags: string[]) => {
  // 检查是否有新创建的标签（不在 availableTags 中）
  const tagNames = getTagNames()
  const newTags = selectedTags.filter(tag => !tagNames.includes(tag))
  
  for (const newTag of newTags) {
    if (newTag.trim()) {
      try {
        await createTag(newTag.trim())
      } catch (error) {
        // 如果创建失败，从当前选中中移除该标签
        const index = selectedTags.indexOf(newTag)
        if (index > -1) {
          selectedTags.splice(index, 1)
        }
      }
    }
  }
}

// 处理标签对话框输入框失去焦点
const handleTagDialogBlur = (event: FocusEvent) => {
  const input = event.target as HTMLInputElement
  const value = input.value?.trim()
  
  if (value && !selectedTags.value.includes(value) && !getTagNames().includes(value)) {
    // 如果有输入值且不是已有标签，创建新标签
    createTag(value).then(() => {
      // 创建成功后添加到当前选中
      if (!selectedTags.value.includes(value)) {
        selectedTags.value.push(value)
      }
      input.value = '' // 清空输入框
    }).catch(() => {
      // 创建失败，不清空输入框，让用户重新输入
    })
  }
}

// 时间快捷选项 - 最多3天
const timeShortcuts = [
  {
    text: '1小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3600 * 1000)
      return date
    }
  },
  {
    text: '2小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 2 * 3600 * 1000)
      return date
    }
  },
  {
    text: '4小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 4 * 3600 * 1000)
      return date
    }
  },
  {
    text: '8小时',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 8 * 3600 * 1000)
      return date
    }
  },
  {
    text: '1天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 24 * 3600 * 1000)
      return date
    }
  },
  {
    text: '2天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 2 * 24 * 3600 * 1000)
      return date
    }
  },
  {
    text: '3天',
    value: () => {
      const date = new Date()
      date.setTime(date.getTime() + 3 * 24 * 3600 * 1000)
      return date
    }
  }
]

// 根据剩余秒数计算截止时间
const getEndTimeFromSeconds = (seconds: number): Date => {
  const now = new Date()
  now.setTime(now.getTime() + seconds * 1000)
  return now
}

// 根据截止时间计算剩余秒数
const getSecondsFromEndTime = (endTime: Date): number => {
  const now = new Date()
  return Math.floor((endTime.getTime() - now.getTime()) / 1000)
}

// 检查设备是否被占用（考虑时间过期）
const isDeviceOccupied = (device: ServerDetailResponse) => {
  // 检查user和time是否有效
  const hasValidUser = device.user && device.user.trim() !== ''
  const hasValidTime = device.time !== undefined && device.time !== null && device.time > 0
  
  // 如果有有效的用户和时间，再检查时间是否过期
  if (hasValidUser && hasValidTime) {
    return device.time > 0 // 剩余时间大于0表示未过期
  }
  
  return false
}

// 根据剩余秒数显示截止时间 - 统一使用 YYYY/MM/DD HH:mm:ss 格式
const getEndTimeDisplay = (device: ServerDetailResponse) => {
  if (!device.time || device.time <= 0) return '-'
  
  const endTime = getEndTimeFromSeconds(device.time)
  return formatDateTime(endTime)
}

// 统一的日期时间格式化函数
const formatDateTime = (date: Date): string => {
  const year = date.getFullYear()
  const month = (date.getMonth() + 1).toString().padStart(2, '0')
  const day = date.getDate().toString().padStart(2, '0')
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  const seconds = date.getSeconds().toString().padStart(2, '0')
  
  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`
}

// 检查当前用户是否是占用人
const isCurrentUserOccupier = (device: ServerDetailResponse) => {
  return device.user === currentUser.value
}

// 获取占用按钮文本
const getOccupyButtonText = (device: ServerDetailResponse) => {
  if (isDeviceOccupied(device) && isCurrentUserOccupier(device)) {
    return '修改占用'
  }
  return '占用服务器'
}

// 检查是否为修改模式
const isModifyMode = computed(() => {
  return currentDevice.value && 
         isDeviceOccupied(currentDevice.value) && 
         isCurrentUserOccupier(currentDevice.value)
})

// 获取对话框标题
const occupyDialogTitle = computed(() => {
  return isModifyMode.value ? '修改占用' : '占用服务器'
})

// 禁用超过3天的日期
// 禁用超过3天的日期和时间
const disabledDate = (time: Date) => {
  const now = new Date()
  const threeDaysLater = new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000)
  
  // 只允许选择今天、明天、后天、大后天（4天内）
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const maxDate = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000) // 大后天
  
  // 禁用今天之前和3天后的日期
  return time.getTime() < today.getTime() || time.getTime() > maxDate.getTime()
}

const disabledHours = () => {
  const now = new Date()
  const selectedDate = occupyForm.endTime
  
  if (!selectedDate) return []
  
  const disabledHours: number[] = []
  const selectedDay = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  
  // 如果选择的是今天，禁用当前时间之前的小时
  if (selectedDay.getTime() === today.getTime()) {
    for (let i = 0; i < now.getHours(); i++) {
      disabledHours.push(i)
    }
  }
  
  // 如果选择的是3天后，禁用当前时间之后的小时
  const threeDaysLater = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000)
  if (selectedDay.getTime() === threeDaysLater.getTime()) {
    for (let i = now.getHours() + 1; i < 24; i++) {
      disabledHours.push(i)
    }
  }
  
  return disabledHours
}

// 禁用分钟
const disabledMinutes = (selectedHour: number) => {
  const now = new Date()
  const selectedDate = occupyForm.endTime
  
  if (!selectedDate) return []
  
  const disabledMinutes: number[] = []
  const selectedDay = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  
  // 如果选择的是今天且选中的小时等于当前小时，禁用当前时间之前的分钟
  if (selectedDay.getTime() === today.getTime() && selectedHour === now.getHours()) {
    for (let i = 0; i < now.getMinutes(); i++) {
      disabledMinutes.push(i)
    }
  }
  
  // 如果选择的是3天后且选中的小时等于当前小时，禁用当前时间之后的分钟
  const threeDaysLater = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000)
  if (selectedDay.getTime() === threeDaysLater.getTime() && selectedHour === now.getHours()) {
    for (let i = now.getMinutes() + 1; i < 60; i++) {
      disabledMinutes.push(i)
    }
  }
  
  return disabledMinutes
}

// 禁用秒数
const disabledSeconds = (selectedHour: number, selectedMinute: number) => {
  const now = new Date()
  const selectedDate = occupyForm.endTime
  
  if (!selectedDate) return []
  
  const disabledSeconds: number[] = []
  const selectedDay = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  
  // 如果选择的是今天且选中的小时和分钟都等于当前时间，禁用当前时间之前的秒数
  if (selectedDay.getTime() === today.getTime() && 
      selectedHour === now.getHours() && 
      selectedMinute === now.getMinutes()) {
    for (let i = 0; i < now.getSeconds(); i++) {
      disabledSeconds.push(i)
    }
  }
  
  // 如果选择的是3天后且选中的小时和分钟都等于当前时间，禁用当前时间之后的秒数
  const threeDaysLater = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000)
  if (selectedDay.getTime() === threeDaysLater.getTime() && 
      selectedHour === now.getHours() && 
      selectedMinute === now.getMinutes()) {
    for (let i = now.getSeconds() + 1; i < 60; i++) {
      disabledSeconds.push(i)
    }
  }
  
  return disabledSeconds
}

// 计算占用时长（显示用）
const calculateDuration = () => {
  if (!occupyForm.endTime) return '-'
  
  const now = new Date()
  const endTime = new Date(occupyForm.endTime)
  const durationMs = endTime.getTime() - now.getTime()
  
  if (durationMs <= 0) return '结束时间必须晚于当前时间'
  
  const seconds = Math.floor(durationMs / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)
  
  if (days > 0) {
    return `${days}天${hours % 24}小时${minutes % 60}分钟`
  } else if (hours > 0) {
    return `${hours}小时${minutes % 60}分钟`
  } else {
    return `${minutes}分钟`
  }
}

// 获取持续秒数
const getDurationSeconds = () => {
  if (!occupyForm.endTime) return 0
  
  const now = new Date()
  const endTime = new Date(occupyForm.endTime)
  const durationMs = endTime.getTime() - now.getTime()
  
  return Math.floor(durationMs / 1000)
}

// 获取时长类型
const getDurationType = () => {
  if (!occupyForm.endTime) return 'info'
  
  const seconds = getDurationSeconds()
  const hours = seconds / 3600
  
  if (hours <= 1) return 'danger'
  if (hours <= 4) return 'warning'
  return 'success'
}

// 获取时长标签大小
const getDurationSize = () => {
  if (!occupyForm.endTime) return ''
  
  const durationText = calculateDuration()
  if (durationText.length > 10) return 'duration-large'
  return ''
}

// 获取结束时间显示（表单用）- 统一使用 YYYY/MM/DD HH:mm:ss 格式
const getEndTimeDisplayFromForm = () => {
  if (!occupyForm.endTime) return ''
  
  const endTime = new Date(occupyForm.endTime)
  return formatDateTime(endTime)
}

// 加载标签列表
const loadTags = async () => {
  try {
    tagsLoading.value = true
    const response = await tagApi.getTags()
    availableTags.value = response.tags || []
  } catch (error) {
    console.error('加载标签失败:', error)
  } finally {
    tagsLoading.value = false
  }
}

// 检查标签是否已选中
const isTagSelected = (tagName: string) => {
  return selectedTags.value.includes(tagName)
}

// 切换标签选中状态
const toggleTag = (tagName: string) => {
  const index = selectedTags.value.indexOf(tagName)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    selectedTags.value.push(tagName)
  }
}

// 移除标签
const handleRemoveTag = async (event: Event, tagName: string, device: ServerDetailResponse) => {
  event.stopPropagation() // 阻止事件冒泡
  
  try {
    await ElMessageBox.confirm(`确定要从服务器 "${device.bmc.hostname}" 中移除标签 "${tagName}" 吗？`, '提示', {
      type: 'warning'
    })

    const updatedTags = device.tags?.filter(tag => tag !== tagName) || []
    
    await deviceApi.update(device.id!, {
      tags: updatedTags,
      auto: false,
      device: {
        ip: device.device.ip,
        username: device.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: device.bmc.hostname,
        ip: device.bmc.ip
      },
      notes: device.notes || '',
      os_types: device.os_types || []
    })
    
    // 更新本地数据
    const deviceIndex = devices.value.findIndex(d => d.id === device.id)
    if (deviceIndex > -1) {
      devices.value[deviceIndex].tags = updatedTags
    }
    
    ElMessage.success('标签移除成功')
  } catch (error) {
    // 用户取消操作
  }
}

// 显示添加标签对话框
const showAddTagDialog = (device: ServerDetailResponse) => {
  editingDevice.value = device
  selectedTags.value = [...(device.tags || [])]
  showAddTagDialogVisible.value = true
}

// 添加标签
const handleAddTags = async () => {
  if (!editingDevice.value) return

  try {
    addingTags.value = true
    
    await deviceApi.update(editingDevice.value.id!, {
      tags: selectedTags.value,
      auto: false,
      device: {
        ip: editingDevice.value.device.ip,
        username: editingDevice.value.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: editingDevice.value.bmc.hostname,
        ip: editingDevice.value.bmc.ip
      },
      notes: editingDevice.value.notes || '',
      os_types: editingDevice.value.os_types || []
    })
    
    // 更新本地数据
    const deviceIndex = devices.value.findIndex(d => d.id === editingDevice.value!.id)
    if (deviceIndex > -1) {
      devices.value[deviceIndex].tags = selectedTags.value
    }
    
    showAddTagDialogVisible.value = false
    ElMessage.success('标签更新成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '更新标签失败')
  } finally {
    addingTags.value = false
  }
}

// 处理标签对话框关闭
const handleTagDialogClose = () => {
  showAddTagDialogVisible.value = false
  editingDevice.value = null
}

// IP地址排序函数
const ipSortMethod = (a: ServerDetailResponse, b: ServerDetailResponse) => {
  const ipToNumber = (ip: string) => {
    const parts = ip.split('.').map(part => parseInt(part, 10));
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3];
  };
  
  const ipA = ipToNumber(a.device.ip);
  const ipB = ipToNumber(b.device.ip);
  
  if (ipA < ipB) return -1;
  if (ipA > ipB) return 1;
  return 0;
};

// 时间排序函数
const timeSortMethod = (a: ServerDetailResponse, b: ServerDetailResponse) => {
  const timeA = a.time || 0;
  const timeB = b.time || 0;
  return timeA - timeB;
};

// 计算属性：过滤设备列表
const filteredDevices = computed(() => {
  let filtered = devices.value
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = devices.value.filter(device => {
      // 搜索服务器名称
      if (device.bmc.hostname.toLowerCase().includes(keyword)) return true
      
      // 搜索服务器管理IP
      if (device.device.ip.toLowerCase().includes(keyword)) return true
      
      // 搜索网卡信息
      const nicSummary = getNicSummary(device)
      if (nicSummary.some(summary => 
        summary.displayType.toLowerCase().includes(keyword) ||
        summary.count.toString().includes(keyword)
      )) return true
      
      // 搜索标签
      if (device.tags && device.tags.some(tag => tag.toLowerCase().includes(keyword))) return true
      
      // 搜索备注
      if (device.notes && device.notes.toLowerCase().includes(keyword)) return true
      
      // 搜索占用人
      if (device.user && device.user.toLowerCase().includes(keyword)) return true
      
      return false
    })
  }
  
  return filtered
})


// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const data = await deviceApi.getAll()
    devices.value = data
    
    // 为有task_id的设备启动状态查询
    data.forEach(device => {
      if (device.task_id) {
        // 启动状态查询
        queryTaskStatus(device)
      }
    })
  } catch (error) {
  } finally {
    loading.value = false
  }
}

// 处理搜索
const handleSearch = () => {
  // 搜索逻辑已经在 computed 属性中处理
}

// 下拉菜单命令处理
const handleCommand = (command: string, device: ServerDetailResponse) => {
  switch (command) {
    case 'detail':
      handleDetail(device)
      break
    case 'edit':
      handleEdit(device)
      break
    case 'bootEntry':
      // 这个命令现在通过 @click 直接处理，不在这里处理
      break
    case 'powerCycle':
      handlePowerOperation(device, 'cycle')
      break
    case 'powerReset':
      handlePowerOperation(device, 'reset')
      break
    case 'updateMcr':
      // 这个命令现在通过 @click 直接处理，不在这里处理
      break
    case 'occupy':
      handleOccupyDialog(device)
      break
    case 'release':
      handleRelease(device)
      break
    case 'delete':
      handleDelete(device)
      break
  }
}

// 查看详情 - 点击服务器名称或详情按钮
const handleDetail = (device: ServerDetailResponse) => {
  router.push(`/devices/detail/${device.id}`)
}

// 编辑
const handleEdit = (device: ServerDetailResponse) => {
  router.push(`/devices/edit/${device.id}`)
}

// 打开占用服务器对话框
const handleOccupyDialog = (device: ServerDetailResponse) => {
  currentDevice.value = device
  
  // 设置默认结束时间
  let defaultEndTime = new Date()
  defaultEndTime.setTime(defaultEndTime.getTime() + 60 * 60 * 1000) // 默认1小时后
  
  // 如果是修改模式，且设备有剩余时间，使用原剩余时间计算新的截止时间
  if (isModifyMode.value && device.time && device.time > 0) {
    defaultEndTime = getEndTimeFromSeconds(device.time)
  }
  
  occupyForm.endTime = defaultEndTime
  occupyDialogVisible.value = true
}

// 占用/修改时间服务器
const handleOccupy = async () => {
  if (!currentDevice.value || !occupyForm.endTime) return
  
  try {
    occupyLoading.value = true
    
    // 计算持续秒数
    const durationSeconds = getDurationSeconds()
    
    // 检查是否超过3天（259200秒）
    const maxDuration = 3 * 24 * 60 * 60 // 3天的秒数
    if (durationSeconds > maxDuration) {
      ElMessage.error('占用时间不能超过3天')
      return
    }
    
    const updateData: ServerUpdateRequest = {
      auto: false,
      time: durationSeconds, // 传持续秒数
      // user字段后端会通过token自动获取当前用户
      device: {
        ip: currentDevice.value.device.ip,
        username: currentDevice.value.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: currentDevice.value.bmc.hostname,
        ip: currentDevice.value.bmc.ip
      },
      tags: currentDevice.value.tags || [],
      notes: currentDevice.value.notes || '',
      os_types: currentDevice.value.os_types || []
    }
    
    await deviceApi.update(currentDevice.value.id!, updateData)
    ElMessage.success(`已成功${isModifyMode.value ? '修改占用' : '占用'}服务器 ${currentDevice.value.bmc.hostname}`)
    occupyDialogVisible.value = false
    loadData() // 重新加载数据
  } catch (error) {
    ElMessage.error(`${isModifyMode.value ? '修改占用' : '占用'}服务器失败`)
  } finally {
    occupyLoading.value = false
  }
}

// 释放占用
const handleRelease = async (device: ServerDetailResponse) => {
  if (!isDeviceOccupied(device)) {
    ElMessage.warning('服务器未被占用，无法释放')
    return
  }
  
  if (!isCurrentUserOccupier(device)) {
    ElMessage.warning('您不是当前占用人，无法释放该服务器')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要释放占用 "${device.bmc.hostname}" 吗？`, 
      '确认结束', 
      {
        type: 'warning',
      }
    )

    const updateData: ServerUpdateRequest = {
      auto: false,
      time: 0, // 设置为0表示释放占用
      // user字段后端会自动处理
      device: {
        ip: device.device.ip,
        username: device.device.username,
        password: '' // 密码不更新
      },
      bmc: {
        hostname: device.bmc.hostname,
        ip: device.bmc.ip
      },
      tags: device.tags || [],
      notes: device.notes || '',
      os_types: device.os_types || []
    }
    
    await deviceApi.update(device.id!, updateData)
    ElMessage.success('服务器已释放')
    loadData() // 重新加载数据
  } catch (error) {
    // 用户取消释放
  }
}

// 删除
const handleDelete = async (device: ServerDetailResponse) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除设备 "${device.bmc.hostname}" 吗？`, 
      '确认删除', 
      {
        type: 'warning',
      }
    )

    await deviceApi.delete(device.id!)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    // 用户取消删除
  }
}

onMounted(() => {
  loadData()
  loadTags()
})
</script>

<style scoped>
/* MCR状态样式 */
.mcr-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mcr-status-tag {
  cursor: help;
}

.mcr-tooltip-content {
  text-align: left;
}

.detail-text {
  margin: 4px 0 0 0;
  font-family: inherit;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.detail-section {
  margin-top: 8px;
}

.mcr-status-tooltip :deep(.el-tooltip__popper) {
  white-space: pre-line;
  max-width: 300px;
}

.loading-spinner {
  animation: spin 1s linear infinite;
  color: #e6a23c;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.current-path {
  margin-bottom: 16px;
  padding: 8px 0;
  width: 100%;
}

.path-input {
  width: 100%;
}

/* 输入框聚焦样式 */
:deep(.path-input .el-input__wrapper) {
  transition: all 0.3s ease;
  font-family: 'Monaco', 'Consolas', monospace;
}

:deep(.path-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

.filter-section {
  margin-bottom: 16px;
  padding: 0 8px;
}

.filter-tags {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.filter-tag {
  cursor: pointer;
  transition: all 0.3s ease;
}

.filter-tag:hover {
  transform: translateY(-1px);
}

/* 文件列表统计信息 */
.file-stats {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
  padding: 0 8px;
}

/* 更新MCR包对话框样式 */
.update-mcr-dialog {
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

.update-mcr-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}


.path-breadcrumb {
  cursor: pointer;
  color: #409eff;
}

.path-breadcrumb:hover {
  color: #337ecc;
  text-decoration: underline;
}

.file-browser {
  background: white;
  border-radius: 8px;
  padding: 0;
}

.file-list {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  max-height: 400px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.file-item:last-child {
  border-bottom: none;
}

.file-item:hover {
  background-color: #f5f7fa;
}

.file-item-selected {
  background-color: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.directory-item:hover {
  background-color: #f0f9ff;
}

.file-icon {
  margin-right: 12px;
  font-size: 20px;
  color: #909399;
}

.directory-item .file-icon {
  color: #409eff;
}

.mcr-file-icon {
  color: #e6a23c !important;
}

.file-info {
  flex: 1;
}

.file-name {
  font-weight: 500;
  color: #1f2937;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.mcr-file-name {
  color: #e6a23c;
  font-weight: 600;
}

.file-type {
  font-size: 12px;
  color: #909399;
}

.file-action {
  color: #c0c4cc;
}

.mcr-tag {
  font-size: 10px;
  padding: 0 4px;
  height: 18px;
  line-height: 18px;
}

.empty-files {
  padding: 40px 0;
}

/* 更新MCR包按钮样式 */
:deep(.update-mcr-item:not(.is-disabled)) {
  color: #7239ea !important;
}

:deep(.update-mcr-item:not(.is-disabled):hover) {
  color: #5f2bc3 !important;
  background-color: #f8f5ff !important;
}

/* 关注心形按钮样式 */
.follow-heart-btn {
  display: inline-flex;
  padding: 0;
  border: none !important;
  background: none !important;
  width: auto;
  height: auto;
  cursor: pointer;
  transition: all 0.3s ease;
}

.follow-heart-btn:deep(.el-icon) {
  font-size: 18px;
  line-height: 1;
}

/* Hover effect */
.follow-heart-btn:hover:deep(.el-icon) {
  transform: scale(1.2);
  color: #409eff; /* 可根据是否已关注调整 */
}

/* 已关注状态 */
.follow-heart-btn.el-button--danger:deep(.el-icon) {
  color: #f56c6c;
}

.follow-heart-btn.el-button--danger:hover:deep(.el-icon) {
  color: #f78989;
}

/* 电源重启对话框样式 */
.power-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog-tip {
  margin-bottom: 8px;
}

.confirm-message {
  text-align: center;
  padding: 8px 0;
}

.confirm-message p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
}

.confirm-message strong {
  color: #409eff;
}

/* 批量操作按钮样式 */
:deep(.batch-release-item.is-disabled) {
  color: #c0c4cc !important;
}

:deep(.batch-release-item.is-disabled .el-icon) {
  color: #c0c4cc !important;
}

:deep(.batch-release-item.is-disabled:hover) {
  background-color: transparent !important;
  color: #c0c4cc !important;
}

/* 批量释放按钮正常状态颜色 - 与单个释放按钮保持一致 */
:deep(.batch-release-item:not(.is-disabled)) {
  color: #67c23a !important;
}

:deep(.batch-release-item:not(.is-disabled):hover) {
  color: #5daf34 !important;
  background-color: #f0f9eb !important;
}

:deep(.batch-power-item) {
  color: #e6a23c !important;
}


/* 批量对话框样式 */
.batch-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.warning-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background-color: #fdf6ec;
  border-radius: 4px;
  color: #e6a23c;
  font-size: 14px;
}

/* 电源操作按钮样式 */
:deep(.power-cycle-item:not(.is-disabled)) {
  color: #e6a23c !important;
}

:deep(.power-cycle-item:not(.is-disabled):hover) {
  color: #cf9236 !important;
  background-color: #fdf6ec !important;
}

:deep(.power-reset-item:not(.is-disabled)) {
  color: #f56c6c !important;
}

:deep(.power-reset-item:not(.is-disabled):hover) {
  color: #dd6161 !important;
  background-color: #fef0f0 !important;
}

/* 服务器名称链接样式 - 添加下划线 */
.underlined-link {
  text-decoration: underline !important;
  text-underline-offset: 3px;
  text-decoration-thickness: 1px;
}

.underlined-link:hover {
  text-decoration-thickness: 2px;
}

/* 操作下拉菜单样式优化 */
:deep(.action-dropdown-menu) {
  min-width: 160px;
}

:deep(.dropdown-item) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  text-align: left !important;
}

:deep(.dropdown-item .el-dropdown-menu__item) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  padding: 8px 12px !important;
}

:deep(.dropdown-item .el-icon) {
  margin-right: 8px !important;
  flex-shrink: 0 !important;
}

:deep(.dropdown-item span) {
  flex: 1 !important;
  text-align: left !important;
}

/* 启动项按钮样式 */
:deep(.boot-entry-item:not(.is-disabled)) {
  color: #7239ea !important;
}

:deep(.boot-entry-item:not(.is-disabled):hover) {
  color: #5f2bc3 !important;
  background-color: #f8f5ff !important;
}

/* 占用相关按钮样式优化 */
:deep(.occupy-item) {
  font-weight: 600 !important;
}

:deep(.occupy-server-item:not(.is-disabled)) {
  color: #409eff !important;
}

:deep(.occupy-server-item:not(.is-disabled):hover) {
  color: #337ecc !important;
  background-color: #f0f7ff !important;
}

:deep(.end-occupy-item:not(.is-disabled)) {
  color: #67c23a !important;
}

:deep(.end-occupy-item:not(.is-disabled):hover) {
  color: #529b2e !important;
  background-color: #f0f9eb !important;
}

:deep(.action-text) {
  font-weight: 600;
  margin-left: 6px;
}

/* 表格列宽优化 */
:deep(.el-table .cell) {
  padding: 0 8px;
}

:deep(.el-table th) {
  padding: 8px 0;
}

:deep(.el-table td) {
  padding: 8px 0;
}

/* 网卡信息样式 */
.nic-summary-compact {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.nic-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  background-color: #f0f7ff;
  border: 1px solid #d4e8ff;
  font-size: 12px;
  line-height: 1.2;
  min-width: 0;
}

.nic-count {
  font-weight: 600;
  color: #409eff;
  min-width: 12px;
  text-align: center;
  flex-shrink: 0;
}

.nic-type {
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* 标签容器样式优化 */
.tags-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.tag-item {
  margin: 0 !important;
  flex-shrink: 0;
  border: none !important;
}

.add-tag-btn {
  margin: 0 !important;
  flex-shrink: 0;
}

/* 对话框样式 */
.occupy-dialog {
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

/* 启动项对话框样式 */
.boot-entry-dialog {
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

.boot-entries-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}




.current-entry {
  font-family: 'Courier New', monospace;
  color: #1890ff;
  font-weight: 500;
}

.boot-selection {
  background: white;
  border-radius: 8px;
  padding: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #f3f4f6;
}

.section-title .el-icon {
  color: #409eff;
}

.boot-entries-list {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
}

.boot-entry-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s ease;
  cursor: pointer;
}

.boot-entry-item:last-child {
  border-bottom: none;
}

.boot-entry-item:hover {
  background-color: #f5f7fa;
}

.boot-entry-item.current-entry {
  background-color: #e6f7ff;
  border-left: 3px solid #1890ff;
}

.boot-entry-item.default-entry {
  background-color: #f6ffed;
}

.boot-entry-item.selected-entry {
  background-color: #f0f7ff;
  border-left: 3px solid #409eff;
}

.boot-entry-content {
  display: flex;
  flex-direction: column;
}

.boot-entry-main {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.boot-radio {
  flex: 1;
  
  :deep(.el-radio__label) {
    font-family: 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.4;
  }
}

.boot-entry-text {
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.4;
}

.boot-entry-tags {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.boot-options {
  padding: 12px 0;
}

.default-boot-checkbox {
  margin-bottom: 4px;
}

.option-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 24px;
}

.no-boot-entries {
  padding: 40px 0;
}

/* 对话框头部 */
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #e2e8f0;
}

.device-info {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 300px;
}

.server-icon {
  font-size: 24px;
  color: #409eff;
}

.info-content .hostname {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.4;
}

.info-content .ip-address {
  font-size: 12px;
  color: #6b7280;
  font-family: 'Monaco', 'Consolas', monospace;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
}

.username {
  font-weight: 500;
  color: #374151;
}

/* 原时间显示 */
.original-time {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fffbf0;
  border: 1px solid #fef3c7;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 14px;
  color: #92400e;
}

.original-time .el-icon {
  color: #d97706;
}

/* 表单区域 */
.form-section {
  background: white;
  border-radius: 8px;
  padding: 0;
}

/* 紧凑表单项 */
.compact-item {
  margin-bottom: 20px;
  
  :deep(.el-form-item__label) {
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;
    color: #374151;
    padding-right: 12px;
  }
}

.form-label {
  font-size: 14px;
}

.required {
  color: #f56c6c;
}

.enhanced-picker {
  :deep(.el-input__wrapper) {
    border-radius: 6px;
    transition: all 0.3s ease;
    
    &:hover {
      border-color: #409eff;
      box-shadow: 0 0 0 1px #409eff;
    }
  }
  
  :deep(.el-input__inner) {
    text-align: center;
    font-weight: 500;
  }
}

/* 时长显示 */
.duration-display {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.duration-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  padding: 8px 12px;
  
  &.duration-large {
    font-size: 15px;
    padding: 10px 16px;
  }
}

.duration-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.end-time {
  color: #6b7280;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 13px;
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.update-options-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.options-label {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

:deep(.update-options-left .el-radio-group) {
  display: flex;
  gap: 20px;
}

:deep(.update-options-left .el-radio) {
  margin-right: 0;
}

.footer-buttons {
  display: flex;
  gap: 12px;
}

.cancel-btn {
  width: 100px;
}

.confirm-btn {
  width: 120px;
  font-weight: 600;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .dialog-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .user-info {
    align-self: flex-end;
  }
  
  .boot-entry-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .boot-entry-tags {
    align-self: flex-start;
  }
}

/* 其他现有样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
}

.hostname-link {
  font-weight: 500;
}

.highlight-ip {
  font-family: 'Monaco', 'Consolas', monospace;
  font-weight: 500;
}

.no-tags {
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
}

.danger-item {
  color: #f56c6c;
}

.danger-item:hover {
  color: #f56c6c;
  background-color: #fef0f0;
}

/* 确保批量删除按钮使用危险色 */
:deep(.danger-item:not(.is-disabled)) {
  color: #f56c6c !important;
}

:deep(.danger-item:not(.is-disabled):hover) {
  color: #dd6161 !important;
  background-color: #fef0f0 !important;
}

.occupy-item:disabled {
  color: #c0c4cc;
  cursor: not-allowed;
}

/* 添加标签对话框样式 */
.tag-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dialog-tip {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.existing-tags {
  margin-top: 8px;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.tag-item {
  cursor: pointer;
  transition: all 0.2s ease;
  border: none !important;
}

.tag-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}
</style>