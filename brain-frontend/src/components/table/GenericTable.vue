<template>
  <div class="generic-table">
    <el-card>
      <!-- 表格头部 -->
      <template #header>
        <div class="table-header">
          <div class="header-left">
            <slot name="header-left">
              <h3 v-if="title">{{ title }}</h3>
            </slot>
          </div>
          
          <div class="header-right">
            <!-- 搜索框 -->
            <el-input
              v-if="showSearch"
              v-model="searchKeyword"
              :placeholder="searchPlaceholder"
              clearable
              :style="searchStyle"
              @input="handleSearch"
              @clear="handleSearchClear"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>

            <!-- 批量操作按钮插槽 -->
            <slot name="batch-actions" :selected="selectedItems" />

            <!-- 自定义操作按钮 -->
            <slot name="actions" />
            
            <!-- 创建按钮（如果配置了创建路由） -->
            <el-button
              v-if="createRoute"
              type="primary"
              @click="handleCreate"
              :loading="loading"
            >
              <el-icon><Plus /></el-icon>
              {{ createButtonText }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 数据表格 -->
      <el-table
        :data="filteredData"
        v-loading="loading"
        :default-sort="defaultSort"
        @sort-change="handleSortChange"
        @selection-change="handleSelectionChange"
        :row-key="rowKey"
        :height="height"
        :max-height="maxHeight"
        :stripe="stripe"
        :border="border"
        :size="size"
        :fit="fit"
        :show-header="showHeader"
        :highlight-current-row="highlightCurrentRow"
        :current-row-key="currentRowKey"
        :cell-class-name="cellClassName"
        :row-class-name="rowClassName"
        :header-row-class-name="headerRowClassName"
        :header-cell-class-name="headerCellClassName"
        :empty-text="emptyText"
      >
        <!-- 多选框 -->
        <el-table-column
          v-if="selectable"
          type="selection"
          :width="selectionWidth"
          :reserve-selection="reserveSelection"
        />

        <!-- 序号列 -->
        <el-table-column
          v-if="showIndex"
          type="index"
          :label="indexLabel"
          :width="indexWidth"
          :align="indexAlign"
        />

        <!-- 动态渲染列 -->
        <template v-for="column in columns" :key="column.prop || column.type">
          <el-table-column
            v-bind="column"
            :prop="column.prop"
            :label="column.label"
            :width="column.width"
            :min-width="column.minWidth"
            :fixed="column.fixed"
            :sortable="column.sortable"
            :sort-by="column.sortBy"
            :sort-orders="column.sortOrders"
            :resizable="column.resizable !== false"
            :show-overflow-tooltip="column.showOverflowTooltip !== false"
            :align="column.align || 'center'"
            :header-align="column.headerAlign || column.align || 'center'"
            :class-name="column.className"
            :label-class-name="column.labelClassName"
          >
            <!-- 自定义列内容 -->
            <template v-if="column.slot" #default="scope">
              <slot :name="`column-${column.prop}`" v-bind="scope" />
            </template>
            
            <!-- 使用渲染函数 -->
            <template v-else-if="column.render" #default="scope">
              <component :is="column.render(scope)" />
            </template>
            
            <!-- 默认显示（支持简单格式化） -->
            <template v-else-if="column.formatter" #default="scope">
              {{ column.formatter(scope.row, scope.column, scope.$index) }}
            </template>
          </el-table-column>
        </template>

        <!-- 操作列 -->
        <el-table-column
          v-if="showActions"
          :label="actionsLabel"
          :width="actionsWidth"
          :fixed="actionsFixed"
          align="center"
        >
          <template #default="scope">
            <slot name="actions-column" v-bind="scope">
              <!-- 默认操作按钮 -->
              <el-button-group>
                <!-- 查看详情 -->
                <el-button
                  v-if="detailRoute"
                  type="primary"
                  link
                  @click="handleDetail(scope.row)"
                >
                  <el-icon><View /></el-icon>
                  详情
                </el-button>
                
                <!-- 编辑 -->
                <el-button
                  v-if="editRoute"
                  type="primary"
                  link
                  @click="handleEdit(scope.row)"
                >
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-button>
                
                <!-- 删除 -->
                <el-button
                  v-if="showDelete"
                  type="danger"
                  link
                  @click="handleDelete(scope.row)"
                  :loading="deletingId === getRowId(scope.row)"
                >
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
                
                <!-- 自定义操作按钮插槽 -->
                <slot name="row-actions" v-bind="scope" />
              </el-button-group>
            </slot>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div v-if="showPagination" class="table-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="pageSizes"
          :layout="paginationLayout"
          :total="total"
          :small="paginationSmall"
          :background="paginationBackground"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>

      <!-- 空状态 -->
      <div v-if="showEmptyState && (!filteredData || filteredData.length === 0)" class="empty-state">
        <slot name="empty">
          <el-empty :description="emptyDescription" />
        </slot>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, View, Edit, Delete } from '@element-plus/icons-vue'

// 列定义接口
export interface TableColumn {
  /** 列属性名 */
  prop?: string
  /** 列显示标签 */
  label: string
  /** 列宽度 */
  width?: string | number
  /** 最小宽度 */
  minWidth?: string | number
  /** 是否固定在左侧或右侧 */
  fixed?: boolean | 'left' | 'right'
  /** 是否可排序 */
  sortable?: boolean | 'custom'
  /** 排序字段（如果与prop不同） */
  sortBy?: string | string[] | ((row: any) => any)
  /** 排序顺序 */
  sortOrders?: Array<'ascending' | 'descending' | null>
  /** 是否可调整宽度 */
  resizable?: boolean
  /** 是否显示溢出提示 */
  showOverflowTooltip?: boolean
  /** 列对齐方式 */
  align?: 'left' | 'center' | 'right'
  /** 表头对齐方式 */
  headerAlign?: 'left' | 'center' | 'right'
  /** 自定义类名 */
  className?: string
  /** 表头类名 */
  labelClassName?: string
  /** 自定义插槽名称 */
  slot?: string
  /** 自定义渲染函数 */
  render?: (scope: any) => any
  /** 格式化函数 */
  formatter?: (row: any, column: any, index: number) => any
  /** 列类型（用于特殊列） */
  type?: string
}

// 组件属性
interface Props {
  /** 表格标题 */
  title?: string
  /** 表格数据 */
  data: any[]
  /** 列配置 */
  columns: TableColumn[]
  /** 是否显示搜索框 */
  showSearch?: boolean
  /** 搜索框占位符 */
  searchPlaceholder?: string
  /** 搜索框样式 */
  searchStyle?: Record<string, any>
  /** 是否可多选 */
  selectable?: boolean
  /** 多选框宽度 */
  selectionWidth?: number | string
  /** 是否保留选中状态（跨页） */
  reserveSelection?: boolean
  /** 是否显示序号列 */
  showIndex?: boolean
  /** 序号列标签 */
  indexLabel?: string
  /** 序号列宽度 */
  indexWidth?: number | string
  /** 序号列对齐方式 */
  indexAlign?: 'left' | 'center' | 'right'
  /** 是否显示操作列 */
  showActions?: boolean
  /** 操作列标签 */
  actionsLabel?: string
  /** 操作列宽度 */
  actionsWidth?: number | string
  /** 操作列是否固定 */
  actionsFixed?: boolean | 'left' | 'right'
  /** 是否显示删除按钮 */
  showDelete?: boolean
  /** 创建按钮路由 */
  createRoute?: string
  /** 创建按钮文本 */
  createButtonText?: string
  /** 详情路由模板（支持 :id 占位符） */
  detailRoute?: string
  /** 编辑路由模板（支持 :id 占位符） */
  editRoute?: string
  /** 删除确认消息模板 */
  deleteConfirmMessage?: string
  /** 删除处理函数 */
  onDelete?: (row: any) => Promise<void>
  /** 是否显示分页 */
  showPagination?: boolean
  /** 当前页码 */
  page?: number
  /** 每页显示数量 */
  pageSize?: number
  /** 总数据量 */
  total?: number
  /** 每页显示数量选项 */
  pageSizes?: number[]
  /** 分页布局 */
  paginationLayout?: string
  /** 小型分页 */
  paginationSmall?: boolean
  /** 分页背景色 */
  paginationBackground?: boolean
  /** 默认排序 */
  defaultSort?: { prop: string; order: 'ascending' | 'descending' }
  /** 行键名 */
  rowKey?: string
  /** 表格高度 */
  height?: string | number
  /** 表格最大高度 */
  maxHeight?: string | number
  /** 是否显示斑马纹 */
  stripe?: boolean
  /** 是否显示边框 */
  border?: boolean
  /** 表格尺寸 */
  size?: 'large' | 'default' | 'small'
  /** 列宽度是否自撑开 */
  fit?: boolean
  /** 是否显示表头 */
  showHeader?: boolean
  /** 是否高亮当前行 */
  highlightCurrentRow?: boolean
  /** 当前行的key */
  currentRowKey?: string | number
  /** 单元格类名函数 */
  cellClassName?: (data: any) => string
  /** 行类名函数 */
  rowClassName?: (data: any) => string
  /** 表头行类名函数 */
  headerRowClassName?: (data: any) => string
  /** 表头单元格类名函数 */
  headerCellClassName?: (data: any) => string
  /** 空数据时显示的文本 */
  emptyText?: string
  /** 空状态描述 */
  emptyDescription?: string
  /** 是否显示空状态 */
  showEmptyState?: boolean
  /** 加载状态 */
  loading?: boolean
  /** 搜索处理函数 */
  onSearch?: (keyword: string) => void
  /** 排序处理函数 */
  onSortChange?: (sort: { prop: string; order: string }) => void
  /** 页码改变处理函数 */
  onPageChange?: (page: number) => void
  /** 每页数量改变处理函数 */
  onPageSizeChange?: (pageSize: number) => void
  /** 行点击处理函数 */
  onRowClick?: (row: any, column: any, event: Event) => void
  /** 行双击处理函数 */
  onRowDblclick?: (row: any, column: any, event: Event) => void
}

const props = withDefaults(defineProps<Props>(), {
  showSearch: true,
  searchPlaceholder: '搜索...',
  searchStyle: () => ({ width: '300px' }),
  selectable: false,
  selectionWidth: 50,
  reserveSelection: false,
  showIndex: false,
  indexLabel: '序号',
  indexWidth: 60,
  indexAlign: 'center',
  showActions: true,
  actionsLabel: '操作',
  actionsWidth: 200,
  actionsFixed: 'right',
  showDelete: true,
  createButtonText: '创建',
  deleteConfirmMessage: '确定要删除这条记录吗？',
  showPagination: false,
  page: 1,
  pageSize: 10,
  total: 0,
  pageSizes: () => [10, 20, 50, 100],
  paginationLayout: 'total, sizes, prev, pager, next, jumper',
  paginationSmall: false,
  paginationBackground: true,
  rowKey: 'id',
  stripe: true,
  border: true,
  size: 'default',
  fit: true,
  showHeader: true,
  highlightCurrentRow: false,
  emptyText: '暂无数据',
  emptyDescription: '暂无数据',
  showEmptyState: true,
  loading: false
})

const emit = defineEmits<{
  'selection-change': [selected: any[]]
  'sort-change': [sort: { prop: string; order: string }]
  'current-change': [currentRow: any, oldCurrentRow: any]
  'row-click': [row: any, column: any, event: Event]
  'row-dblclick': [row: any, column: any, event: Event]
  'create': []
  'detail': [row: any]
  'edit': [row: any]
  'delete': [row: any]
  'search': [keyword: string]
  'page-change': [page: number]
  'page-size-change': [pageSize: number]
}>()

const router = useRouter()
const searchKeyword = ref('')
const selectedItems = ref<any[]>([])
const deletingId = ref<string | number | null>(null)
const currentPage = ref(props.page)
const pageSizeValue = ref(props.pageSize)

// 计算过滤后的数据
const filteredData = computed(() => {
  if (!searchKeyword.value) {
    return props.data
  }
  
  const keyword = searchKeyword.value.toLowerCase()
  return props.data.filter(item => {
    // 在所有列中搜索
    return props.columns.some(column => {
      if (!column.prop) return false
      
      const value = item[column.prop]
      if (value === null || value === undefined) return false
      
      return String(value).toLowerCase().includes(keyword)
    })
  })
})

// 获取行ID
const getRowId = (row: any): string | number => {
  return row[props.rowKey]
}

// 处理搜索
const handleSearch = () => {
  if (props.onSearch) {
    props.onSearch(searchKeyword.value)
  }
  emit('search', searchKeyword.value)
}

// 处理搜索清除
const handleSearchClear = () => {
  searchKeyword.value = ''
  handleSearch()
}

// 处理选择改变
const handleSelectionChange = (selection: any[]) => {
  selectedItems.value = selection
  emit('selection-change', selection)
}

// 处理排序改变
const handleSortChange = (sort: { prop: string; order: string }) => {
  if (props.onSortChange) {
    props.onSortChange(sort)
  }
  emit('sort-change', sort)
}

// 处理创建
const handleCreate = () => {
  if (props.createRoute) {
    router.push(props.createRoute)
  }
  emit('create')
}

// 处理详情
const handleDetail = (row: any) => {
  if (props.detailRoute) {
    const route = props.detailRoute.replace(':id', getRowId(row))
    router.push(route)
  }
  emit('detail', row)
}

// 处理编辑
const handleEdit = (row: any) => {
  if (props.editRoute) {
    const route = props.editRoute.replace(':id', getRowId(row))
    router.push(route)
  }
  emit('edit', row)
}

// 处理删除
const handleDelete = async (row: any) => {
  try {
    const rowId = getRowId(row)
    const message = typeof props.deleteConfirmMessage === 'function' 
      ? props.deleteConfirmMessage(row) 
      : props.deleteConfirmMessage.replace('{name}', row.name || rowId)
    
    await ElMessageBox.confirm(
      message,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }
    )

    deletingId.value = rowId
    
    if (props.onDelete) {
      await props.onDelete(row)
    }
    
    emit('delete', row)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  } finally {
    deletingId.value = null
  }
}

// 处理分页大小改变
const handleSizeChange = (size: number) => {
  pageSizeValue.value = size
  if (props.onPageSizeChange) {
    props.onPageSizeChange(size)
  }
  emit('page-size-change', size)
}

// 处理页码改变
const handleCurrentChange = (page: number) => {
  currentPage.value = page
  if (props.onPageChange) {
    props.onPageChange(page)
  }
  emit('page-change', page)
}

// 监听外部页码变化
watch(() => props.page, (newPage) => {
  currentPage.value = newPage
})

// 监听外部每页数量变化
watch(() => props.pageSize, (newPageSize) => {
  pageSizeValue.value = newPageSize
})

// 暴露方法给父组件
defineExpose({
  clearSelection: () => {
    // 这里需要访问 el-table 实例的 clearSelection 方法
    // 实际使用时需要通过 ref 获取 el-table 实例
  },
  getSelectedItems: () => selectedItems.value,
  clearSearch: () => {
    searchKeyword.value = ''
    handleSearchClear()
  }
})
</script>

<style scoped>
.generic-table {
  width: 100%;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.table-pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .table-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-right {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-right .el-input {
    width: 100% !important;
    margin-right: 0 !important;
  }
}
</style>