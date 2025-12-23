<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <img src="/logo.svg" alt="A股-智能体" class="logo" />
        <h1 class="title">A股-智能体</h1>
        <p class="subtitle">多智能体股票分析学习平台</p>
      </div>

      <el-card class="login-card" shadow="always">
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form
              :model="loginForm"
              :rules="loginRules"
              ref="loginFormRef"
              label-position="top"
              size="large"
            >
              <el-form-item label="用户名" prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名"
                  prefix-icon="User"
                />
              </el-form-item>

              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  prefix-icon="Lock"
                  show-password
                  @keyup.enter="handleLogin"
                />
              </el-form-item>

              <el-form-item>
                <div class="form-options">
                  <el-checkbox v-model="loginForm.rememberMe">
                    记住我
                  </el-checkbox>
                </div>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  size="large"
                  style="width: 100%"
                  :loading="loginLoading"
                  @click="handleLogin"
                >
                  登录
                </el-button>
              </el-form-item>

              </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form
              :model="registerForm"
              :rules="registerRules"
              ref="registerFormRef"
              label-position="top"
              size="large"
            >
              <el-form-item label="用户名" prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="请输入用户名 (3-20位字母数字下划线)"
                  prefix-icon="User"
                />
              </el-form-item>

              <el-form-item label="邮箱" prop="email">
                <el-input
                  v-model="registerForm.email"
                  placeholder="请输入邮箱地址"
                  prefix-icon="Message"
                />
              </el-form-item>

              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="请输入密码 (至少6位)"
                  prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item label="确认密码" prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="请再次确认密码"
                  prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item>
                <el-button
                  type="success"
                  size="large"
                  style="width: 100%"
                  :loading="registerLoading"
                  @click="handleRegister"
                >
                  注册
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </el-card>

      <div class="login-footer">
        <p>&copy; 2025 A股-智能体. All rights reserved.</p>
        <p class="disclaimer">
          A股-智能体 是一个 AI 多 Agents 的股票分析学习平台。平台中的分析结论、观点和“投资建议”均由 AI 自动生成，仅用于学习、研究与交流，不构成任何形式的投资建议或承诺。用户据此进行的任何投资行为及其产生的风险与后果，均由用户自行承担。市场有风险，入市需谨慎。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 表单引用
const loginFormRef = ref()
const registerFormRef = ref()

// 加载状态
const loginLoading = ref(false)
const registerLoading = ref(false)

// 当前激活的Tab
const activeTab = ref('login')

// 登录表单
const loginForm = reactive({
  username: '',
  password: '',
  rememberMe: false
})

// 注册表单
const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 登录表单验证规则
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

// 注册表单验证规则
const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为3-20位', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string, callback: Function) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleLogin = async () => {
  // 防止重复提交
  if (loginLoading.value) {
    console.log('⏭️ 登录请求进行中，跳过重复点击')
    return
  }

  try {
    await loginFormRef.value.validate()

    loginLoading.value = true
    console.log('🔐 开始登录流程...')

    // 调用真实的登录API
    const success = await authStore.login({
      username: loginForm.username,
      password: loginForm.password
    })

    if (success) {
      console.log('✅ 登录成功')
      ElMessage.success('登录成功')

      // 跳转到重定向路径或仪表板
      const redirectPath = authStore.getAndClearRedirectPath()
      console.log('🔄 重定向到:', redirectPath)
      router.push(redirectPath)
    } else {
      ElMessage.error('用户名或密码错误')
    }

  } catch (error) {
    console.error('登录失败:', error)
    // 只有在不是表单验证错误时才显示错误消息
    if (error.message && !error.message.includes('validate')) {
      ElMessage.error('登录失败，请重试')
    }
  } finally {
    loginLoading.value = false
  }
}

const handleRegister = async () => {
  // 防止重复提交
  if (registerLoading.value) {
    console.log('⏭️ 注册请求进行中，跳过重复点击')
    return
  }

  try {
    await registerFormRef.value.validate()

    registerLoading.value = true
    console.log('🔐 开始注册流程...')

    // 调用注册API
    const response = await authStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })

    if (response.success) {
      console.log('✅ 注册成功')
      ElMessage.success('注册成功，已自动登录')

      // 跳转到仪表板
      router.push('/dashboard')
    } else {
      ElMessage.error(response.message || '注册失败')
    }

  } catch (error: any) {
    console.error('注册失败:', error)
    // 显示具体错误信息
    const errorMsg = error.response?.data?.detail || error.message || '注册失败，请重试'
    ElMessage.error(errorMsg)
  } finally {
    registerLoading.value = false
  }
}


</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-container {
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
  color: white;

  .logo {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
  }

  .title {
    font-size: 32px;
    font-weight: 600;
    margin: 0 0 8px 0;
  }

  .subtitle {
    font-size: 16px;
    opacity: 0.9;
    margin: 0;
  }
}

.login-card {
  .login-tabs {
    margin: 0;
  }

  .form-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }
}

.login-footer {
  text-align: center;
  margin-top: 32px;
  color: white;
  opacity: 0.9;

  p {
    margin: 0;
    font-size: 14px;
  }

  .disclaimer {
    margin-top: 8px;
    font-size: 12px;
    line-height: 1.6;
    max-width: 800px;
    margin-left: auto;
    margin-right: auto;
    color: white;
    opacity: 0.85;
  }
}
</style>
