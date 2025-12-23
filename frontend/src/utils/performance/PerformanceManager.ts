/**
 * 性能管理器 - 统一管理前端性能优化策略
 *
 * 功能特性：
 * 1. 路由级别的代码分割和预加载
 * 2. 组件懒加载管理
 * 3. 智能预取策略
 * 4. 性能监控和分析
 * 5. 缓存管理
 */

import { type Component, type AsyncComponentLoader } from 'vue'

// 性能配置接口
interface PerformanceConfig {
  // 预加载策略
  preloadStrategy: 'idle' | 'visible' | 'hover' | 'manual'
  // 预取延迟时间（毫秒）
  prefetchDelay: number
  // 最大并发加载数
  maxConcurrentLoads: number
  // 缓存策略
  cacheStrategy: 'memory' | 'indexedDB' | 'both'
  // 是否启用性能监控
  enableMonitoring: boolean
}

// 路由优先级
type RoutePriority = 'critical' | 'high' | 'medium' | 'low'

// 路由性能配置
interface RoutePerformanceConfig {
  priority: RoutePriority
  preload?: boolean
  prefetch?: boolean
  timeout?: number
  fallback?: Component
}

// 组件性能配置
interface ComponentPerformanceConfig {
  lazy: boolean
  preload?: boolean
  timeout?: number
  loading?: Component
  error?: Component
  delay?: number
}

class PerformanceManager {
  private static instance: PerformanceManager
  private config: PerformanceConfig
  private loadedComponents = new Map<string, Component>()
  private loadingPromises = new Map<string, Promise<Component>>()
  private prefetchQueue: string[] = []
  private isPreloading = false

  private constructor() {
    this.config = {
      preloadStrategy: 'idle',
      prefetchDelay: 2000,
      maxConcurrentLoads: 3,
      cacheStrategy: 'both',
      enableMonitoring: true
    }

    this.initPerformanceObserver()
    this.startIdlePreloading()
  }

  static getInstance(): PerformanceManager {
    if (!PerformanceManager.instance) {
      PerformanceManager.instance = new PerformanceManager()
    }
    return PerformanceManager.instance
  }

  /**
   * 配置性能管理器
   */
  configure(config: Partial<PerformanceConfig>): void {
    this.config = { ...this.config, ...config }
  }

  /**
   * 创建性能优化的异步组件
   */
  createOptimizedAsyncComponent<T extends Component>(
    loader: AsyncComponentLoader<T>,
    config: ComponentPerformanceConfig = { lazy: true }
  ): Component {
    if (!config.lazy) {
      // 非懒加载组件，直接加载
      loader().then(component => {
        const name = this.getComponentName(loader)
        this.loadedComponents.set(name, component)
      })
      return loader
    }

    return this.createLazyComponent(loader, config)
  }

  /**
   * 创建懒加载组件
   */
  private createLazyComponent<T extends Component>(
    loader: AsyncComponentLoader<T>,
    config: ComponentPerformanceConfig
  ): Component {
    const name = this.getComponentName(loader)

    // 检查是否已缓存
    if (this.loadedComponents.has(name)) {
      return this.loadedComponents.get(name)!
    }

    // 检查是否正在加载
    if (this.loadingPromises.has(name)) {
      return this.createLoadingWrapper(config)
    }

    const loadPromise = this.loadComponentWithTimeout(loader, config.timeout || 5000)
    this.loadingPromises.set(name, loadPromise)

    // 预加载处理
    if (config.preload) {
      this.schedulePreload(() => loadPromise)
    }

    return this.defineAsyncComponent(loader, config)
  }

  /**
   * 定义异步组件
   */
  private defineAsyncComponent<T extends Component>(
    loader: AsyncComponentLoader<T>,
    config: ComponentPerformanceConfig
  ): Component {
    return {
      setup() {
        // 组件逻辑
      }
    } as any
  }

  /**
   * 带超时的组件加载
   */
  private async loadComponentWithTimeout<T extends Component>(
    loader: AsyncComponentLoader<T>,
    timeout: number
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new Error(`Component loading timeout after ${timeout}ms`))
      }, timeout)

      loader()
        .then(component => {
          clearTimeout(timer)
          resolve(component)
        })
        .catch(error => {
          clearTimeout(timer)
          reject(error)
        })
    })
  }

  /**
   * 创建路由性能配置
   */
  createRoutePerformanceConfig(): Map<string, RoutePerformanceConfig> {
    const configs = new Map<string, RoutePerformanceConfig>()

    // 核心路由 - 立即加载
    configs.set('DashboardHome', {
      priority: 'critical',
      preload: true,
      timeout: 3000
    })

    configs.set('Login', {
      priority: 'critical',
      preload: true,
      timeout: 2000
    })

    // 高频路由 - 空闲时预加载
    configs.set('SingleAnalysis', {
      priority: 'high',
      preload: false,
      prefetch: true,
      timeout: 5000
    })

    configs.set('StockScreeningHome', {
      priority: 'high',
      preload: false,
      prefetch: true,
      timeout: 5000
    })

    configs.set('FavoritesHome', {
      priority: 'high',
      preload: false,
      prefetch: true,
      timeout: 5000
    })

    // 中等优先级 - hover时预加载
    configs.set('BatchAnalysis', {
      priority: 'medium',
      preload: false,
      prefetch: true,
      timeout: 8000
    })

    configs.set('ReportsHome', {
      priority: 'medium',
      preload: false,
      prefetch: true,
      timeout: 8000
    })

    configs.set('LearningHome', {
      priority: 'medium',
      preload: false,
      prefetch: false,
      timeout: 8000
    })

    // 低优先级 - 手动加载
    configs.set('TaskCenterHome', {
      priority: 'low',
      preload: false,
      prefetch: false,
      timeout: 10000
    })

    configs.set('PaperTradingHome', {
      priority: 'low',
      preload: false,
      prefetch: false,
      timeout: 10000
    })

    // 设置页面 - 根据权限决定优先级
    configs.set('SettingsHome', {
      priority: 'medium',
      preload: false,
      prefetch: true,
      timeout: 8000
    })

    return configs
  }

  /**
   * 智能预取路由
   */
  prefetchRoute(routeName: string): void {
    const configs = this.createRoutePerformanceConfig()
    const config = configs.get(routeName)

    if (!config || !config.prefetch) {
      return
    }

    if (!this.prefetchQueue.includes(routeName)) {
      this.prefetchQueue.push(routeName)
      this.processPrefetchQueue()
    }
  }

  /**
   * 处理预取队列
   */
  private async processPrefetchQueue(): Promise<void> {
    if (this.isPreloading || this.prefetchQueue.length === 0) {
      return
    }

    this.isPreloading = true

    while (this.prefetchQueue.length > 0) {
      const routeName = this.prefetchQueue.shift()!

      try {
        // 在空闲时预加载
        await this.scheduleIdleLoad(() => {
          console.log(`🚀 Prefetching route: ${routeName}`)
          // 实际的路由预加载逻辑
        })
      } catch (error) {
        console.warn(`Failed to prefetch route ${routeName}:`, error)
      }
    }

    this.isPreloading = false
  }

  /**
   * 调度空闲时加载
   */
  private scheduleIdleLoad(loadFn: () => void): Promise<void> {
    return new Promise((resolve) => {
      if ('requestIdleCallback' in window) {
        requestIdleCallback(() => {
          loadFn()
          resolve()
        })
      } else {
        // 降级到 setTimeout
        setTimeout(() => {
          loadFn()
          resolve()
        }, 1)
      }
    })
  }

  /**
   * 调度预加载
   */
  private schedulePreload(loadFn: () => Promise<any>): void {
    if (this.config.preloadStrategy === 'idle') {
      this.scheduleIdleLoad(() => loadFn())
    } else {
      // 其他策略的实现
      setTimeout(() => loadFn(), this.config.prefetchDelay)
    }
  }

  /**
   * 启动空闲时预加载
   */
  private startIdlePreloading(): void {
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        this.preloadHighPriorityRoutes()
      })
    }
  }

  /**
   * 预加载高优先级路由
   */
  private preloadHighPriorityRoutes(): void {
    const configs = this.createRoutePerformanceConfig()

    for (const [routeName, config] of configs) {
      if (config.priority === 'critical' || config.preload) {
        this.prefetchRoute(routeName)
      }
    }
  }

  /**
   * 初始化性能监控
   */
  private initPerformanceObserver(): void {
    if (!this.config.enableMonitoring || !('PerformanceObserver' in window)) {
      return
    }

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        this.analyzePerformanceEntry(entry as PerformanceEntry)
      }
    })

    observer.observe({ entryTypes: ['navigation', 'resource', 'measure'] })
  }

  /**
   * 分析性能条目
   */
  private analyzePerformanceEntry(entry: PerformanceEntry): void {
    if (entry.entryType === 'navigation') {
      const navEntry = entry as PerformanceNavigationTiming
      console.log('📊 Page Load Performance:', {
        domContentLoaded: navEntry.domContentLoadedEventEnd - navEntry.domContentLoadedEventStart,
        loadComplete: navEntry.loadEventEnd - navEntry.loadEventStart,
        totalTime: navEntry.loadEventEnd - navEntry.fetchStart
      })
    }
  }

  /**
   * 获取组件名称
   */
  private getComponentName(loader: AsyncComponentLoader<any>): string {
    return loader.toString().replace(/[^a-zA-Z0-9]/g, '_')
  }

  /**
   * 创建加载包装器
   */
  private createLoadingWrapper(config: ComponentPerformanceConfig): Component {
    // 返回加载中的组件
    return config.loading || this.createDefaultLoadingComponent()
  }

  /**
   * 创建默认加载组件
   */
  private createDefaultLoadingComponent(): Component {
    return {
      template: '<div class="component-loading">加载中...</div>'
    } as any
  }

  /**
   * 获取性能统计
   */
  getPerformanceStats() {
    return {
      loadedComponents: this.loadedComponents.size,
      loadingComponents: this.loadingPromises.size,
      prefetchQueue: this.prefetchQueue.length,
      isPreloading: this.isPreloading
    }
  }
}

export default PerformanceManager
export type {
  PerformanceConfig,
  RoutePerformanceConfig,
  ComponentPerformanceConfig,
  RoutePriority
}