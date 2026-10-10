// 为什么有这个文件：统一页面构建入口和本地请求转发。
// 它解决什么问题：开发页面与后端使用相同接口路径，发布时资源不依赖外网。
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/',
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8710' } },
  build: { outDir: 'dist', emptyOutDir: true },
});
