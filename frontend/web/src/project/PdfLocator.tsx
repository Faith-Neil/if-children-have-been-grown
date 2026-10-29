// 为什么有这个文件：在解析页左栏直接显示招标原件 PDF，按条款来源跳页并高亮原句（APP-M2-T103）。
// 它解决什么问题：识别文字可能有错，核对条款要看原件本身；扫描件按 DeepDOC 位置框高亮，电子版按 PDF.js 文字层高亮。
// PDF.js 与其 Worker 都随前端打包（本站地址），内网部署不依赖外网；只在打开 PDF 时才加载这部分代码。

import React, { useEffect, useRef, useState } from 'react';
import { Alert, Spin } from 'antd';
import { fetchBytes } from '../shared/api.ts';
import { boxToCss, cornersToCss, locateMessage, regionHits, textItemHits, type CssRect, type TextRegion } from './pdf-locator-core.ts';

type PdfModule = typeof import('pdfjs-dist');
type PdfDocument = Awaited<ReturnType<PdfModule['getDocument']>['promise']>;

let pdfModule: Promise<PdfModule> | null = null;
function loadPdfJs(): Promise<PdfModule> {
  pdfModule ??= Promise.all([import('pdfjs-dist'), import('pdfjs-dist/build/pdf.worker.min.mjs?url')]).then(([pdfjs, worker]) => {
    pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
    return pdfjs;
  });
  return pdfModule;
}

export interface PdfLocatorProps {
  fileUrl: string;
  token: string;
  page: number;
  quote: string;
  regions: TextRegion[];
  onPageCount?: (count: number) => void;
}

const MAX_WIDTH = 900;
// 构建时由 vite.config.ts 复制到本站（中文 CMap、标准字体、JBIG2/JPEG2000 解码器），不访问外网
const PDFJS_ASSETS = {
  cMapUrl: '/assets/pdfjs/cmaps/', cMapPacked: true,
  standardFontDataUrl: '/assets/pdfjs/standard_fonts/', wasmUrl: '/assets/pdfjs/wasm/', iccUrl: '/assets/pdfjs/iccs/',
};

export function PdfLocator({ fileUrl, token, page, quote, regions, onPageCount }: PdfLocatorProps) {
  const [doc, setDoc] = useState<PdfDocument | null>(null);
  const [error, setError] = useState('');
  const [hits, setHits] = useState<CssRect[]>([]);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [rendering, setRendering] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    let loading: { destroy: () => Promise<void> } | null = null;
    setDoc(null);
    setError('');
    Promise.all([loadPdfJs(), fetchBytes(fileUrl, token)])
      .then(([pdfjs, data]) => {
        const task = pdfjs.getDocument({ data, ...PDFJS_ASSETS });
        loading = task;
        return task.promise;
      })
      .then(result => {
        if (cancelled) return;
        setDoc(result);
        onPageCount?.(result.numPages);
      })
      .catch(() => {
        if (!cancelled) setError('原件 PDF 无法在页面内打开，请下载原件核对或切换到识别文字。');
      });
    return () => {
      cancelled = true;
      void loading?.destroy();
    };
  }, [fileUrl, token]);

  useEffect(() => {
    if (!doc || !canvasRef.current) return;
    let cancelled = false;
    let task: { cancel: () => void; promise: Promise<void> } | null = null;
    setRendering(true);
    setHits([]);
    (async () => {
      const pdfPage = await doc.getPage(Math.min(Math.max(1, page), doc.numPages));
      const base = pdfPage.getViewport({ scale: 1 });
      const container = wrapRef.current?.closest('.paper-wrap') as HTMLElement | null;
      const width = Math.min(MAX_WIDTH, Math.max(320, (container?.clientWidth ?? 600) - 32));
      const scale = width / base.width;
      const viewport = pdfPage.getViewport({ scale });
      const canvas = canvasRef.current;
      if (!canvas || cancelled) return;
      const ratio = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * ratio);
      canvas.height = Math.floor(viewport.height * ratio);
      canvas.style.width = `${viewport.width}px`;
      canvas.style.height = `${viewport.height}px`;
      task = pdfPage.render({ canvas, viewport, transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0] });
      await task.promise;
      if (cancelled) return;
      setSize({ width: viewport.width, height: viewport.height });
      let rects: CssRect[] = [];
      if (quote && regions.length) {
        rects = regionHits(regions, quote).map(box => boxToCss(box, scale));
      } else if (quote) {
        const content = await pdfPage.getTextContent();
        const items = content.items.filter((item): item is typeof item & { str: string; transform: number[]; width: number; height: number } => 'str' in item);
        rects = textItemHits(items, quote).map(index => {
          const item = items[index];
          const [x, y] = [item.transform[4], item.transform[5]];
          const height = item.height || Math.abs(item.transform[3]);
          return cornersToCss([...viewport.convertToViewportPoint(x, y), ...viewport.convertToViewportPoint(x + item.width, y + height)]);
        });
      }
      if (cancelled) return;
      setHits(rects);
      if (rects.length && container) container.scrollTop = Math.max(0, rects[0].top - 80);
    })()
      .catch(() => {
        if (!cancelled) setError('本页渲染失败，请下载原件核对。');
      })
      .finally(() => {
        if (!cancelled) setRendering(false);
      });
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [doc, page, quote, regions]);

  if (error) return <Alert type="warning" showIcon message={error} />;
  const message = !rendering && doc ? locateMessage(quote, hits.length) : '';
  return (
    <div className="pdf-locator" ref={wrapRef}>
      {message && <div className={hits.length ? 'pdf-locate-note' : 'pdf-locate-note miss'} role="status">{message}</div>}
      <Spin spinning={!doc || rendering}>
        <div className="pdf-page" data-testid="pdf-page" data-page={page} style={size.width ? { width: size.width, height: size.height } : undefined}>
          <canvas ref={canvasRef} aria-label={`原件第 ${page} 页`} />
          {hits.map((rect, index) => (
            <span key={index} className="pdf-hit" data-testid="pdf-hit" style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }} />
          ))}
        </div>
      </Spin>
    </div>
  );
}
