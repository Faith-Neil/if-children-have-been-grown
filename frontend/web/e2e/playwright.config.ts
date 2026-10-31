// 为什么有这个文件：配置浏览器端到端检查，只用Chromium和本机内存后台。
// 它解决什么问题：布局断点、离开保护与前进后退需要真实浏览器证据；产物写到工作区外，不入库。
import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const port = Number(process.env.E2E_PORT || 8766);
const root = resolve(import.meta.dirname, '../../..');
const python = process.env.E2E_PYTHON || 'python';

export default defineConfig({
  testDir: '.',
  testMatch: '*.spec.ts',
  outputDir: process.env.E2E_OUTPUT_DIR || join(tmpdir(), 'icg-e2e', 'results'),
  timeout: 60_000,
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    browserName: 'chromium',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `${python} -m uvicorn icg_demo.main:app --app-dir backend/bid-core --host 127.0.0.1 --port ${port} --workers 1`,
    cwd: root,
    url: `http://127.0.0.1:${port}/health`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
