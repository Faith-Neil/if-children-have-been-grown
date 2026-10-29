// 为什么有这个文件：验证原件 PDF 定位（APP-M2-T103）的高亮计算：扫描件用位置框、电子版用文字层。
// 它解决什么问题：识别文字与条款原句常差换行和空格；同页重复开头时只画整句命中的那块；PDF.js 与 Worker 必须本地打包。
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { boxToCss, cornersToCss, isPdf, locateMessage, plain, regionHits, textItemHits } from '../../src/project/pdf-locator-core.ts';

test('scan regions are matched ignoring line breaks, spaces and table separators', () => {
  const regions = [
    { text: '第一章 招标公告', boxes: [[80, 500, 60, 80]] },
    { text: '》支持手动标注，支持两点标注和三点标注功能，适应\n不同版式文本倾斜情况。', boxes: [[131, 505, 78, 127]] },
  ];
  assert.deepEqual(regionHits(regions, '》支持手动标注，支持两点标注和三点标注功能，适应 不同版式文本倾斜情况。'), [[131, 505, 78, 127]]);
  assert.equal(plain('评分 | 分值\n技术 30'), '评分分值技术30');
  assert.deepEqual(regionHits(regions, ''), []);
  assert.deepEqual(regionHits(regions, '完全不在本页的句子'), []);
});

test('a quote split across line regions highlights every line it covers', () => {
  const regions = [
    { text: '1. 投标人须具有独立承担民事责任的能力，', boxes: [[90, 500, 100, 115]] },
    { text: '并提供有效营业执照复印件。', boxes: [[90, 300, 116, 131]] },
    { text: '2. 其他要求', boxes: [[90, 200, 140, 155]] },
  ];
  assert.deepEqual(regionHits(regions, '1. 投标人须具有独立承担民事责任的能力，并提供有效营业执照复印件。'), [[90, 500, 100, 115], [90, 300, 116, 131]]);
});

test('when one region holds the whole quote only that region is drawn', () => {
  const regions = [
    { text: '投标文件未按要求盖章的，视为无效投标。', boxes: [[90, 500, 300, 315]] },
    { text: '投标文件未按要求盖章的，视为无效投标。另见第二章须知前附表。', boxes: [[90, 500, 500, 530]] },
  ];
  assert.deepEqual(regionHits(regions, '投标文件未按要求盖章的，视为无效投标。'), [[90, 500, 300, 315]]);
});

test('text-layer items covering the quote are returned, falling back to its first 12 characters', () => {
  const items = [{ str: '第二章 评标办法' }, { str: '1. 技术方案（30分）：' }, { str: '方案完整的得30分。' }, { str: '2. 报价' }];
  assert.deepEqual(textItemHits(items, '1. 技术方案（30分）：方案完整的得30分。'), [1, 2]);
  assert.deepEqual(textItemHits(items, '1. 技术方案（30分）：方案完整的得30分并附说明'), [1]);
  assert.deepEqual(textItemHits(items, '不存在的原句内容'), []);
});

test('boxes in PDF points scale to canvas pixels and corners normalise', () => {
  assert.deepEqual(boxToCss([100, 300, 50, 70], 1.5), { left: 150, top: 75, width: 300, height: 30 });
  assert.deepEqual(cornersToCss([300, 70, 100, 50]), { left: 100, top: 50, width: 200, height: 20 });
  assert.equal(isPdf({ filename: '招标.PDF' }), true);
  assert.equal(isPdf({ filename: 'a.docx', media_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }), false);
  assert.equal(locateMessage('', 0), '');
  assert.match(locateMessage('原句', 0), /未找到/);
  assert.match(locateMessage('原句', 2), /已在原件上高亮/);
});

test('PDF.js and its worker are bundled locally and loaded only when a PDF is opened', () => {
  const locator = readFileSync(new URL('../../src/project/PdfLocator.tsx', import.meta.url), 'utf8');
  const preview = readFileSync(new URL('../../src/project/OriginalPreview.tsx', import.meta.url), 'utf8');
  assert.match(locator, /import\('pdfjs-dist'\)/);
  assert.match(locator, /import\('pdfjs-dist\/build\/pdf\.worker\.min\.mjs\?url'\)/);
  assert.doesNotMatch(locator, /https?:\/\//);
  assert.doesNotMatch(locator, /^import .* from 'pdfjs-dist'/m);
  assert.match(preview, /<PdfLocator/);
  assert.match(preview, /识别文字/);
});
