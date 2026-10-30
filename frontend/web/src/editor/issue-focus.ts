// 为什么有这个文件：从检查页“定位”跳到编辑台时带上要定位的问题（APP-M2-T166）。
// 它解决什么问题：路由只认到章节为止（/projects/:id/editor/:chapterId），问题编号不进地址；
// 检查页先记下“哪一章、哪个原问题”，编辑台加载该章问题清单后取走并定位，只取一次。

type Pending = { chapterId: string; issueId: string };
let pending: Pending | null = null;

/** 检查批次里的问题编号（check 批次的 issue.id）。 */
export function requestIssueFocus(chapterId: string, issueId: string): void {
  pending = { chapterId, issueId };
}

/** 编辑台载入该章问题后调用：匹配到本章则返回并清除。 */
export function takeIssueFocus(chapterId: string): string | null {
  if (!pending || pending.chapterId !== chapterId) return null;
  const { issueId } = pending;
  pending = null;
  return issueId;
}
