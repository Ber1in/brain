import { useAuthStore } from '@/stores/auth'

export const checkAuth = (): boolean => {
  const authStore = useAuthStore()
  return authStore.isAuthenticated
}

export const getToken = (): string => {
  const authStore = useAuthStore()
  return authStore.accessToken
}
