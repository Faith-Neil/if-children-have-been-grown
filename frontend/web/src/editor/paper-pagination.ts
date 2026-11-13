// 为什么有这个文件：纸面编辑器按 A4 高度估算分页，贴近 Word 分页浏览。
// 它解决什么问题：长章节在编辑区按页断开显示，而不是一整条无限长白纸。

/** A4 纸面高度（96dpi 近似值，单位 px） */
export const PAPER_PAGE_HEIGHT = 1123;
/** 页与页之间的桌面留白 */
export const PAPER_PAGE_GAP = 18;
/** 页内上下页边距 */
export const PAPER_PAGE_MARGIN_Y = 96;
/** 单页可排正文高度 */
export const PAPER_PAGE_BODY_HEIGHT = PAPER_PAGE_HEIGHT - PAPER_PAGE_MARGIN_Y * 2;

export function estimatePaperPageCount(contentHeight: number): number {
  if (!Number.isFinite(contentHeight) || contentHeight <= 0) return 1;
  return Math.max(1, Math.ceil(contentHeight / PAPER_PAGE_BODY_HEIGHT));
}

export function paperStackMinHeight(pageCount: number): number {
  const pages = Math.max(1, pageCount);
  return pages * PAPER_PAGE_HEIGHT + (pages - 1) * PAPER_PAGE_GAP;
}
