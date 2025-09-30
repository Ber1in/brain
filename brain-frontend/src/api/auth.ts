import apiClient from './client'
import { LoginCredentials, TokenResponse } from '@/types/api'

export const authApi = {
  login(credentials: LoginCredentials): Promise<TokenResponse> {
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)
    formData.append('grant_type', 'password')

    if (credentials.scope) formData.append('scope', credentials.scope)
    if (credentials.client_id) formData.append('client_id', credentials.client_id)
    if (credentials.client_secret) formData.append('client_secret', credentials.client_secret)

    return apiClient.post('/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },

  refreshToken(refreshToken: string): Promise<TokenResponse> {
    const formData = new URLSearchParams()
    formData.append('grant_type', 'refresh_token')
    formData.append('refresh_token', refreshToken)

    return apiClient.post('/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },
}
