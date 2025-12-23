/**
 * 性能监控器 - 监控前端性能并提供优化建议
 *
 * 功能：
 * 1. 实时性能监控
 * 2. 性能指标收集
 * 3. 自动性能分析
 * 4. 优化建议生成
 * 5. 性能报告生成
 */

interface PerformanceMetrics {
  // Core Web Vitals
  fcp: number // First Contentful Paint
  lcp: number // Largest Contentful Paint
  fid: number // First Input Delay
  cls: number // Cumulative Layout Shift

  // Navigation timing
  domContentLoaded: number
  loadComplete: number
  totalTime: number

  // Resource timing
  resourceCount: number
  totalResourceSize: number
  slowResources: Array<{ name: string; duration: number; size: number }>

  // Custom metrics
  routeChangeTime: number
  componentLoadTime: number
  apiResponseTime: number

  // Memory usage
  memoryUsage?: {
    usedJSHeapSize: number
    totalJSHeapSize: number
    jsHeapSizeLimit: number
  }
}

interface PerformanceAlert {
  type: 'warning' | 'error' | 'info'
  metric: string
  value: number
  threshold: number
  message: string
  recommendation: string
  timestamp: number
}

interface OptimizationSuggestion {
  category: 'route' | 'component' | 'library' | 'image' | 'api' | 'general'
  title: string
  description: string
  impact: 'high' | 'medium' | 'low'
  effort: 'high' | 'medium' | 'low'
  expectedImprovement: string
  implementation: string
}

class PerformanceMonitor {
  private static instance: PerformanceMonitor
  private metrics: PerformanceMetrics
  private alerts: PerformanceAlert[] = []
  private observers: PerformanceObserver[] = []
  private isMonitoring = false
  private reportInterval: NodeJS.Timeout | null = null
  private metricsHistory: PerformanceMetrics[] = []
  private maxHistorySize = 100

  private constructor() {
    this.metrics = this.initializeMetrics()
  }

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor()
    }
    return PerformanceMonitor.instance
  }

  /**
   * 初始化性能指标
   */
  private initializeMetrics(): PerformanceMetrics {
    return {
      fcp: 0,
      lcp: 0,
      fid: 0,
      cls: 0,
      domContentLoaded: 0,
      loadComplete: 0,
      totalTime: 0,
      resourceCount: 0,
      totalResourceSize: 0,
      slowResources: [],
      routeChangeTime: 0,
      componentLoadTime: 0,
      apiResponseTime: 0
    }
  }

  /**
   * 开始性能监控
   */
  startMonitoring(): void {
    if (this.isMonitoring) {
      return
    }

    console.log('📊 Starting performance monitoring...')
    this.isMonitoring = true

    // 监控 Core Web Vitals
    this.observeCoreWebVitals()

    // 监控资源加载
    this.observeResourceTiming()

    // 监控路由变化
    this.observeRouteChanges()

    // 监控内存使用
    this.observeMemoryUsage()

    // 定期生成报告
    this.startPeriodicReporting()

    // 监控长任务
    this.observeLongTasks()
  }

  /**
   * 停止性能监控
   */
  stopMonitoring(): void {
    if (!this.isMonitoring) {
      return
    }

    console.log('⏹️ Stopping performance monitoring...')
    this.isMonitoring = false

    // 断开所有观察器
    this.observers.forEach(observer => observer.disconnect())
    this.observers = []

    // 停止定期报告
    if (this.reportInterval) {
      clearInterval(this.reportInterval)
      this.reportInterval = null
    }
  }

  /**
   * 监控 Core Web Vitals
   */
  private observeCoreWebVitals(): void {
    if (!('PerformanceObserver' in window)) {
      return
    }

    // 监控 LCP
    const lcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      const lastEntry = entries[entries.length - 1] as any
      this.metrics.lcp = lastEntry.startTime
      this.checkThreshold('lcp', this.metrics.lcp, 2500, 'Largest Contentful Paint')
    })
    lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })
    this.observers.push(lcpObserver)

    // 监控 FID
    const fidObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry: any) => {
        this.metrics.fid = entry.processingStart - entry.startTime
        this.checkThreshold('fid', this.metrics.fid, 100, 'First Input Delay')
      })
    })
    fidObserver.observe({ entryTypes: ['first-input'] })
    this.observers.push(fidObserver)

    // 监控 CLS
    let clsValue = 0
    const clsObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry: any) => {
        if (!entry.hadRecentInput) {
          clsValue += entry.value
          this.metrics.cls = clsValue
          this.checkThreshold('cls', this.metrics.cls, 0.1, 'Cumulative Layout Shift')
        }
      })
    })
    clsObserver.observe({ entryTypes: ['layout-shift'] })
    this.observers.push(clsObserver)

    // 监控 FCP
    const fcpObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries()
      entries.forEach((entry) => {
        if (entry.name === 'first-contentful-paint') {
          this.metrics.fcp = entry.startTime
          this.checkThreshold('fcp', this.metrics.fcp, 1800, 'First Contentful Paint')
        }
      })
    })
    fcpObserver.observe({ entryTypes: ['paint'] })
    this.observers.push(fcpObserver)
  }

  /**
   * 监控资源加载
   */
  private observeResourceTiming(): void {
    if (!('PerformanceObserver' in window)) {
      return
    }

    const resourceObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries() as PerformanceResourceTiming[]

      entries.forEach(entry => {
        this.metrics.resourceCount++

        if (entry.transferSize) {
          this.metrics.totalResourceSize += entry.transferSize
        }

        const duration = entry.responseEnd - entry.requestStart

        // 识别慢速资源
        if (duration > 1000) { // 超过1秒
          this.metrics.slowResources.push({
            name: entry.name,
            duration,
            size: entry.transferSize || 0
          })
        }
      })

      // 限制慢速资源列表大小
      if (this.metrics.slowResources.length > 10) {
        this.metrics.slowResources = this.metrics.slowResources.slice(-10)
      }
    })

    resourceObserver.observe({ entryTypes: ['resource'] })
    this.observers.push(resourceObserver)
  }

  /**
   * 监控路由变化
   */
  private observeRouteChanges(): void {
    // 监听路由变化事件
    window.addEventListener('popstate', () => {
      this.measureRouteChange()
    })

    // 监听 pushState 和 replaceState
    const originalPushState = history.pushState
    const originalReplaceState = history.replaceState

    history.pushState = (...args) => {
      const result = originalPushState.apply(history, args)
      this.measureRouteChange()
      return result
    }

    history.replaceState = (...args) => {
      const result = originalReplaceState.apply(history, args)
      this.measureRouteChange()
      return result
    }
  }

  /**
   * 测量路由变化时间
   */
  private measureRouteChange(): void {
    const startTime = performance.now()

    // 使用 requestAnimationFrame 等待路由渲染完成
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this.metrics.routeChangeTime = performance.now() - startTime
        this.checkThreshold('routeChangeTime', this.metrics.routeChangeTime, 300, 'Route Change Time')
      })
    })
  }

  /**
   * 监控内存使用
   */
  private observeMemoryUsage(): void {
    if ('memory' in performance) {
      setInterval(() => {
        const memory = (performance as any).memory
        this.metrics.memoryUsage = {
          usedJSHeapSize: memory.usedJSHeapSize,
          totalJSHeapSize: memory.totalJSHeapSize,
          jsHeapSizeLimit: memory.jsHeapSizeLimit
        }

        // 检查内存使用率
        const memoryUsageRatio = memory.usedJSHeapSize / memory.jsHeapSizeLimit
        this.checkThreshold('memoryUsage', memoryUsageRatio, 0.8, 'Memory Usage')
      }, 10000) // 每10秒检查一次
    }
  }

  /**
   * 监控长任务
   */
  private observeLongTasks(): void {
    if (!('PerformanceObserver' in window)) {
      return
    }

    try {
      const longTaskObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries()
        entries.forEach((entry) => {
          if (entry.duration > 50) { // 超过50ms的任务
            console.warn(`⚠️ Long task detected: ${entry.duration.toFixed(2)}ms`)
            this.addAlert({
              type: 'warning',
              metric: 'longTask',
              value: entry.duration,
              threshold: 50,
              message: `Long task detected: ${entry.duration.toFixed(2)}ms`,
              recommendation: 'Consider breaking down long tasks into smaller chunks',
              timestamp: Date.now()
            })
          }
        })
      })

      longTaskObserver.observe({ entryTypes: ['longtask'] })
      this.observers.push(longTaskObserver)
    } catch (error) {
      console.warn('Long task monitoring not supported')
    }
  }

  /**
   * 开始定期报告
   */
  private startPeriodicReporting(): void {
    this.reportInterval = setInterval(() => {
      this.generateSnapshot()
    }, 30000) // 每30秒生成一次快照
  }

  /**
   * 生成性能快照
   */
  private generateSnapshot(): void {
    // 复制当前指标
    const snapshot = { ...this.metrics }

    // 添加到历史记录
    this.metricsHistory.push(snapshot)

    // 限制历史记录大小
    if (this.metricsHistory.length > this.maxHistorySize) {
      this.metricsHistory = this.metricsHistory.slice(-this.maxHistorySize)
    }

    // 分析趋势
    this.analyzeTrends()
  }

  /**
   * 分析性能趋势
   */
  private analyzeTrends(): void {
    if (this.metricsHistory.length < 5) {
      return
    }

    const recent = this.metricsHistory.slice(-5)
    const oldest = this.metricsHistory[0]
    const latest = this.metricsHistory[this.metricsHistory.length - 1]

    // 分析 LCP 趋势
    const lcpTrend = latest.lcp - oldest.lcp
    if (lcpTrend > 200) {
      this.addAlert({
        type: 'warning',
        metric: 'lcp_trend',
        value: lcpTrend,
        threshold: 200,
        message: `LCP is increasing by ${lcpTrend.toFixed(0)}ms`,
        recommendation: 'Check for large resources or slow server responses',
        timestamp: Date.now()
      })
    }

    // 分析内存使用趋势
    if (latest.memoryUsage && oldest.memoryUsage) {
      const memoryTrend = latest.memoryUsage.usedJSHeapSize - oldest.memoryUsage.usedJSHeapSize
      if (memoryTrend > 10 * 1024 * 1024) { // 10MB
        this.addAlert({
          type: 'warning',
          metric: 'memory_trend',
          value: memoryTrend,
          threshold: 10 * 1024 * 1024,
          message: `Memory usage increased by ${(memoryTrend / 1024 / 1024).toFixed(1)}MB`,
          recommendation: 'Check for memory leaks or large data structures',
          timestamp: Date.now()
        })
      }
    }
  }

  /**
   * 检查阈值并生成告警
   */
  private checkThreshold(metric: string, value: number, threshold: number, name: string): void {
    if (value > threshold) {
      const alertType = value > threshold * 2 ? 'error' : 'warning'

      this.addAlert({
        type: alertType,
        metric,
        value,
        threshold,
        message: `${name} is ${value.toFixed(2)}ms (threshold: ${threshold}ms)`,
        recommendation: this.getRecommendation(metric, value, threshold),
        timestamp: Date.now()
      })
    }
  }

  /**
   * 获取优化建议
   */
  private getRecommendation(metric: string, value: number, threshold: number): string {
    const recommendations: Record<string, string> = {
      fcp: 'Optimize server response time and reduce render-blocking resources',
      lcp: 'Optimize images, reduce server response time, and eliminate render-blocking resources',
      fid: 'Break up long JavaScript tasks and reduce JavaScript execution time',
      cls: 'Ensure proper dimensions for images and videos, avoid inserting content above existing content',
      routeChangeTime: 'Implement route-based code splitting and lazy loading',
      memoryUsage: 'Check for memory leaks and optimize data structures'
    }

    return recommendations[metric] || 'Investigate performance bottlenecks'
  }

  /**
   * 添加告警
   */
  private addAlert(alert: PerformanceAlert): void {
    this.alerts.push(alert)

    // 限制告警数量
    if (this.alerts.length > 100) {
      this.alerts = this.alerts.slice(-100)
    }

    // 记录到控制台
    const emoji = alert.type === 'error' ? '❌' : alert.type === 'warning' ? '⚠️' : 'ℹ️'
    console.log(`${emoji} ${alert.message}`)
  }

  /**
   * 手动测量性能
   */
  measurePerformance(name: string, fn: () => void | Promise<void>): void {
    const startTime = performance.now()
    const startMark = `${name}-start`
    const endMark = `${name}-end`

    performance.mark(startMark)

    const finish = () => {
      performance.mark(endMark)
      performance.measure(name, startMark, endMark)

      const measure = performance.getEntriesByName(name, 'measure').pop()
      if (measure) {
        console.log(`⏱️ ${name}: ${measure.duration.toFixed(2)}ms`)
      }
    }

    const result = fn()

    if (result instanceof Promise) {
      result.then(finish).catch(finish)
    } else {
      finish()
    }
  }

  /**
   * 生成性能报告
   */
  generateReport(): {
    metrics: PerformanceMetrics
    alerts: PerformanceAlert[]
    score: number
    suggestions: OptimizationSuggestion[]
    grade: 'A' | 'B' | 'C' | 'D' | 'F'
  } {
    const score = this.calculatePerformanceScore()
    const grade = this.getPerformanceGrade(score)
    const suggestions = this.generateOptimizationSuggestions()

    return {
      metrics: this.metrics,
      alerts: this.alerts,
      score,
      suggestions,
      grade
    }
  }

  /**
   * 计算性能分数
   */
  private calculatePerformanceScore(): number {
    const weights = {
      fcp: 0.2,
      lcp: 0.25,
      fid: 0.2,
      cls: 0.15,
      routeChangeTime: 0.1,
      resourceCount: 0.1
    }

    const scores = {
      fcp: Math.max(0, 100 - (this.metrics.fcp - 1000) / 20),
      lcp: Math.max(0, 100 - (this.metrics.lcp - 2000) / 30),
      fid: Math.max(0, 100 - (this.metrics.fid - 100) / 2),
      cls: Math.max(0, 100 - this.metrics.cls * 1000),
      routeChangeTime: Math.max(0, 100 - (this.metrics.routeChangeTime - 200) / 5),
      resourceCount: Math.max(0, 100 - this.metrics.resourceCount / 2)
    }

    return Object.entries(weights).reduce((total, [metric, weight]) => {
      return total + (scores[metric as keyof typeof scores] || 0) * weight
    }, 0)
  }

  /**
   * 获取性能等级
   */
  private getPerformanceGrade(score: number): 'A' | 'B' | 'C' | 'D' | 'F' {
    if (score >= 90) return 'A'
    if (score >= 80) return 'B'
    if (score >= 70) return 'C'
    if (score >= 60) return 'D'
    return 'F'
  }

  /**
   * 生成优化建议
   */
  private generateOptimizationSuggestions(): OptimizationSuggestion[] {
    const suggestions: OptimizationSuggestion[] = []

    // 基于 FCP 的建议
    if (this.metrics.fcp > 1800) {
      suggestions.push({
        category: 'general',
        title: 'Improve First Contentful Paint',
        description: 'Reduce server response time and eliminate render-blocking resources',
        impact: 'high',
        effort: 'medium',
        expectedImprovement: '30-50% faster FCP',
        implementation: 'Enable resource hints, optimize critical CSS, reduce server redirects'
      })
    }

    // 基于 LCP 的建议
    if (this.metrics.lcp > 2500) {
      suggestions.push({
        category: 'image',
        title: 'Optimize Largest Contentful Paint',
        description: 'The largest content element is taking too long to load',
        impact: 'high',
        effort: 'medium',
        expectedImprovement: '20-40% faster LCP',
        implementation: 'Compress images, use modern formats, implement lazy loading'
      })
    }

    // 基于资源加载的建议
    if (this.metrics.slowResources.length > 0) {
      suggestions.push({
        category: 'resource',
        title: 'Optimize Slow Resources',
        description: `Found ${this.metrics.slowResources.length} slow-loading resources`,
        impact: 'medium',
        effort: 'low',
        expectedImprovement: '15-25% faster page load',
        implementation: 'Enable compression, use CDNs, optimize API responses'
      })
    }

    // 基于内存使用的建议
    if (this.metrics.memoryUsage) {
      const memoryUsageRatio = this.metrics.memoryUsage.usedJSHeapSize / this.metrics.memoryUsage.jsHeapSizeLimit
      if (memoryUsageRatio > 0.7) {
        suggestions.push({
          category: 'component',
          title: 'Reduce Memory Usage',
          description: 'High memory usage may cause performance issues',
          impact: 'medium',
          effort: 'medium',
          expectedImprovement: 'Better performance on low-end devices',
          implementation: 'Implement proper cleanup, use object pooling, optimize data structures'
        })
      }
    }

    // 基于路由变化的建议
    if (this.metrics.routeChangeTime > 300) {
      suggestions.push({
        category: 'route',
        title: 'Optimize Route Changes',
        description: 'Route transitions are taking longer than expected',
        impact: 'medium',
        effort: 'medium',
        expectedImprovement: '40-60% faster navigation',
        implementation: 'Implement route-based code splitting, add skeleton screens, prefetch routes'
      })
    }

    return suggestions
  }

  /**
   * 导出性能数据
   */
  exportData(): string {
    return JSON.stringify({
      metrics: this.metrics,
      alerts: this.alerts,
      history: this.metricsHistory,
      report: this.generateReport()
    }, null, 2)
  }

  /**
   * 清除数据
   */
  clearData(): void {
    this.metrics = this.initializeMetrics()
    this.alerts = []
    this.metricsHistory = []
    console.log('🧹 Performance data cleared')
  }
}

export default PerformanceMonitor
export type { PerformanceMetrics, PerformanceAlert, OptimizationSuggestion }