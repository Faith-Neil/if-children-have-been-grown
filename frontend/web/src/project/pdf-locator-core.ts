// 为什么有这个文件：原件 PDF 定位（APP-M2-T103）的纯计算部分：在哪一块画高亮、画多大。
// 它解决什么问题：扫描件没有文字层，只能用 RAGFlow DeepDOC 回传的位置框；电子版 PDF 用 PDF.js 文字层逐字匹配。
// 两条路都按“去掉空白和表格分隔符后比对”，因为识别文字和条款原句之间常差换行与空格。
// 规则与后端测试 tests/backend/test_tender_remote_parse.py::locatable 一致，改动须两边同步。

export type Box = [number, number, number, number]; // [x0, x1, top, bottom]，PDF 点，左上角为原点
export type TextRegion = { text: string; boxes: number[][] };
export type TextItemLike = { str: string };
export type CssRect = { left: number; top: number; width: number; height: number };

const PREFIX = 12;

export function plain(text: string): string {
  return text.replace(/[\s|]/g, '');
}

/** 扫描件：返回本页与原句对应的位置框。区域含原句、原句含整行区域，或区域含原句前 12 字。 */
export function regionHits(regions: TextRegion[], quote: string): Box[] {
  const q = plain(quote);
  if (!q) return [];
  const head = q.slice(0, PREFIX);
  const hits = regions.filter(region => {
    const text = plain(region.text);
    return text.includes(q) || (text.length >= 4 && q.includes(text)) || text.includes(head);
  });
  // 有整句命中的区域时只画它（避免同页别处出现同样的开头被一起画上）
  const whole = hits.filter(region => plain(region.text).includes(q));
  const chosen = whole.length ? [whole.reduce((a, b) => (plain(a.text).length <= plain(b.text).length ? a : b))] : hits;
  return chosen.flatMap(region => region.boxes.filter(box => box.length === 4).map(box => box as Box));
}

/** 电子版：返回覆盖原句的文字项下标（先找整句，找不到再找前 12 字）。 */
export function textItemHits(items: TextItemLike[], quote: string): number[] {
  const q = plain(quote);
  if (!q) return [];
  let joined = '';
  const owner: number[] = [];
  items.forEach((item, index) => {
    const text = plain(item.str);
    joined += text;
    for (let i = 0; i < text.length; i += 1) owner.push(index);
  });
  for (const needle of [q, q.slice(0, PREFIX)]) {
    const start = joined.indexOf(needle);
    if (start >= 0) return [...new Set(owner.slice(start, start + needle.length))];
  }
  return [];
}

/** 位置框（PDF 点）换算成画布上的像素矩形。 */
export function boxToCss(box: Box, scale: number): CssRect {
  const [x0, x1, top, bottom] = box;
  return { left: x0 * scale, top: top * scale, width: (x1 - x0) * scale, height: (bottom - top) * scale };
}

/** PDF.js convertToViewportRectangle 返回的两角坐标（可能颠倒）规整成矩形。 */
export function cornersToCss(corners: number[]): CssRect {
  const [a, b, c, d] = corners;
  return { left: Math.min(a, c), top: Math.min(b, d), width: Math.abs(c - a), height: Math.abs(d - b) };
}

export function isPdf(file: { filename?: string; media_type?: string } | undefined): boolean {
  return !!file && (file.media_type === 'application/pdf' || /\.pdf$/i.test(file.filename ?? ''));
}

export function locateMessage(quote: string, hits: number): string {
  if (!quote) return '';
  return hits > 0 ? '已在原件上高亮条款原句' : '本页未找到条款原句，请对照识别文字核对';
}
