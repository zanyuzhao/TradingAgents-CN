/**
 * 优化后的路由配置示例
 * 展示如何使用性能优化工具来改进路由性能
 */

import { type RouteRecordRaw } from 'vue-router'
import { performanceOptimizer } from '../utils/performance'

// 创建预取指令
export const vPrefetch = performanceOptimizer.routes.createPrefetchHook()

// 路由配置工厂
export const createOptimizedRoute = (
  path: string,
  name: string,
  componentLoader: () => Promise<any>,
  options: {
    title?: string
    icon?: string
    requiresAuth?: boolean
    priority?: 'critical' | 'high' | 'medium' | 'low'
    preload?: boolean
    prefetch?: boolean
    hideInMenu?: boolean
    transition?: string
    children?: any[]
  } = {}
): RouteRecordRaw => {
  const {
    title,
    icon,
    requiresAuth = false,
    priority = 'medium',
    preload = false,
    prefetch = false,
    hideInMenu = false,
    transition = 'fade',
    children = []
  } = options

  // 使用性能优化器创建优化后的组件加载器
  const optimizedComponent = performanceOptimizer.global.createAsyncComponent(
    componentLoader,
    {
      lazy: true,
      preload: priority === 'critical' || preload,
      timeout: priority === 'critical' ? 3000 : 8000
    }
  )

  const route: RouteRecordRaw = {
    path,
    name,
    component: optimizedComponent,
    meta: {
      title,
      icon,
      requiresAuth,
      hideInMenu,
      transition,
      priority,
      preload,
      prefetch
    },
    children
  }

  return route
}

// 创建布局组件加载器
const createLayoutLoader = (layoutName: string) => () =>
  import(`@/layouts/${layoutName}.vue`)

// 创建页面组件加载器
const createPageLoader = (pagePath: string) => () =>
  import(`@/views/${pagePath}.vue`)

// 优化后的路由配置
export const optimizedRoutes: RouteRecordRaw[] = [
  // 根路径重定向
  {
    path: '/',
    redirect: '/dashboard'
  },

  // 登录页面 - 关键优先级
  createOptimizedRoute(
    '/login',
    'Login',
    createPageLoader('Auth/Login'),
    {
      title: '登录',
      priority: 'critical',
      preload: true,
      hideInMenu: true
    }
  ),

  // 仪表板 - 关键优先级
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: createLayoutLoader('BasicLayout'),
    meta: {
      title: '仪表板',
      icon: 'Dashboard',
      requiresAuth: true,
      transition: 'fade'
    },
    children: [
      createOptimizedRoute(
        '',
        'DashboardHome',
        createPageLoader('Dashboard/index'),
        {
          title: '仪表板',
          priority: 'critical',
          preload: true,
          requiresAuth: true
        }
      )
    ]
  },

  // 分析页面 - 高优先级
  {
    path: '/analysis',
    name: 'Analysis',
    component: createLayoutLoader('BasicLayout'),
    redirect: '/analysis/single',
    meta: {
      title: '股票分析',
      icon: 'TrendCharts',
      requiresAuth: true
    },
    children: [
      createOptimizedRoute(
        'single',
        'SingleAnalysis',
        createPageLoader('Analysis/SingleAnalysis'),
        {
          title: '个股分析',
          priority: 'high',
          prefetch: true
        }
      ),
      createOptimizedRoute(
        'batch',
        'BatchAnalysis',
        createPageLoader('Analysis/BatchAnalysis'),
        {
          title: '批量分析',
          priority: 'medium',
          prefetch: true
        }
      )
    ]
  },

  // 筛选页面 - 高优先级
  {
    path: '/screening',
    name: 'StockScreening',
    component: createLayoutLoader('BasicLayout'),
    meta: {
      title: '股票筛选',
      icon: 'Search',
      requiresAuth: true,
      transition: 'slide-up'
    },
    children: [
      createOptimizedRoute(
        '',
        'StockScreeningHome',
        createPageLoader('Screening/index'),
        {
          title: '股票筛选',
          priority: 'high',
          prefetch: true,
          requiresAuth: true
        }
      )
    ]
  },

  // 自选股页面 - 高优先级
  {
    path: '/favorites',
    name: 'Favorites',
    component: createLayoutLoader('BasicLayout'),
    meta: {
      title: '我的自选股',
      icon: 'Star',
      requiresAuth: true,
      transition: 'slide-up'
    },
    children: [
      createOptimizedRoute(
        '',
        'FavoritesHome',
        createPageLoader('Favorites/index'),
        {
          title: '我的自选股',
          priority: 'high',
          prefetch: true,
          requiresAuth: true
        }
      )
    ]
  },

  // 报告页面 - 中等优先级
  {
    path: '/reports',
    name: 'Reports',
    component: createLayoutLoader('BasicLayout'),
    meta: {
      title: '分析报告',
      icon: 'Document',
      requiresAuth: true,
      transition: 'fade'
    },
    children: [
      createOptimizedRoute(
        '',
        'ReportsHome',
        createPageLoader('Reports/index'),
        {
          title: '分析报告',
          priority: 'medium',
          prefetch: true,
          requiresAuth: true
        }
      ),
      createOptimizedRoute(
        'view/:id',
        'ReportDetail',
        createPageLoader('Reports/ReportDetail'),
        {
          title: '报告详情',
          priority: 'medium',
          requiresAuth: true
        }
      ),
      createOptimizedRoute(
        'token',
        'TokenStatistics',
        createPageLoader('Reports/TokenStatistics'),
        {
          title: 'Token统计',
          priority: 'low',
          requiresAuth: true
        }
      )
    ]
  },

  // 学习中心 - 中等优先级（无需认证）
  {
    path: '/learning',
    name: 'Learning',
    component: createLayoutLoader('BasicLayout'),
    meta: {
      title: '学习中心',
      icon: 'Reading',
      requiresAuth: false,
      transition: 'fade'
    },
    children: [
      createOptimizedRoute(
        '',
        'LearningHome',
        createPageLoader('Learning/index'),
        {
          title: '学习中心',
          priority: 'medium',
          requiresAuth: false
        }
      ),
      createOptimizedRoute(
        ':category',
        'LearningCategory',
        createPageLoader('Learning/Category'),
        {
          title: '学习分类',
          priority: 'low',
          requiresAuth: false
        }
      ),
      createOptimizedRoute(
        'article/:id',
        'LearningArticle',
        createPageLoader('Learning/Article'),
        {
          title: '文章详情',
          priority: 'low',
          requiresAuth: false
        }
      )
    ]
  },

  // 设置页面 - 中等优先级
  {
    path: '/settings',
    name: 'Settings',
    component: createLayoutLoader('BasicLayout'),
    meta: {
      title: '设置',
      icon: 'Setting',
      requiresAuth: true,
      transition: 'slide-left'
    },
    children: [
      createOptimizedRoute(
        '',
        'SettingsHome',
        createPageLoader('Settings/index'),
        {
          title: '设置',
          priority: 'medium',
          prefetch: true,
          requiresAuth: true
        }
      ),
      createOptimizedRoute(
        'config',
        'ConfigManagement',
        createPageLoader('Settings/ConfigManagement'),
        {
          title: '配置管理',
          priority: 'low',
          requiresAuth: true
        }
      ),
      createOptimizedRoute(
        'usage',
        'UsageStatistics',
        createPageLoader('Settings/UsageStatistics'),
        {
          title: '使用统计',
          priority: 'low',
          requiresAuth: true
        }
      )
    ]
  },

  // 404页面 - 低优先级
  createOptimizedRoute(
    '/:pathMatch(.*)*',
    'NotFound',
    createPageLoader('Error/404'),
    {
      title: '页面不存在',
      priority: 'low',
      hideInMenu: true
    }
  )
]

// 路由性能优化中间件
export const routePerformanceMiddleware = (to: any, from: any, next: any) => {
  // 开始性能测量
  performanceOptimizer.utils.mark(`route-start-${to.name}`)

  // 智能预取相关路由
  if (from.name) {
    // 基于当前路由预测下一步可能访问的路由
    const predictions = predictNextRoutes(from.name as string)
    predictions.forEach(routeName => {
      performanceOptimizer.routes.prefetch(routeName)
    })
  }

  // 智能库加载
  performanceOptimizer.libraries.smartLoad(`navigate_to_${to.name}`)

  next()
}

// 预测下一个可能访问的路由
const predictNextRoutes = (currentRoute: string): string[] => {
  const predictions: Record<string, string[]> = {
    'Dashboard': ['SingleAnalysis', 'StockScreeningHome', 'FavoritesHome'],
    'SingleAnalysis': ['StockDetail', 'BatchAnalysis', 'ReportsHome'],
    'StockScreeningHome': ['SingleAnalysis', 'FavoritesHome'],
    'ReportsHome': ['ReportDetail', 'SingleAnalysis'],
    'SettingsHome': ['ConfigManagement', 'UsageStatistics']
  }

  return predictions[currentRoute] || []
}

export default optimizedRoutes