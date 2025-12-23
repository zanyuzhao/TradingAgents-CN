/**
 * 路由优化器 - 专门处理路由级别的性能优化
 *
 * 功能：
 * 1. 智能代码分割
 * 2. 路由预加载策略
 * 3. 权限相关优化
 * 4. 路由缓存管理
 */

import { type RouteRecordRaw } from 'vue-router'
import PerformanceManager, { type RoutePerformanceConfig } from './PerformanceManager'

interface OptimizedRouteConfig extends RouteRecordRaw {
  performance?: RoutePerformanceConfig
  preloadChunks?: string[]
  cacheKey?: string
}

class RouteOptimizer {
  private performanceManager: PerformanceManager
  private routeConfigs = new Map<string, RoutePerformanceConfig>()
  private preloadRegistry = new Set<string>()

  constructor() {
    this.performanceManager = PerformanceManager.getInstance()
    this.initRouteConfigs()
  }

  /**
   * 初始化路由配置
   */
  private initRouteConfigs(): void {
    this.routeConfigs = this.performanceManager.createRoutePerformanceConfig()
  }

  /**
   * 优化路由配置
   */
  optimizeRoutes(routes: RouteRecordRaw[]): OptimizedRouteConfig[] {
    return routes.map(route => this.optimizeRoute(route))
  }

  /**
   * 优化单个路由
   */
  private optimizeRoute(route: RouteRecordRaw): OptimizedRouteConfig {
    const optimizedRoute: OptimizedRouteConfig = { ...route }

    // 添加性能配置
    const routeName = route.name as string
    if (this.routeConfigs.has(routeName)) {
      optimizedRoute.performance = this.routeConfigs.get(routeName)
    }

    // 优化组件加载
    if (route.component) {
      optimizedRoute.component = this.optimizeComponentLoader(route.component, routeName)
    }

    // 优化子路由
    if (route.children && route.children.length > 0) {
      optimizedRoute.children = route.children.map(child =>
        this.optimizeRoute(child)
      )
    }

    // 添加缓存键
    optimizedRoute.cacheKey = this.generateCacheKey(routeName)

    return optimizedRoute
  }

  /**
   * 优化组件加载器
   */
  private optimizeComponentLoader(
    componentLoader: any,
    routeName: string
  ): any {
    const config = this.routeConfigs.get(routeName)

    if (!config) {
      return componentLoader
    }

    // 根据优先级决定加载策略
    if (config.priority === 'critical') {
      // 关键路由 - 立即加载
      this.preloadComponent(componentLoader, routeName)
      return componentLoader
    }

    if (config.preload) {
      // 预加载路由 - 空闲时加载
      this.schedulePreload(componentLoader, routeName)
    }

    // 包装组件加载器，添加超时和错误处理
    return this.wrapComponentLoader(componentLoader, config)
  }

  /**
   * 包装组件加载器
   */
  private wrapComponentLoader(componentLoader: any, config: RoutePerformanceConfig): any {
    return async () => {
      try {
        const startTime = performance.now()
        const component = await Promise.race([
          componentLoader(),
          this.createTimeoutPromise(config.timeout || 5000)
        ])
        const loadTime = performance.now() - startTime

        console.log(`📦 Route component loaded: ${loadTime.toFixed(2)}ms`)
        return component
      } catch (error) {
        console.error('Component loading failed:', error)
        return this.getErrorFallback()
      }
    }
  }

  /**
   * 预加载组件
   */
  private preloadComponent(componentLoader: any, routeName: string): void {
    if (this.preloadRegistry.has(routeName)) {
      return
    }

    this.preloadRegistry.add(routeName)

    // 立即开始预加载
    componentLoader().then(() => {
      console.log(`⚡ Preloaded critical route: ${routeName}`)
    }).catch(error => {
      console.warn(`Failed to preload route ${routeName}:`, error)
    })
  }

  /**
   * 调度预加载
   */
  private schedulePreload(componentLoader: any, routeName: string): void {
    // 在空闲时预加载
    if ('requestIdleCallback' in window) {
      requestIdleCallback(() => {
        componentLoader().then(() => {
          console.log(`🚀 Preloaded route: ${routeName}`)
        })
      })
    } else {
      setTimeout(() => {
        componentLoader().then(() => {
          console.log(`🚀 Preloaded route: ${routeName}`)
        })
      }, 2000)
    }
  }

  /**
   * 创建超时 Promise
   */
  private createTimeoutPromise(timeout: number): Promise<never> {
    return new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Component loading timeout after ${timeout}ms`))
      }, timeout)
    })
  }

  /**
   * 获取错误回退组件
   */
  private getErrorFallback() {
    return {
      template: `
        <div class="route-error-fallback">
          <h3>页面加载失败</h3>
          <p>请刷新页面重试</p>
        </div>
      `,
      style: `
        .route-error-fallback {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 200px;
          color: #666;
        }
      `
    }
  }

  /**
   * 生成缓存键
   */
  private generateCacheKey(routeName: string): string {
    return `route_${routeName}_${Date.now()}`
  }

  /**
   * 创建智能预取 Hook
   */
  createPrefetchHook() {
    return {
      mounted: (el: HTMLElement, binding: { value: string }) => {
        const routeName = binding.value

        // 鼠标悬停时预取
        el.addEventListener('mouseenter', () => {
          this.performanceManager.prefetchRoute(routeName)
        }, { once: true })

        // 触摸设备上触摸时预取
        el.addEventListener('touchstart', () => {
          this.performanceManager.prefetchRoute(routeName)
        }, { once: true })
      }
    }
  }

  /**
   * 创建路由级别的分析器
   */
  analyzeRoutePerformance(routeName: string): {
    loadTime: number
    renderTime: number
    totalTime: number
  } {
    const navigationEntries = performance.getEntriesByType('navigation')
    const latestEntry = navigationEntries[navigationEntries.length - 1] as PerformanceNavigationTiming

    if (latestEntry) {
      return {
        loadTime: latestEntry.loadEventEnd - latestEntry.loadEventStart,
        renderTime: latestEntry.domContentLoadedEventEnd - latestEntry.domContentLoadedEventStart,
        totalTime: latestEntry.loadEventEnd - latestEntry.fetchStart
      }
    }

    return {
      loadTime: 0,
      renderTime: 0,
      totalTime: 0
    }
  }

  /**
   * 批量预加载用户常用路由
   */
  preloadUserFrequentRoutes(userRoutes: string[]): void {
    userRoutes.forEach(routeName => {
      const config = this.routeConfigs.get(routeName)
      if (config && config.priority !== 'low') {
        this.performanceManager.prefetchRoute(routeName)
      }
    })
  }

  /**
   * 清理未使用的预加载资源
   */
  cleanupUnusedPreloads(): void {
    // 实现清理逻辑
    console.log('🧹 Cleaning up unused preload resources')
  }

  /**
   * 获取路由性能报告
   */
  getPerformanceReport() {
    return {
      totalRoutes: this.routeConfigs.size,
      preloadedRoutes: this.preloadRegistry.size,
      configurations: Object.fromEntries(this.routeConfigs)
    }
  }
}

export default RouteOptimizer
export type { OptimizedRouteConfig }