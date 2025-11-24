import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const loading = ref(false)
  const pageTitle = ref('云服务器管理系统')

  const setLoading = (value: boolean) => {
    loading.value = value
  }

  const setPageTitle = (title: string) => {
    pageTitle.value = title
    document.title = title
  }

  return {
    loading,
    pageTitle,
    setLoading,
    setPageTitle,
  }
})
