import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getMe } from '../api/auth.js'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const token = ref(localStorage.getItem('token') || '')
  const username = ref('')

  // 计算属性
  const isAuthenticated = computed(() => !!token.value)

  // 登录
  async function login(user, pass) {
    const data = await apiLogin(user, pass)
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    username.value = user
    return data
  }

  // 注册
  async function register(user, pass) {
    const data = await apiRegister(user, pass)
    token.value = data.access_token
    localStorage.setItem('token', data.access_token)
    username.value = user
    return data
  }

  // 退出登录
  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
  }

  // 检查认证状态（调用 getMe 验证 token 是否有效）
  async function checkAuth() {
    const savedToken = localStorage.getItem('token')
    if (!savedToken) {
      token.value = ''
      return false
    }
    try {
      await getMe()
      token.value = savedToken
      return true
    } catch {
      token.value = ''
      localStorage.removeItem('token')
      return false
    }
  }

  // 处理 401 过期事件
  function onAuthExpired() {
    token.value = ''
    username.value = ''
    // localStorage 已由拦截器清除
  }

  return {
    token,
    username,
    isAuthenticated,
    login,
    register,
    logout,
    checkAuth,
    onAuthExpired,
  }
})
