<template>
  <div class="performance-panel">
    <el-card class="panel-card" shadow="hover">
      <template #header>
        <div class="panel-header">
          <el-icon><DataAnalysis /></el-icon>
          <span>性能监控面板</span>
          <el-switch
            v-model="isMonitoring"
            @change="toggleMonitoring"
            size="small"
            style="margin-left: auto"
          />
        </div>
      </template>

      <!-- 性能指标 -->
      <div class="metrics-grid">
        <div class="metric-item">
          <div class="metric-label">FCP</div>
          <div class="metric-value" :class="getMetricClass(metrics.fcp, 1800)">
            {{ metrics.fcp.toFixed(0) }}ms
          </div>
        </div>

        <div class="metric-item">
          <div class="metric-label">LCP</div>
          <div class="metric-value" :class="getMetricClass(metrics.lcp, 2500)">
            {{ metrics.lcp.toFixed(0) }}ms
          </div>
        </div>

        <div class="metric-item">
          <div class="metric-label">FID</div>
          <div class="metric-value" :class="getMetricClass(metrics.fid, 100)">
            {{ metrics.fid.toFixed(0) }}ms
          </div>
        </div>

        <div class="metric-item">
          <div class="metric-label">CLS</div>
          <div class="metric-value" :class="getMetricClass(metrics.cls, 0.1, true)">
            {{ metrics.cls.toFixed(3) }}
          </div>
        </div>
      </div>

      <!-- 优化统计 -->
      <div class="stats-section">
        <h4>优化统计</h4>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">已预加载路由:</span>
            <span class="stat-value">{{ stats.preloadedRoutes }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">已加载组件:</span>
            <span class="stat-value">{{ stats.loadedComponents }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">缓存命中率:</span>
            <span class="stat-value">{{ (stats.cacheHitRate * 100).toFixed(1) }}%</span>
          </div>
        </div>
      </div>

      <!-- 性能等级 -->
      <div class="grade-section">
        <h4>性能等级</h4>
        <div class="grade-display">
          <span class="grade-badge" :class="`grade-${grade.toLowerCase()}`">
            {{ grade }}
          </span>
          <span class="grade-score">{{ performanceScore.toFixed(1) }}/100</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="actions-section">
        <el-button type="primary" size="small" @click="runPerformanceTest">
          <el-icon><Cpu /></el-icon>
          运行测试
        </el-button>
        <el-button type="info" size="small" @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报告
        </el-button>
        <el-button size="small" @click="refreshStats">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <!-- 实时性能图 -->
      <div class="chart-section" v-if="showChart">
        <h4>性能趋势</h4>
        <div ref="chartContainer" class="performance-chart"></div>
      </div>
    </el-card>

    <!-- 告警信息 -->
    <el-card class="alerts-card" shadow="hover" v-if="alerts.length > 0">
      <template #header>
        <span>性能告警</span>
      </template>
      <div class="alerts-list">
        <div
          v-for="alert in alerts.slice(0, 3)"
          :key="alert.timestamp"
          class="alert-item"
          :class="alert.type"
        >
          <el-icon>
            <WarningFilled v-if="alert.type === 'warning'" />
            <CircleCloseFilled v-else />
          </el-icon>
          <span class="alert-message">{{ alert.message }}</span>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  Cpu,
  Download,
  Refresh,
  WarningFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue'
import { performanceOptimizer, PerformanceMonitor } from '@/utils/performance'

const isMonitoring = ref(false)
const metrics = ref({
  fcp: 0,
  lcp: 0,
  fid: 0,
  cls: 0
})
const stats = ref({
  preloadedRoutes: 0,
  loadedComponents: 0,
  cacheHitRate: 0.85
})
const grade = ref('A')
const performanceScore = ref(0)
const alerts = ref<any[]>([])
const showChart = ref(false)

let monitor: PerformanceMonitor
let updateInterval: NodeJS.Timeout | null = null

onMounted(() => {
  monitor = PerformanceMonitor.getInstance()
  refreshStats()

  // 每5秒更新一次数据
  updateInterval = setInterval(refreshStats, 5000)
})

onUnmounted(() => {
  if (updateInterval) {
    clearInterval(updateInterval)
  }
  if (isMonitoring.value) {
    monitor.stopMonitoring()
  }
})

const toggleMonitoring = (enabled: boolean) => {
  if (enabled) {
    monitor.startMonitoring()
    ElMessage.success('性能监控已启动')
  } else {
    monitor.stopMonitoring()
    ElMessage.info('性能监控已停止')
  }
}

const refreshStats = () => {
  // 获取性能指标
  const report = monitor.generateReport()
  metrics.value = {
    fcp: report.metrics.fcp,
    lcp: report.metrics.lcp,
    fid: report.metrics.fid,
    cls: report.metrics.cls
  }

  // 获取优化统计
  const perfStats = performanceOptimizer.global.getStats()
  stats.value = {
    preloadedRoutes: perfStats.loadedComponents, // 这里需要调整
    loadedComponents: perfStats.loadedComponents,
    cacheHitRate: 0.85 // 模拟值
  }

  // 计算性能等级和分数
  grade.value = report.grade
  performanceScore.value = report.score

  // 获取告警信息
  alerts.value = report.alerts
}

const runPerformanceTest = async () => {
  try {
    const { default: PerformanceTester } = await import('@/utils/performance/PerformanceTester')
    const tester = new PerformanceTester()

    ElMessage.info('正在运行性能测试...')
    await tester.runFullTestSuite()

    ElMessage.success('性能测试完成')
    refreshStats()
  } catch (error) {
    console.error('性能测试失败:', error)
    ElMessage.error('性能测试失败')
  }
}

const exportReport = () => {
  const report = monitor.generateReport()
  const dataStr = JSON.stringify(report, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })

  const link = document.createElement('a')
  link.href = URL.createObjectURL(dataBlob)
  link.download = `performance-report-${new Date().toISOString().split('T')[0]}.json`
  link.click()

  ElMessage.success('性能报告已导出')
}

const getMetricClass = (value: number, threshold: number, inverse: boolean = false) => {
  if (inverse) {
    return value <= threshold ? 'good' : value <= threshold * 2 ? 'warning' : 'poor'
  } else {
    return value <= threshold ? 'good' : value <= threshold * 2 ? 'warning' : 'poor'
  }
}
</script>

<style lang="scss" scoped>
.performance-panel {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 380px;
  max-height: 80vh;
  overflow-y: auto;
  z-index: 9999;

  .panel-card {
    .panel-header {
      display: flex;
      align-items: center;
      font-weight: 600;

      .el-icon {
        margin-right: 8px;
        color: #409eff;
      }
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 20px;

      .metric-item {
        text-align: center;
        padding: 12px;
        border: 1px solid #e4e7ed;
        border-radius: 6px;

        .metric-label {
          font-size: 12px;
          color: #909399;
          margin-bottom: 4px;
        }

        .metric-value {
          font-size: 18px;
          font-weight: 600;

          &.good {
            color: #67c23a;
          }

          &.warning {
            color: #e6a23c;
          }

          &.poor {
            color: #f56c6c;
          }
        }
      }
    }

    .stats-section, .grade-section {
      margin-bottom: 16px;

      h4 {
        margin-bottom: 8px;
        color: #303133;
        font-size: 14px;
      }
    }

    .stats-grid {
      .stat-item {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        font-size: 13px;

        .stat-label {
          color: #606266;
        }

        .stat-value {
          font-weight: 500;
          color: #303133;
        }
      }
    }

    .grade-display {
      display: flex;
      align-items: center;
      justify-content: space-between;

      .grade-badge {
        padding: 6px 12px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 16px;

        &.grade-a {
          background-color: #f0f9ff;
          color: #1890ff;
        }

        &.grade-b {
          background-color: #fcffe6;
          color: #52c41a;
        }

        &.grade-c {
          background-color: #fff7e6;
          color: #fa8c16;
        }

        &.grade-d, &.grade-f {
          background-color: #fff1f0;
          color: #ff4d4f;
        }
      }

      .grade-score {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
      }
    }

    .actions-section {
      display: flex;
      gap: 8px;
      margin-bottom: 16px;

      .el-button {
        flex: 1;
      }
    }

    .chart-section {
      h4 {
        margin-bottom: 8px;
        color: #303133;
        font-size: 14px;
      }

      .performance-chart {
        height: 120px;
        background-color: #f5f7fa;
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #909399;
        font-size: 12px;
      }
    }
  }

  .alerts-card {
    margin-top: 12px;

    .alerts-list {
      .alert-item {
        display: flex;
        align-items: center;
        padding: 8px;
        margin-bottom: 8px;
        border-radius: 4px;
        font-size: 13px;

        &.warning {
          background-color: #fdf6ec;
          color: #e6a23c;
        }

        &.error {
          background-color: #fef0f0;
          color: #f56c6c;
        }

        .el-icon {
          margin-right: 8px;
        }

        .alert-message {
          flex: 1;
        }
      }
    }
  }
}
</style>