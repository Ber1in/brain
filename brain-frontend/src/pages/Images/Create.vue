<template>
  <div class="image-create">
    <el-card>
      <template #header>
        <h2>录入镜像</h2>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="镜像名称" prop="name">
          <el-input v-model="form.name" placeholder="输入镜像名称" />
        </el-form-item>

        <el-form-item label="镜像源地址" prop="ceph_location">
          <el-input v-model="form.ceph_location" placeholder="格式: pool/rbd" />
        </el-form-item>

        <el-form-item label="Ceph集群IP" prop="mon_host">
          <el-input v-model="form.mon_host" placeholder="输入Ceph集群IP" />
        </el-form-item>

        <el-form-item label="最小容量(GB)" prop="min_size">
          <el-input-number
            v-model="form.min_size"
            :min="1"
            controls-position="right"
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="输入描述信息"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSubmit" :loading="loading"> 创建 </el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { imagesApi } from '@/api/images'
import { createRequiredRule, createCephLocationRule, createIPRule, createNumberRangeRule } from '@/utils/validators'
import type { ImageCreate } from '@/types/api'

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = ref<ImageCreate>({
  name: '',
  ceph_location: '',
  mon_host: '',
  min_size: 1,
  description: '',
})

// 使用公共验证规则
const rules: FormRules = {
  name: [createRequiredRule('镜像名称')],
  ceph_location: [
    createRequiredRule('镜像源地址'),
    createCephLocationRule('镜像源地址')
  ],
  mon_host: [createIPRule('Ceph集群IP')],
  min_size: [
    createRequiredRule('最小容量'),
    createNumberRangeRule('最小容量', { min: 1 })
  ],
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    await imagesApi.create(form.value)
    ElMessage.success('创建成功')
    window.location.href = '/images'
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.image-create {
  max-width: 800px;
  margin: 0 auto;
}
</style>