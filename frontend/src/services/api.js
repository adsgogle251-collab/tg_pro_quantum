import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
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
    if (err.response?.status === 401) localStorage.removeItem('auth_token')
    return Promise.reject(err)
  }
)

export const login = (credentials) =>
  api.post('/auth/login', credentials).then((r) => r.data)

export const getAccounts = () =>
  api.get('/accounts').then((r) => r.data)

export const getCampaigns = () =>
  api.get('/campaigns').then((r) => r.data)

export const getAnalytics = (params) =>
  api.get('/analytics', { params }).then((r) => r.data)

export const getBroadcastStats = () =>
  api.get('/broadcast/stats').then((r) => r.data)

export default api
