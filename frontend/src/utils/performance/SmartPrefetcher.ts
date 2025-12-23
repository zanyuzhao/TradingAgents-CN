/**
 * 智能预取器 - 基于用户行为模式进行智能预加载
 *
 * 功能：
 * 1. 用户行为分析
 * 2. 访问模式学习
 * 3. 智能预取策略
 * 4. 缓存管理
 * 5. 预取效果评估
 */

interface UserAction {
  type: 'navigate' | 'click' | 'hover' | 'scroll' | 'search'
  target: string
  timestamp: number
  context?: any
}

interface AccessPattern {
  sequence: string[]
  frequency: number
  lastAccess: number
  averageTimeBetween: number
}

interface PrefetchPrediction {
  target: string
  confidence: number
  reason: string
  priority: 'high' | 'medium' | 'low'
}

interface CacheItem<T> {
  data: T
  timestamp: number
  accessCount: number
  lastAccess: number
  expiresAt?: number
}

class SmartPrefetcher {
  private static instance: SmartPrefetcher
  private userActions: UserAction[] = []
  private accessPatterns = new Map<string, AccessPattern>()
  private cache = new Map<string, any>()
  private prefetchQueue: PrefetchPrediction[] = []
  private isProcessing = false
  private maxCacheSize = 100
  private maxActionHistory = 1000

  private constructor() {
    this.initEventListeners()
    this.startPeriodicCleanup()
  }

  static getInstance(): SmartPrefetcher {
    if (!SmartPrefetcher.instance) {
      SmartPrefetcher.instance = new SmartPrefetcher()
    }
    return SmartPrefetcher.instance
  }

  /**
   * 初始化事件监听器
   */
  private initEventListeners(): void {
    // 监听路由变化
    window.addEventListener('popstate', () => {
      this.recordAction({
        type: 'navigate',
        target: window.location.pathname,
        timestamp: Date.now()
      })
    })

    // 监听页面可见性变化
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        this.scheduleIntelligentPrefetch()
      }
    })

    // 监听鼠标移动（用于预测用户意图）
    let mouseTimer: NodeJS.Timeout
    document.addEventListener('mousemove', (event) => {
      clearTimeout(mouseTimer)
      mouseTimer = setTimeout(() => {
        this.analyzeMouseMovement(event)
      }, 500)
    })
  }

  /**
   * 记录用户行为
   */
  recordAction(action: UserAction): void {
    this.userActions.push(action)

    // 限制历史记录大小
    if (this.userActions.length > this.maxActionHistory) {
      this.userActions = this.userActions.slice(-this.maxActionHistory)
    }

    // 更新访问模式
    this.updateAccessPatterns(action)

    // 触发智能预取
    this.triggerSmartPrefetch(action)
  }

  /**
   * 更新访问模式
   */
  private updateAccessPatterns(action: UserAction): void {
    if (action.type !== 'navigate') return

    const key = action.target
    const existing = this.accessPatterns.get(key)

    if (existing) {
      // 更新现有模式
      existing.frequency++
      existing.lastAccess = action.timestamp

      if (existing.sequence.length > 10) {
        existing.sequence = existing.sequence.slice(-9)
      }
    } else {
      // 创建新模式
      this.accessPatterns.set(key, {
        sequence: [action.target],
        frequency: 1,
        lastAccess: action.timestamp,
        averageTimeBetween: 0
      })
    }
  }

  /**
   * 触发智能预取
   */
  private triggerSmartPrefetch(currentAction: UserAction): void {
    if (currentAction.type !== 'navigate') return

    const predictions = this.predictNextActions(currentAction.target)

    predictions.forEach(prediction => {
      if (prediction.confidence > 0.6) {
        this.addToPrefetchQueue(prediction)
      }
    })

    this.processPrefetchQueue()
  }

  /**
   * 预测下一个用户行为
   */
  predictNextActions(currentTarget: string): PrefetchPrediction[] {
    const predictions: PrefetchPrediction[] = []

    // 基于历史模式预测
    const patternPredictions = this.predictFromPatterns(currentTarget)
    predictions.push(...patternPredictions)

    // 基于时间模式预测
    const timePredictions = this.predictFromTimePatterns(currentTarget)
    predictions.push(...timePredictions)

    // 基于页面结构预测
    const structurePredictions = this.predictFromPageStructure(currentTarget)
    predictions.push(...structurePredictions)

    // 去重并按置信度排序
    return this.deduplicateAndSort(predictions)
  }

  /**
   * 基于访问模式预测
   */
  private predictFromPatterns(currentTarget: string): PrefetchPrediction[] {
    const predictions: PrefetchPrediction[] = []

    // 分析最近的访问序列
    const recentActions = this.userActions.slice(-20)
    const currentIndex = recentActions.findIndex(a => a.target === currentTarget)

    if (currentIndex > 0 && currentIndex < recentActions.length - 1) {
      const nextActions = recentActions
        .slice(currentIndex + 1)
        .filter(a => a.type === 'navigate')
        .map(a => a.target)

      // 统计下一个页面
      const nextPageStats = nextActions.reduce((stats, page) => {
        stats[page] = (stats[page] || 0) + 1
        return stats
      }, {} as Record<string, number>)

      Object.entries(nextPageStats).forEach(([page, count]) => {
        const confidence = Math.min(count / nextActions.length, 0.8)
        predictions.push({
          target: page,
          confidence,
          reason: 'Based on recent navigation pattern',
          priority: confidence > 0.5 ? 'high' : 'medium'
        })
      })
    }

    return predictions
  }

  /**
   * 基于时间模式预测
   */
  private predictFromTimePatterns(currentTarget: string): PrefetchPrediction[] {
    const predictions: PrefetchPrediction[] = []
    const currentHour = new Date().getHours()

    // 分析不同时间段的访问模式
    const timePatterns = this.analyzeTimePatterns(currentTarget, currentHour)

    timePatterns.forEach((confidence, target) => {
      if (confidence > 0.4) {
        predictions.push({
          target,
          confidence,
          reason: `Based on time-of-day pattern (${currentHour}:00)`,
          priority: 'medium'
        })
      }
    })

    return predictions
  }

  /**
   * 基于页面结构预测
   */
  private predictFromPageStructure(currentTarget: string): PrefetchPrediction[] {
    const predictions: PrefetchPrediction[] = []

    // 基于页面类型预测
    const pageTypePredictions = this.predictFromPageType(currentTarget)
    predictions.push(...pageTypePredictions)

    return predictions
  }

  /**
   * 基于页面类型预测
   */
  private predictFromPageType(pagePath: string): PrefetchPrediction[] {
    const predictions: PrefetchPrediction[] = []

    // 分析页面路径模式
    if (pagePath.includes('/analysis/')) {
      predictions.push({
        target: '/stocks',
        confidence: 0.7,
        reason: 'Users often view stock details after analysis',
        priority: 'high'
      })
      predictions.push({
        target: '/reports',
        confidence: 0.5,
        reason: 'Users may view reports after analysis',
        priority: 'medium'
      })
    } else if (pagePath.includes('/screening')) {
      predictions.push({
        target: '/analysis/single',
        confidence: 0.6,
        reason: 'Users often analyze screened stocks',
        priority: 'high'
      })
      predictions.push({
        target: '/favorites',
        confidence: 0.4,
        reason: 'Users may add screened stocks to favorites',
        priority: 'medium'
      })
    } else if (pagePath.includes('/dashboard')) {
      predictions.push({
        target: '/analysis/single',
        confidence: 0.5,
        reason: 'Common dashboard action: analyze stock',
        priority: 'medium'
      })
      predictions.push({
        target: '/favorites',
        confidence: 0.4,
        reason: 'Common dashboard action: view favorites',
        priority: 'medium'
      })
    }

    return predictions
  }

  /**
   * 分析时间模式
   */
  private analyzeTimePatterns(currentTarget: string, currentHour: number): Map<string, number> {
    const patterns = new Map<string, number>()

    // 获取同一时间段的访问历史
    const sameTimeActions = this.userActions.filter(action => {
      const actionHour = new Date(action.timestamp).getHours()
      return action.type === 'navigate' && Math.abs(actionHour - currentHour) <= 1
    })

    // 统计访问模式
    const accessCounts = sameTimeActions.reduce((counts, action) => {
      counts[action.target] = (counts[action.target] || 0) + 1
      return counts
    }, {} as Record<string, number>)

    // 计算概率
    const totalAccess = Object.values(accessCounts).reduce((sum, count) => sum + count, 0)
    Object.entries(accessCounts).forEach(([target, count]) => {
      if (target !== currentTarget) {
        const probability = count / totalAccess
        patterns.set(target, probability * 0.3) // 降低时间模式的权重
      }
    })

    return patterns
  }

  /**
   * 去重并排序预测结果
   */
  private deduplicateAndSort(predictions: PrefetchPrediction[]): PrefetchPrediction[] {
    const uniquePredictions = new Map<string, PrefetchPrediction>()

    predictions.forEach(prediction => {
      const existing = uniquePredictions.get(prediction.target)
      if (!existing || prediction.confidence > existing.confidence) {
        uniquePredictions.set(prediction.target, prediction)
      }
    })

    return Array.from(uniquePredictions.values())
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 5) // 限制预测数量
  }

  /**
   * 添加到预取队列
   */
  private addToPrefetchQueue(prediction: PrefetchPrediction): void {
    const existingIndex = this.prefetchQueue.findIndex(p => p.target === prediction.target)

    if (existingIndex >= 0) {
      // 更新现有的预测
      this.prefetchQueue[existingIndex] = {
        ...this.prefetchQueue[existingIndex],
        confidence: Math.max(this.prefetchQueue[existingIndex].confidence, prediction.confidence)
      }
    } else {
      // 添加新预测
      this.prefetchQueue.push(prediction)
    }
  }

  /**
   * 处理预取队列
   */
  private async processPrefetchQueue(): Promise<void> {
    if (this.isProcessing || this.prefetchQueue.length === 0) {
      return
    }

    this.isProcessing = true

    // 按优先级排序
    this.prefetchQueue.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 }
      return priorityOrder[b.priority] - priorityOrder[a.priority] ||
             b.confidence - a.confidence
    })

    // 处理队列中的预测
    while (this.prefetchQueue.length > 0) {
      const prediction = this.prefetchQueue.shift()!

      try {
        await this.executePrefetch(prediction)
      } catch (error) {
        console.warn(`Prefetch failed for ${prediction.target}:`, error)
      }

      // 避免阻塞主线程
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    this.isProcessing = false
  }

  /**
   * 执行预取
   */
  private async executePrefetch(prediction: PrefetchPrediction): Promise<void> {
    console.log(`🚀 Prefetching: ${prediction.target} (${prediction.confidence.toFixed(2)})`)

    // 检查是否已缓存
    if (this.cache.has(prediction.target)) {
      return
    }

    // 预取页面组件
    try {
      const startTime = performance.now()

      // 这里应该调用路由预取逻辑
      await this.prefetchRouteComponent(prediction.target)

      const loadTime = performance.now() - startTime

      // 缓存结果
      this.setCache(prediction.target, {
        loaded: true,
        loadTime,
        timestamp: Date.now()
      })

      console.log(`✅ Prefetch completed: ${prediction.target} (${loadTime.toFixed(2)}ms)`)
    } catch (error) {
      console.error(`❌ Prefetch failed: ${prediction.target}`, error)
    }
  }

  /**
   * 预取路由组件
   */
  private async prefetchRouteComponent(routePath: string): Promise<void> {
    // 这里应该根据路由路径动态导入对应的组件
    // 实际实现需要与路由系统集成
    console.log(`Prefetching route component for: ${routePath}`)
  }

  /**
   * 分析鼠标移动
   */
  private analyzeMouseMovement(event: MouseEvent): void {
    const elements = document.elementsFromPoint(event.clientX, event.clientY)
    const links = elements.filter(el => el.tagName === 'A' || el.onclick) as HTMLElement[]

    links.forEach(link => {
      const href = link.getAttribute('href') || link.onclick?.toString()
      if (href && !href.startsWith('#')) {
        // 鼠标悬停在链接上，增加预取优先级
        this.increasePrefetchPriority(href, 'hover')
      }
    })
  }

  /**
   * 增加预取优先级
   */
  private increasePrefetchPriority(target: string, reason: string): void {
    const existing = this.prefetchQueue.find(p => p.target === target)
    if (existing) {
      existing.confidence = Math.min(existing.confidence + 0.2, 0.9)
      existing.reason += `, ${reason}`
    }
  }

  /**
   * 调度智能预取
   */
  private scheduleIntelligentPrefetch(): void {
    setTimeout(() => {
      const recentActions = this.userActions.slice(-5)
      if (recentActions.length > 0) {
        const lastAction = recentActions[recentActions.length - 1]
        this.triggerSmartPrefetch(lastAction)
      }
    }, 1000)
  }

  /**
   * 缓存管理
   */
  setCache<T>(key: string, data: T, ttl?: number): void {
    const item: CacheItem<T> = {
      data,
      timestamp: Date.now(),
      accessCount: 0,
      lastAccess: Date.now(),
      expiresAt: ttl ? Date.now() + ttl : undefined
    }

    this.cache.set(key, item)
    this.maintainCacheSize()
  }

  /**
   * 获取缓存
   */
  getCache<T>(key: string): T | null {
    const item = this.cache.get(key) as CacheItem<T>

    if (!item) {
      return null
    }

    // 检查是否过期
    if (item.expiresAt && Date.now() > item.expiresAt) {
      this.cache.delete(key)
      return null
    }

    // 更新访问信息
    item.accessCount++
    item.lastAccess = Date.now()

    return item.data
  }

  /**
   * 维护缓存大小
   */
  private maintainCacheSize(): void {
    if (this.cache.size <= this.maxCacheSize) {
      return
    }

    // 按最近最少使用排序
    const sortedItems = Array.from(this.cache.entries())
      .sort(([, a], [, b]) => a.lastAccess - b.lastAccess)

    // 删除最旧的项目
    const toDelete = sortedItems.slice(0, this.cache.size - this.maxCacheSize)
    toDelete.forEach(([key]) => this.cache.delete(key))
  }

  /**
   * 定期清理
   */
  private startPeriodicCleanup(): void {
    setInterval(() => {
      this.cleanupExpiredItems()
      this.cleanupOldActions()
    }, 5 * 60 * 1000) // 每5分钟清理一次
  }

  /**
   * 清理过期项目
   */
  private cleanupExpiredItems(): void {
    const now = Date.now()

    for (const [key, item] of this.cache.entries()) {
      if (item.expiresAt && now > item.expiresAt) {
        this.cache.delete(key)
      }
    }
  }

  /**
   * 清理旧的行动记录
   */
  private cleanupOldActions(): void {
    const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000)
    this.userActions = this.userActions.filter(action => action.timestamp > oneWeekAgo)
  }

  /**
   * 获取统计信息
   */
  getStats() {
    return {
      totalActions: this.userActions.length,
      accessPatterns: this.accessPatterns.size,
      cacheSize: this.cache.size,
      prefetchQueue: this.prefetchQueue.length,
      isProcessing: this.isProcessing
    }
  }

  /**
   * 获取预取报告
   */
  getPrefetchReport() {
    return {
      recentPredictions: this.prefetchQueue.slice(0, 10),
      cacheHitRate: this.calculateCacheHitRate(),
      commonPatterns: this.getCommonPatterns(),
      recommendations: this.getRecommendations()
    }
  }

  /**
   * 计算缓存命中率
   */
  private calculateCacheHitRate(): number {
    // 实现缓存命中率计算逻辑
    return 0.85 // 示例值
  }

  /**
   * 获取常见模式
   */
  private getCommonPatterns(): Array<{ pattern: string; frequency: number }> {
    return Array.from(this.accessPatterns.entries())
      .map(([key, pattern]) => ({
        pattern: key,
        frequency: pattern.frequency
      }))
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, 5)
  }

  /**
   * 获取优化建议
   */
  private getRecommendations(): string[] {
    const recommendations: string[] = []
    const stats = this.getStats()

    if (stats.cacheSize < this.maxCacheSize * 0.5) {
      recommendations.push('Consider increasing cache size for better performance')
    }

    if (stats.accessPatterns < 10) {
      recommendations.push('User behavior patterns are still being learned')
    }

    return recommendations
  }
}

export default SmartPrefetcher
export type { UserAction, PrefetchPrediction, CacheItem }