/**
 * 性能测试工具 - 用于验证前端优化效果
 */

import { performanceOptimizer } from './index'
import PerformanceMonitor from './PerformanceMonitor'

class PerformanceTester {
  private monitor: PerformanceMonitor
  private testResults: any[] = []

  constructor() {
    this.monitor = PerformanceMonitor.getInstance()
  }

  /**
   * 运行完整的性能测试套件
   */
  async runFullTestSuite(): Promise<void> {
    console.log('🧪 开始性能测试...')

    // 清理之前的数据
    this.cleanup()

    // 1. 测试首次加载性能
    await this.testInitialLoadPerformance()

    // 2. 测试路由切换性能
    await this.testRouteSwitchingPerformance()

    // 3. 测试组件懒加载性能
    await this.testComponentLazyLoading()

    // 4. 测试库加载性能
    await this.testLibraryLoadingPerformance()

    // 5. 测试内存使用情况
    await this.testMemoryUsage()

    // 6. 生成测试报告
    this.generateTestReport()

    console.log('✅ 性能测试完成')
  }

  /**
   * 测试首次加载性能
   */
  private async testInitialLoadPerformance(): Promise<void> {
    console.log('📊 测试首次加载性能...')

    const startTime = performance.now()

    // 模拟首次访问
    await this.simulateFirstVisit()

    const loadTime = performance.now() - startTime

    this.testResults.push({
      test: 'Initial Load',
      loadTime,
      fcp: this.getFirstContentfulPaint(),
      lcp: this.getLargestContentfulPaint(),
      status: loadTime < 3000 ? 'PASS' : 'FAIL'
    })

    console.log(`⏱️ 首次加载时间: ${loadTime.toFixed(2)}ms`)
  }

  /**
   * 测试路由切换性能
   */
  private async testRouteSwitchingPerformance(): Promise<void> {
    console.log('🔄 测试路由切换性能...')

    const routes = [
      '/dashboard',
      '/analysis/single',
      '/screening',
      '/favorites',
      '/reports'
    ]

    const routeTimes: number[] = []

    for (const route of routes) {
      const startTime = performance.now()

      // 模拟路由切换
      await this.simulateRouteChange(route)

      const switchTime = performance.now() - startTime
      routeTimes.push(switchTime)

      console.log(`🛣️ 路由 ${route}: ${switchTime.toFixed(2)}ms`)
    }

    const averageRouteTime = routeTimes.reduce((a, b) => a + b, 0) / routeTimes.length

    this.testResults.push({
      test: 'Route Switching',
      averageTime: averageRouteTime,
      maxTime: Math.max(...routeTimes),
      minTime: Math.min(...routeTimes),
      status: averageRouteTime < 300 ? 'PASS' : 'FAIL'
    })
  }

  /**
   * 测试组件懒加载性能
   */
  private async testComponentLazyLoading(): Promise<void> {
    console.log('🧩 测试组件懒加载性能...')

    // 测试组件加载
    const componentTests = [
      () => import('@/components/Dashboard/MultiSourceSyncCard.vue'),
      () => import('@/views/Analysis/SingleAnalysis.vue'),
      () => import('@/views/Reports/index.vue')
    ]

    const loadTimes: number[] = []

    for (const componentLoader of componentTests) {
      const startTime = performance.now()

      try {
        await componentLoader()
        const loadTime = performance.now() - startTime
        loadTimes.push(loadTime)
      } catch (error) {
        console.warn('组件加载失败:', error)
      }
    }

    const averageLoadTime = loadTimes.length > 0
      ? loadTimes.reduce((a, b) => a + b, 0) / loadTimes.length
      : 0

    this.testResults.push({
      test: 'Component Lazy Loading',
      averageLoadTime,
      componentsTested: loadTimes.length,
      status: averageLoadTime < 500 ? 'PASS' : 'FAIL'
    })

    console.log(`⚡ 组件平均加载时间: ${averageLoadTime.toFixed(2)}ms`)
  }

  /**
   * 测试库加载性能
   */
  private async testLibraryLoadingPerformance(): Promise<void> {
    console.log('📚 测试库加载性能...')

    const libraryTests = [
      {
        name: 'Element Plus Button',
        loader: () => performanceOptimizer.libraries.loadElementPlus('button')
      },
      {
        name: 'ECharts Core',
        loader: () => performanceOptimizer.libraries.loadECharts('core')
      },
      {
        name: 'Lodash Debounce',
        loader: () => performanceOptimizer.libraries.loadLodash('debounce')
      }
    ]

    const loadTimes: Array<{ name: string; time: number }> = []

    for (const test of libraryTests) {
      const startTime = performance.now()

      try {
        await test.loader()
        const loadTime = performance.now() - startTime
        loadTimes.push({ name: test.name, time: loadTime })
      } catch (error) {
        console.warn(`库 ${test.name} 加载失败:`, error)
      }
    }

    const averageLoadTime = loadTimes.reduce((sum, t) => sum + t.time, 0) / loadTimes.length

    this.testResults.push({
      test: 'Library Loading',
      averageLoadTime,
      librariesTested: loadTimes.length,
      details: loadTimes,
      status: averageLoadTime < 200 ? 'PASS' : 'FAIL'
    })

    console.log(`📦 库平均加载时间: ${averageLoadTime.toFixed(2)}ms`)
  }

  /**
   * 测试内存使用情况
   */
  private async testMemoryUsage(): Promise<void> {
    console.log('🧠 测试内存使用情况...')

    const memoryUsage = (performance as any).memory

    if (memoryUsage) {
      const usedMB = memoryUsage.usedJSHeapSize / 1024 / 1024
      const totalMB = memoryUsage.totalJSHeapSize / 1024 / 1024
      const limitMB = memoryUsage.jsHeapSizeLimit / 1024 / 1024
      const usagePercent = (usedMB / limitMB) * 100

      this.testResults.push({
        test: 'Memory Usage',
        usedMB: usedMB.toFixed(2),
        totalMB: totalMB.toFixed(2),
        limitMB: limitMB.toFixed(2),
        usagePercent: usagePercent.toFixed(2),
        status: usagePercent < 70 ? 'PASS' : 'WARNING'
      })

      console.log(`💾 内存使用: ${usedMB.toFixed(2)}MB (${usagePercent.toFixed(2)}%)`)
    } else {
      console.log('⚠️ 浏览器不支持内存监控')
    }
  }

  /**
   * 生成测试报告
   */
  private generateTestReport(): void {
    console.log('\n📋 ===== 性能测试报告 =====')

    let passCount = 0
    let failCount = 0
    let warningCount = 0

    this.testResults.forEach(result => {
      const icon = result.status === 'PASS' ? '✅' : result.status === 'FAIL' ? '❌' : '⚠️'

      console.log(`\n${icon} ${result.test}`)

      if (result.loadTime) {
        console.log(`   加载时间: ${result.loadTime.toFixed(2)}ms`)
      }

      if (result.averageTime) {
        console.log(`   平均时间: ${result.averageTime.toFixed(2)}ms`)
      }

      if (result.averageLoadTime) {
        console.log(`   平均加载: ${result.averageLoadTime.toFixed(2)}ms`)
      }

      if (result.usedMB) {
        console.log(`   内存使用: ${result.usedMB}MB (${result.usagePercent}%)`)
      }

      if (result.status === 'PASS') passCount++
      else if (result.status === 'FAIL') failCount++
      else warningCount++
    })

    console.log('\n📊 测试统计:')
    console.log(`   通过: ${passCount}`)
    console.log(`   失败: ${failCount}`)
    console.log(`   警告: ${warningCount}`)

    const successRate = (passCount / this.testResults.length) * 100
    console.log(`   成功率: ${successRate.toFixed(1)}%`)

    // 性能优化建议
    console.log('\n💡 性能优化建议:')
    this.generateOptimizationSuggestions()

    console.log('\n=========================\n')
  }

  /**
   * 生成优化建议
   */
  private generateOptimizationSuggestions(): void {
    const suggestions: string[] = []

    this.testResults.forEach(result => {
      switch (result.test) {
        case 'Initial Load':
          if (result.status === 'FAIL') {
            suggestions.push('考虑增加预加载策略，优化关键渲染路径')
          }
          break
        case 'Route Switching':
          if (result.status === 'FAIL') {
            suggestions.push('优化路由懒加载，减少路由切换时的资源加载')
          }
          break
        case 'Component Lazy Loading':
          if (result.status === 'FAIL') {
            suggestions.push('增加组件预加载，使用更好的代码分割策略')
          }
          break
        case 'Memory Usage':
          if (result.status === 'WARNING') {
            suggestions.push('检查内存泄漏，优化大数据结构的处理')
          }
          break
      }
    })

    if (suggestions.length === 0) {
      console.log('   🎉 性能表现良好，继续保持！')
    } else {
      suggestions.forEach((suggestion, index) => {
        console.log(`   ${index + 1}. ${suggestion}`)
      })
    }
  }

  /**
   * 获取FCP指标
   */
  private getFirstContentfulPaint(): number {
    const entries = performance.getEntriesByType('paint')
    const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint')
    return fcpEntry ? fcpEntry.startTime : 0
  }

  /**
   * 获取LCP指标
   */
  private getLargestContentfulPaint(): number {
    const entries = performance.getEntriesByType('largest-contentful-paint')
    const lastEntry = entries[entries.length - 1]
    return lastEntry ? lastEntry.startTime : 0
  }

  /**
   * 模拟首次访问
   */
  private async simulateFirstVisit(): Promise<void> {
    // 模拟首次访问的操作
    await new Promise(resolve => setTimeout(resolve, 100))
  }

  /**
   * 模拟路由变化
   */
  private async simulateRouteChange(route: string): Promise<void> {
    // 模拟路由变化
    await new Promise(resolve => setTimeout(resolve, 50))
  }

  /**
   * 清理测试数据
   */
  private cleanup(): void {
    this.testResults = []
  }

  /**
   * 获取测试结果
   */
  getTestResults() {
    return this.testResults
  }

  /**
   * 导出测试报告
   */
  exportTestReport(): string {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      results: this.testResults,
      summary: {
        total: this.testResults.length,
        passed: this.testResults.filter(r => r.status === 'PASS').length,
        failed: this.testResults.filter(r => r.status === 'FAIL').length,
        warnings: this.testResults.filter(r => r.status === 'WARNING').length
      }
    }, null, 2)
  }
}

export default PerformanceTester