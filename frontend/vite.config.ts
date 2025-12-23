import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: [
        'vue',
        'vue-router',
        'pinia',
        '@vueuse/core'
      ],
      dts: true,
      eslintrc: {
        enabled: true
      }
    }),
    // 自动按需组件导入
    Components({
      resolvers: [ElementPlusResolver()],
      dts: true
    })
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@views': resolve(__dirname, 'src/views'),
      '@stores': resolve(__dirname, 'src/stores'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@types': resolve(__dirname, 'src/types'),
      '@api': resolve(__dirname, 'src/api')
    }
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    hmr: {
      overlay: false
    },
    // 允许访问的主机名
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '0.0.0.0',
      'aitradingcn.com',
      '.aitradingcn.com'  // 支持所有子域名
    ],
    // 允许从项目根目录之外（例如 /docs）导入原始文件
    fs: {
      allow: [resolve(__dirname, '..')]
    },
    // 🚀 预构建优化 - 减少冷启动时间
    warmup: {
      clientFiles: [
        './src/main.ts',
        './src/App.vue',
        './src/router/index.ts',
        './src/stores/auth.ts'
      ]
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true  // 🔥 启用 WebSocket 代理支持
      }
    }
  },
  build: {
    target: 'es2020',  // 支持 nullish coalescing operator (??) 和 optional chaining (?.)
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    rollupOptions: {
      output: {
        chunkFileNames: 'js/[name]-[hash].js',
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: '[ext]/[name]-[hash].[ext]',
        // 🚀 手动代码分割 - 提升缓存效率
        manualChunks: {
          // Vue 生态系统
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          // Element Plus
          'element-plus': ['element-plus', '@element-plus/icons-vue'],
          // 工具库
          'utils': ['axios', 'dayjs', 'lodash-es'],
          // 图表库
          'charts': ['echarts', 'vue-echarts'],
          // Markdown 相关
          'markdown': ['marked', 'vue3-markdown-it']
        }
      }
    },
    // 🚀 启用模块预加载
    modulePreload: {
      polyfill: true,
      resolveDependencies: (filename, deps) => {
        return deps.filter(dep => !dep.includes('.scss') && !dep.includes('.css'))
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables.scss" as *;`
      }
    }
  },
  // 🚀 依赖预构建优化 - 减少启动时间
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'element-plus',
      '@element-plus/icons-vue',
      'axios',
      'dayjs',
      'echarts',
      'vue-echarts'
    ],
    exclude: ['mermaid'] // 排除大型库，按需加载
  }
})