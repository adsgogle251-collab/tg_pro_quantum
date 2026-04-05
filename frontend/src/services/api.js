import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const isLogoutRequest = err.config?.url?.includes('/auth/logout')
    if (err.response?.status === 401 && !isLogoutRequest) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// ─── Auth ────────────────────────────────────────────────────────────────────
export const register = (data) =>
  api.post('/auth/register', data).then((r) => r.data)

export const login = (credentials) =>
  api.post('/auth/login', credentials).then((r) => r.data)

export const logout = () =>
  api.post('/auth/logout').then((r) => r.data)

// ─── Profile ─────────────────────────────────────────────────────────────────
export const getProfile = () =>
  api.get('/users/me').then((r) => r.data)

export const updateProfile = (data) =>
  api.patch('/users/me', data).then((r) => r.data)

export const changePassword = (data) =>
  api.post('/users/me/change-password', data).then((r) => r.data)

// ─── 2FA ─────────────────────────────────────────────────────────────────────
export const setup2FA = () =>
  api.post('/auth/2fa/setup').then((r) => r.data)

export const verify2FA = (data) =>
  api.post('/auth/2fa/verify', data).then((r) => r.data)

export const disable2FA = () =>
  api.post('/auth/2fa/disable').then((r) => r.data)

// ─── API Keys ─────────────────────────────────────────────────────────────────
export const getApiKeys = () =>
  api.get('/users/me/api-keys').then((r) => r.data)

export const createApiKey = (data) =>
  api.post('/users/me/api-keys', data).then((r) => r.data)

export const revokeApiKey = (id) =>
  api.delete(`/users/me/api-keys/${id}`).then((r) => r.data)

// ─── Accounts ────────────────────────────────────────────────────────────────
export const getAccounts = (params) =>
  api.get('/accounts', { params }).then((r) => r.data)

// ─── Campaigns ───────────────────────────────────────────────────────────────
export const getCampaigns = (params) =>
  api.get('/campaigns', { params }).then((r) => r.data)

export const exportCampaigns = (params) =>
  api.get('/campaigns/export', { params, responseType: 'blob' }).then((r) => r.data)

// ─── Analytics ───────────────────────────────────────────────────────────────
export const getAnalytics = (params) =>
  api.get('/analytics', { params }).then((r) => r.data)

// ─── Broadcast ───────────────────────────────────────────────────────────────
export const getBroadcastStats = () =>
  api.get('/broadcast/stats').then((r) => r.data)

export const exportAccounts = (params) =>
  api.get('/accounts/export', { params, responseType: 'blob' }).then((r) => r.data)

// ─── Admin — Licenses ────────────────────────────────────────────────────────
export const getLicenses = (params) =>
  api.get('/admin/licenses', { params }).then((r) => r.data)

export const createLicense = (data) =>
  api.post('/admin/licenses', data).then((r) => r.data)

export const updateLicense = (id, data) =>
  api.patch(`/admin/licenses/${id}`, data).then((r) => r.data)

// ─── Admin — Clients ─────────────────────────────────────────────────────────
export const getClients = (params) =>
  api.get('/admin/clients', { params }).then((r) => r.data)

export const updateClient = (id, data) =>
  api.patch(`/admin/clients/${id}`, data).then((r) => r.data)

// ─── Notifications ───────────────────────────────────────────────────────────
export const getNotifications = (params) =>
  api.get('/notifications', { params }).then((r) => r.data)

export const markNotificationRead = (id) =>
  api.patch(`/notifications/${id}/read`).then((r) => r.data)

export default api
