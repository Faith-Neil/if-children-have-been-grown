// 为什么有这个文件：统一页面构建入口和本地请求转发。
// 它解决什么问题：开发页面与后端使用相同接口路径，发布时资源不依赖外网。
// PDF.js 的字符映射（中文 PDF 常用）、标准字体和解码器（扫描件常见的 JBIG2/JPEG2000）复制到 assets/pdfjs，随产品一起发布。
import { cpSync, existsSync, readFileSync } from 'node:fs';
import { join, normalize, resolve } from 'node:path';
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';

const PDFJS_ROOT = resolve(__dirname, 'node_modules/pdfjs-dist');
const PDFJS_DIRS = ['cmaps', 'standard_fonts', 'wasm', 'iccs'];

function pdfjsAssets(): Plugin {
  let outDir = 'dist';
  return {
    name: 'icg-pdfjs-assets',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir);
    },
    configureServer(server) {
      server.middlewares.use('/assets/pdfjs/', (req, res, next) => {
        const target = normalize(join(PDFJS_ROOT, decodeURIComponent((req.url ?? '').split('?')[0])));
        if (!target.startsWith(PDFJS_ROOT) || !existsSync(target) || !PDFJS_DIRS.some(dir => target.startsWith(join(PDFJS_ROOT, dir)))) return next();
        res.end(readFileSync(target));
      });
    },
    writeBundle() {
      for (const dir of PDFJS_DIRS) cpSync(join(PDFJS_ROOT, dir), join(outDir, 'assets', 'pdfjs', dir), { recursive: true });
    },
  };
}

export default defineConfig({
  plugins: [react(), pdfjsAssets()],
  base: '/',
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:8710' } },
  build: { outDir: 'dist', emptyOutDir: true },
});
