/**
 * 简化的性能报告工具
 */

interface SimplePerformanceReport {
  timestamp: string
  pageLoadTime: number
  routeChangeTime: number
  memoryUsage?: {
    used: number
    total: number
  }
  recommendations: string[]
}

class SimpleReport {
  /**
   * 生成性能报告
   */
  generateReport(): SimplePerformanceReport {
    const now = new Date()
    const navigationEntries = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming

    const pageLoadTime = navigationEntries
      ? navigationEntries.loadEventEnd - navigationEntries.fetchStart
      : 0

    const routeChangeTime = this.getAverageRouteChangeTime()

    const memoryUsage = (performance as any).memory ? {
      used: Math.round((performance as any).memory.usedJSHeapSize / 1024 / 1024),
      total: Math.round((performance as any).memory.totalJSHeapSize / 1024 / 1024)
    } : undefined

    const recommendations = this.generateRecommendations(pageLoadTime, memoryUsage)

    return {
      timestamp: now.toISOString(),
      pageLoadTime,
      routeChangeTime,
      memoryUsage,
      recommendations
    }
  }

  /**
   * 获取平均路由切换时间
   */
  private getAverageRouteChangeTime(): number {
    const measures = performance.getEntriesByType('measure')
    const routeMeasures = measures.filter(m =>
      m.name && m.name.toString().includes('route-change')
    )

    if (routeMeasures.length === 0) return 0

    const totalTime = routeMeasures.reduce((sum, m) => sum + m.duration, 0)
    return Math.round(totalTime / routeMeasures.length)
  }

  /**
   * 生成优化建议
   */
  private generateRecommendations(pageLoadTime: number, memoryUsage?: any): string[] {
    const recommendations: string[] = []

    if (pageLoadTime > 3000) {
      recommendations.push('页面加载时间过长，建议优化首屏资源加载')
    } else if (pageLoadTime > 1500) {
      recommendations.push('页面加载时间可以进一步优化')
    }

    if (memoryUsage && memoryUsage.used > 100) {
      recommendations.push('内存使用较高，建议检查是否有内存泄漏')
    }

    if (recommendations.length === 0) {
      recommendations.push('性能表现良好，继续保持！')
    }

    return recommendations
  }

  /**
   * 打印性能报告到控制台
   */
  printReport(): void {
    const report = this.generateReport()

    console.log('\n📊 ===== 性能优化报告 =====')
    console.log(`⏰ 页面加载时间: ${report.pageLoadTime}ms`)
    console.log(`🔄 平均路由切换: ${report.routeChangeTime}ms`)

    if (report.memoryUsage) {
      console.log(`💾 内存使用: ${report.memoryUsage.used}MB`)
    }

    console.log('\n💡 优化建议:')
    report.recommendations.forEach((rec, index) => {
      console.log(`   ${index + 1}. ${rec}`)
    })

    console.log(`\n📅 报告时间: ${report.timestamp}`)
    console.log('========================\n')
  }

  /**
   * 导出性能报告
   */
  exportReport(): string {
    const report = this.generateReport()
    return JSON.stringify(report, null, 2)
  }
}

export default SimpleReport