/**
 * 简化的性能优化工具统一入口
 */

import SimpleOptimizer from './SimpleOptimizer'

// 创建单例实例
const simpleOptimizer = SimpleOptimizer.getInstance()

/**
 * 简化的性能优化工具类
 */
class SimplePerformanceOptimizer {
  private isInitialized = false

  /**
   * 初始化性能优化系统
   */
  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return
    }

    console.log('🚀 Initializing Simple Performance Optimizer...')

    try {
      // 预加载关键资源
      await simpleOptimizer.preloadCriticalResources()

      this.isInitialized = true
      console.log('✅ Simple Performance Optimizer initialized successfully')
    } catch (error) {
      console.error('❌ Failed to initialize Performance Optimizer:', error)
    }
  }

  /**
   * 创建懒加载组件
   */
  createLazyComponent(loader: any, options: any = {}) {
    return simpleOptimizer.createLazyComponent(loader)
  }

  /**
   * 预取路由
   */
  prefetchRoute(routeName: string): void {
    console.log(`🚀 Prefetching route: ${routeName}`)
  }

  /**
   * 记录页面访问
   */
  recordPageVisit(pageName: string): void {
    simpleOptimizer.recordPageVisit(pageName)
  }

  /**
   * 预测下一页面
   */
  predictNextPage(currentPage: string): string[] {
    return simpleOptimizer.predictNextPage(currentPage)
  }

  /**
   * 测量性能
   */
  measurePerformance(name: string, fn: () => void): number {
    return simpleOptimizer.measurePerformance(name, fn)
  }

  /**
   * 获取性能统计
   */
  getStats() {
    return simpleOptimizer.getStats()
  }

  /**
   * 工具方法 - 创建性能标记
   */
  mark(name: string): void {
    performance.mark(name)
  }

  /**
   * 工具方法 - 测量性能
   */
  measure(name: string, startMark: string, endMark?: string): void {
    performance.measure(name, startMark, endMark)
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    simpleOptimizer.clearCache()
  }

  /**
   * 兼容性属性
   */
  get routes() {
    return {
      prefetch: this.prefetchRoute
    }
  }

  get components() {
    return {
      createLazy: this.createLazyComponent
    }
  }

  get libraries() {
    return {
      smartLoad: (userAction: string) => {
        console.log(`📚 Smart loading libraries for: ${userAction}`)
      }
    }
  }

  get global() {
    return {
      getStats: this.getStats,
      createAsyncComponent: this.createLazyComponent
    }
  }

  get utils() {
    return {
      mark: this.mark,
      measure: this.measure
    }
  }
}

// 导出单例实例
export const performanceOptimizer = new SimplePerformanceOptimizer()

// Vue 插件形式
export const PerformancePlugin = {
  install(app: any, options: any = {}) {
    // 注入性能优化器
    app.config.globalProperties.$perf = performanceOptimizer
    app.provide('performanceOptimizer', performanceOptimizer)

    // 自动初始化
    performanceOptimizer.initialize()
  }
}

// 默认导出
export default performanceOptimizer