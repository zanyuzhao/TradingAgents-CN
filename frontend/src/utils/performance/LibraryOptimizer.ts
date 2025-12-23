/**
 * 第三方库优化器 - 处理第三方库的按需加载和优化
 *
 * 功能：
 * 1. Element Plus 按需加载
 * 2. ECharts 按需加载
 * 3. 图标库按需加载
 * 4. 工具库按需加载
 * 5. 库版本管理
 */

interface LibraryConfig {
  name: string
  version?: string
  lazy: boolean
  priority: 'critical' | 'high' | 'medium' | 'low'
  preload?: boolean
  dependencies?: string[]
}

interface LoadResult {
  library: string
  loaded: boolean
  size?: number
  loadTime?: number
  error?: Error
}

class LibraryOptimizer {
  private static instance: LibraryOptimizer
  private loadedLibraries = new Map<string, LoadResult>()
  private loadingPromises = new Map<string, Promise<any>>()
  private libraryConfigs = new Map<string, LibraryConfig>()

  private constructor() {
    this.initLibraryConfigs()
  }

  static getInstance(): LibraryOptimizer {
    if (!LibraryOptimizer.instance) {
      LibraryOptimizer.instance = new LibraryOptimizer()
    }
    return LibraryOptimizer.instance
  }

  /**
   * 初始化库配置
   */
  private initLibraryConfigs(): void {
    // Element Plus 配置
    this.libraryConfigs.set('element-plus', {
      name: 'Element Plus',
      version: '2.4.4',
      lazy: true,
      priority: 'high',
      preload: true
    })

    // ECharts 配置
    this.libraryConfigs.set('echarts', {
      name: 'ECharts',
      version: '5.4.3',
      lazy: true,
      priority: 'medium',
      dependencies: ['vue-echarts']
    })

    // Lodash 配置
    this.libraryConfigs.set('lodash-es', {
      name: 'Lodash',
      lazy: true,
      priority: 'medium'
    })

    // 其他库配置
    this.libraryConfigs.set('dayjs', {
      name: 'Day.js',
      lazy: true,
      priority: 'high'
    })

    this.libraryConfigs.set('marked', {
      name: 'Marked',
      lazy: true,
      priority: 'low'
    })

    this.libraryConfigs.set('mermaid', {
      name: 'Mermaid',
      lazy: true,
      priority: 'low'
    })
  }

  /**
   * 按需加载 Element Plus 组件
   */
  async loadElementPlusComponent(componentName: string): Promise<any> {
    const cacheKey = `element-plus-${componentName}`

    if (this.loadedLibraries.has(cacheKey)) {
      return this.loadedLibraries.get(cacheKey)!
    }

    if (this.loadingPromises.has(cacheKey)) {
      return this.loadingPromises.get(cacheKey)
    }

    const loadPromise = this.loadElementPlusComponentInternal(componentName)
    this.loadingPromises.set(cacheKey, loadPromise)

    return loadPromise
  }

  /**
   * 内部方法：加载 Element Plus 组件
   */
  private async loadElementPlusComponentInternal(componentName: string): Promise<any> {
    const startTime = performance.now()

    try {
      // 使用映射表避免动态导入问题
      const component = await this.loadElementPlusComponentByName(componentName)

      const loadTime = performance.now() - startTime
      const result: LoadResult = {
        library: `Element Plus - ${componentName}`,
        loaded: true,
        loadTime
      }

      this.loadedLibraries.set(`element-plus-${componentName}`, result)
      console.log(`📦 Element Plus component loaded: ${componentName} (${loadTime.toFixed(2)}ms)`)

      return component
    } catch (error) {
      const result: LoadResult = {
        library: `Element Plus - ${componentName}`,
        loaded: false,
        error: error as Error
      }
      this.loadedLibraries.set(`element-plus-${componentName}`, result)
      throw error
    }
  }

  /**
   * 通过名称加载 Element Plus 组件（使用静态导入映射）
   */
  private async loadElementPlusComponentByName(componentName: string): Promise<any> {
    // 静态映射表，避免 Vite 动态导入问题
    const componentMap: Record<string, () => Promise<any>> = {
      'button': () => import('element-plus/es/components/button'),
      'input': () => import('element-plus/es/components/input'),
      'form': () => import('element-plus/es/components/form'),
      'table': () => import('element-plus/es/components/table'),
      'dialog': () => import('element-plus/es/components/dialog'),
      'card': () => import('element-plus/es/components/card'),
      'select': () => import('element-plus/es/components/select'),
      'option': () => import('element-plus/es/components/option'),
      'dropdown': () => import('element-plus/es/components/dropdown'),
      'menu': () => import('element-plus/es/components/menu'),
      'pagination': () => import('element-plus/es/components/pagination'),
      'loading': () => import('element-plus/es/components/loading'),
      'message': () => import('element-plus/es/components/message'),
      'notification': () => import('element-plus/es/components/notification'),
      'tooltip': () => import('element-plus/es/components/tooltip'),
      'popover': () => import('element-plus/es/components/popover'),
      'tree': () => import('element-plus/es/components/tree')
    }

    const loader = componentMap[componentName]
    if (!loader) {
      console.warn(`Unknown Element Plus component: ${componentName}`)
      return null
    }

    return await loader()
  }

  /**
   * 按需加载 ECharts 模块
   */
  async loadEChartsModule(moduleName: string): Promise<any> {
    const cacheKey = `echarts-${moduleName}`

    if (this.loadedLibraries.has(cacheKey)) {
      return this.loadedLibraries.get(cacheKey)!
    }

    if (this.loadingPromises.has(cacheKey)) {
      return this.loadingPromises.get(cacheKey)
    }

    const loadPromise = this.loadEChartsModuleInternal(moduleName)
    this.loadingPromises.set(cacheKey, loadPromise)

    return loadPromise
  }

  /**
   * 内部方法：加载 ECharts 模块
   */
  private async loadEChartsModuleInternal(moduleName: string): Promise<any> {
    const startTime = performance.now()

    try {
      let module

      switch (moduleName) {
        case 'core':
          module = await import('echarts/core')
          break
        case 'charts':
          // 加载常用图表类型
          const [
            LineChart,
            BarChart,
            PieChart,
            ScatterChart
          ] = await Promise.all([
            import('echarts/charts/LineChart'),
            import('echarts/charts/BarChart'),
            import('echarts/charts/PieChart'),
            import('echarts/charts/ScatterChart')
          ])
          module = { LineChart, BarChart, PieChart, ScatterChart }
          break
        case 'components':
          // 加载常用组件
          const [
            GridComponent,
            TooltipComponent,
            LegendComponent,
            TitleComponent
          ] = await Promise.all([
            import('echarts/components/GridComponent'),
            import('echarts/components/TooltipComponent'),
            import('echarts/components/LegendComponent'),
            import('echarts/components/TitleComponent')
          ])
          module = { GridComponent, TooltipComponent, LegendComponent, TitleComponent }
          break
        default:
          throw new Error(`Unknown ECharts module: ${moduleName}`)
      }

      const loadTime = performance.now() - startTime
      const result: LoadResult = {
        library: `ECharts - ${moduleName}`,
        loaded: true,
        loadTime
      }

      this.loadedLibraries.set(`echarts-${moduleName}`, result)
      console.log(`📊 ECharts module loaded: ${moduleName} (${loadTime.toFixed(2)}ms)`)

      return module
    } catch (error) {
      const result: LoadResult = {
        library: `ECharts - ${moduleName}`,
        loaded: false,
        error: error as Error
      }
      this.loadedLibraries.set(`echarts-${moduleName}`, result)
      throw error
    }
  }

  /**
   * 按需加载 Lodash 函数
   */
  async loadLodashFunction(functionName: string): Promise<any> {
    const cacheKey = `lodash-${functionName}`

    if (this.loadedLibraries.has(cacheKey)) {
      return this.loadedLibraries.get(cacheKey)
    }

    if (this.loadingPromises.has(cacheKey)) {
      return this.loadingPromises.get(cacheKey)
    }

    const loadPromise = this.loadLodashFunctionInternal(functionName)
    this.loadingPromises.set(cacheKey, loadPromise)

    return loadPromise
  }

  /**
   * 内部方法：加载 Lodash 函数
   */
  private async loadLodashFunctionInternal(functionName: string): Promise<any> {
    const startTime = performance.now()

    try {
      // 使用静态映射避免 Vite 动态导入问题
      const module = await this.loadLodashFunctionByName(functionName)

      const loadTime = performance.now() - startTime
      const result: LoadResult = {
        library: `Lodash - ${functionName}`,
        loaded: true,
        loadTime
      }

      this.loadedLibraries.set(`lodash-${functionName}`, result)
      console.log(`🔧 Lodash function loaded: ${functionName} (${loadTime.toFixed(2)}ms)`)

      return module
    } catch (error) {
      const result: LoadResult = {
        library: `Lodash - ${functionName}`,
        loaded: false,
        error: error as Error
      }
      this.loadedLibraries.set(`lodash-${functionName}`, result)
      throw error
    }
  }

  /**
   * 通过名称加载 Lodash 函数（使用静态导入映射）
   */
  private async loadLodashFunctionByName(functionName: string): Promise<any> {
    // 静态映射表，避免 Vite 动态导入问题
    const functionMap: Record<string, () => Promise<any>> = {
      'debounce': () => import('lodash-es/debounce'),
      'throttle': () => import('lodash-es/throttle'),
      'cloneDeep': () => import('lodash-es/cloneDeep'),
      'get': () => import('lodash-es/get'),
      'set': () => import('lodash-es/set'),
      'merge': () => import('lodash-es/merge'),
      'uniq': () => import('lodash-es/uniq'),
      'isEmpty': () => import('lodash-es/isEmpty'),
      'isEqual': () => import('lodash-es/isEqual'),
      'pick': () => import('lodash-es/pick'),
      'omit': () => import('lodash-es/omit'),
      'filter': () => import('lodash-es/filter'),
      'map': () => import('lodash-es/map'),
      'reduce': () => import('lodash-es/reduce'),
      'find': () => import('lodash-es/find'),
      'sortBy': () => import('lodash-es/sortBy'),
      'groupBy': () => import('lodash-es/groupBy'),
      'chunk': () => import('lodash-es/chunk'),
      'flatten': () => import('lodash-es/flatten')
    }

    const loader = functionMap[functionName]
    if (!loader) {
      console.warn(`Unknown Lodash function: ${functionName}`)
      return null
    }

    return await loader()
  }

  /**
   * 预加载关键库
   */
  async preloadCriticalLibraries(): Promise<void> {
    const criticalLibs = ['element-plus', 'dayjs']
    const loadPromises = criticalLibs.map(lib => this.preloadLibrary(lib))

    await Promise.allSettled(loadPromises)
  }

  /**
   * 预加载库
   */
  async preloadLibrary(libraryName: string): Promise<void> {
    const config = this.libraryConfigs.get(libraryName)

    if (!config || !config.preload) {
      return
    }

    console.log(`🚀 Preloading library: ${libraryName}`)

    try {
      switch (libraryName) {
        case 'element-plus':
          // 预加载常用的 Element Plus 组件
          const commonComponents = ['button', 'input', 'form', 'table', 'dialog']
          await Promise.allSettled(
            commonComponents.map(comp => this.loadElementPlusComponent(comp))
          )
          break
        case 'echarts':
          // 预加载 ECharts 核心和常用图表
          await Promise.allSettled([
            this.loadEChartsModule('core'),
            this.loadEChartsModule('charts'),
            this.loadEChartsModule('components')
          ])
          break
        case 'lodash-es':
          // 预加载常用 Lodash 函数
          const commonFunctions = ['debounce', 'throttle', 'cloneDeep', 'get', 'set']
          await Promise.allSettled(
            commonFunctions.map(func => this.loadLodashFunction(func))
          )
          break
      }
    } catch (error) {
      console.warn(`Failed to preload library ${libraryName}:`, error)
    }
  }

  /**
   * 智能库加载 - 根据用户行为预测需要的库
   */
  smartLibraryLoad(userAction: string): void {
    const predictions = this.predictLibraries(userAction)

    predictions.forEach(lib => {
      if (lib.confidence > 0.7) {
        this.preloadLibrary(lib.name)
      }
    })
  }

  /**
   * 预测用户需要的库
   */
  private predictLibraries(userAction: string): Array<{ name: string; confidence: number }> {
    const predictions: Array<{ name: string; confidence: number }> = []

    switch (userAction) {
      case 'navigate_to_analysis':
        predictions.push({ name: 'echarts', confidence: 0.9 })
        predictions.push({ name: 'lodash-es', confidence: 0.7 })
        break
      case 'navigate_to_reports':
        predictions.push({ name: 'marked', confidence: 0.8 })
        predictions.push({ name: 'element-plus', confidence: 0.9 })
        break
      case 'navigate_to_settings':
        predictions.push({ name: 'element-plus', confidence: 0.9 })
        break
      default:
        predictions.push({ name: 'element-plus', confidence: 0.5 })
    }

    return predictions
  }

  /**
   * 获取库加载报告
   */
  getLibraryReport(): {
    totalLibraries: number
    loadedLibraries: number
    failedLibraries: number
    libraries: Array<{ name: string; loaded: boolean; loadTime?: number; error?: string }>
  } {
    const libraries = Array.from(this.loadedLibraries.entries()).map(([key, result]) => ({
      name: key,
      loaded: result.loaded,
      loadTime: result.loadTime,
      error: result.error?.message
    }))

    return {
      totalLibraries: this.libraryConfigs.size,
      loadedLibraries: libraries.filter(lib => lib.loaded).length,
      failedLibraries: libraries.filter(lib => !lib.loaded).length,
      libraries
    }
  }

  /**
   * 清理未使用的库
   */
  cleanupUnusedLibraries(): void {
    // 实现 LRU 缓存策略，清理最近最少使用的库
    console.log('🧹 Cleaning up unused libraries')
  }

  /**
   * 获取库配置
   */
  getLibraryConfig(libraryName: string): LibraryConfig | undefined {
    return this.libraryConfigs.get(libraryName)
  }

  /**
   * 添加自定义库配置
   */
  addLibraryConfig(config: LibraryConfig): void {
    this.libraryConfigs.set(config.name, config)
  }
}

export default LibraryOptimizer
export type { LibraryConfig, LoadResult }