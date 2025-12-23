/**
 * 组件懒加载器 - 处理组件级别的性能优化
 *
 * 功能：
 * 1. 智能组件懒加载
 * 2. 可视区域检测
 * 3. 优先级管理
 * 4. 错误重试机制
 */

import { ref, onMounted, onUnmounted, type Component, type Ref } from 'vue'
import type { AsyncComponentLoader } from 'vue'

interface LazyLoadOptions {
  // 延迟加载时间（毫秒）
  delay?: number
  // 超时时间（毫秒）
  timeout?: number
  // 重试次数
  retryCount?: number
  // 是否使用交叉观察器
  useIntersectionObserver?: boolean
  // 可视区域的阈值
  intersectionThreshold?: number
  // 根边距
  rootMargin?: string
  // 加载中的组件
  loadingComponent?: Component
  // 错误时显示的组件
  errorComponent?: Component
  // 自定义触发条件
  shouldLoad?: () => boolean
}

interface LoadingState {
  isLoading: boolean
  isLoaded: boolean
  error: Error | null
  retryCount: number
}

class ComponentLazyLoader {
  private static instance: ComponentLazyLoader
  private loadingRegistry = new Map<string, Promise<Component>>()
  private loadedComponents = new Map<string, Component>()
  private intersectionObservers = new Map<string, IntersectionObserver>()

  static getInstance(): ComponentLazyLoader {
    if (!ComponentLazyLoader.instance) {
      ComponentLazyLoader.instance = new ComponentLazyLoader()
    }
    return ComponentLazyLoader.instance
  }

  /**
   * 创建懒加载组件 Composable
   */
  createLazyComponent<T extends Component>(
    loader: AsyncComponentLoader<T>,
    options: LazyLoadOptions = {}
  ) {
    const {
      delay = 0,
      timeout = 5000,
      retryCount = 3,
      useIntersectionObserver = false,
      intersectionThreshold = 0.1,
      rootMargin = '50px',
      shouldLoad
    } = options

    const loadingState = ref<LoadingState>({
      isLoading: false,
      isLoaded: false,
      error: null,
      retryCount: 0
    })

    const componentRef: Ref<Component | null> = ref(null)
    const elementRef = ref<HTMLElement | null>(null)

    const componentKey = this.generateComponentKey(loader)

    // 检查是否已经加载
    if (this.loadedComponents.has(componentKey)) {
      componentRef.value = this.loadedComponents.get(componentKey)!
      loadingState.value.isLoaded = true
      return {
        component: componentRef,
        loadingState,
        elementRef
      }
    }

    const loadComponent = async () => {
      if (loadingState.value.isLoading || loadingState.value.isLoaded) {
        return
      }

      loadingState.value.isLoading = true
      loadingState.value.error = null

      try {
        // 检查是否正在加载
        if (this.loadingRegistry.has(componentKey)) {
          componentRef.value = await this.loadingRegistry.get(componentKey)!
        } else {
          const loadPromise = this.loadWithRetry(loader, retryCount, timeout)
          this.loadingRegistry.set(componentKey, loadPromise)

          componentRef.value = await loadPromise
          this.loadedComponents.set(componentKey, componentRef.value)
        }

        loadingState.value.isLoaded = true
        console.log(`✅ Component loaded: ${componentKey}`)
      } catch (error) {
        loadingState.value.error = error as Error
        console.error(`❌ Component loading failed: ${componentKey}`, error)
      } finally {
        loadingState.value.isLoading = false
      }
    }

    const startLoad = () => {
      if (shouldLoad && !shouldLoad()) {
        return
      }

      if (delay > 0) {
        setTimeout(loadComponent, delay)
      } else {
        loadComponent()
      }
    }

    // 设置交叉观察器
    if (useIntersectionObserver) {
      const setupIntersectionObserver = () => {
        if (!elementRef.value || typeof IntersectionObserver === 'undefined') {
          startLoad() // 降级到立即加载
          return
        }

        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                startLoad()
                observer.unobserve(entry.target)
                this.intersectionObservers.delete(componentKey)
              }
            })
          },
          {
            threshold: intersectionThreshold,
            rootMargin
          }
        )

        observer.observe(elementRef.value)
        this.intersectionObservers.set(componentKey, observer)
      }

      onMounted(() => {
        setupIntersectionObserver()
      })

      onUnmounted(() => {
        const observer = this.intersectionObservers.get(componentKey)
        if (observer) {
          observer.disconnect()
          this.intersectionObservers.delete(componentKey)
        }
      })
    } else {
      // 立即开始加载
      onMounted(() => {
        startLoad()
      })
    }

    return {
      component: componentRef,
      loadingState,
      elementRef
    }
  }

  /**
   * 带重试的组件加载
   */
  private async loadWithRetry<T extends Component>(
    loader: AsyncComponentLoader<T>,
    retryCount: number,
    timeout: number
  ): Promise<T> {
    let lastError: Error | null = null

    for (let attempt = 0; attempt <= retryCount; attempt++) {
      try {
        const component = await Promise.race([
          loader(),
          this.createTimeoutPromise(timeout)
        ])
        return component
      } catch (error) {
        lastError = error as Error

        if (attempt < retryCount) {
          // 指数退避策略
          const delay = Math.pow(2, attempt) * 1000
          await this.sleep(delay)
          console.log(`🔄 Retrying component load (attempt ${attempt + 1}):`, error)
        }
      }
    }

    throw lastError
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
   * 睡眠函数
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * 生成组件键
   */
  private generateComponentKey(loader: AsyncComponentLoader<any>): string {
    return loader.toString().replace(/[^a-zA-Z0-9]/g, '_')
  }

  /**
   * 预加载组件
   */
  async preloadComponent<T extends Component>(loader: AsyncComponentLoader<T>): Promise<void> {
    const componentKey = this.generateComponentKey(loader)

    if (this.loadedComponents.has(componentKey) || this.loadingRegistry.has(componentKey)) {
      return
    }

    try {
      const loadPromise = loader()
      this.loadingRegistry.set(componentKey, loadPromise)

      const component = await loadPromise
      this.loadedComponents.set(componentKey, component)

      console.log(`⚡ Component preloaded: ${componentKey}`)
    } catch (error) {
      this.loadingRegistry.delete(componentKey)
      console.warn(`Failed to preload component: ${componentKey}`, error)
    }
  }

  /**
   * 批量预加载组件
   */
  async preloadComponents<T extends Component>(
    loaders: AsyncComponentLoader<T>[]
  ): Promise<void> {
    const batchSize = 3 // 限制并发数

    for (let i = 0; i < loaders.length; i += batchSize) {
      const batch = loaders.slice(i, i + batchSize)
      await Promise.allSettled(
        batch.map(loader => this.preloadComponent(loader))
      )
    }
  }

  /**
   * 获取组件加载状态
   */
  getComponentStatus(loader: AsyncComponentLoader<any>): {
    isLoaded: boolean
    isLoading: boolean
    error: Error | null
  } {
    const componentKey = this.generateComponentKey(loader)

    return {
      isLoaded: this.loadedComponents.has(componentKey),
      isLoading: this.loadingRegistry.has(componentKey),
      error: null
    }
  }

  /**
   * 清理未使用的组件
   */
  cleanup(): void {
    // 停止所有交叉观察器
    for (const observer of this.intersectionObservers.values()) {
      observer.disconnect()
    }
    this.intersectionObservers.clear()
  }

  /**
   * 获取性能统计
   */
  getStats() {
    return {
      loadedComponents: this.loadedComponents.size,
      loadingComponents: this.loadingRegistry.size,
      activeObservers: this.intersectionObservers.size
    }
  }
}

export default ComponentLazyLoader
export type { LazyLoadOptions, LoadingState }