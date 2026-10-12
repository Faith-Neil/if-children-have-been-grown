// 为什么有这个文件：把未保存离开的判断从页面按钮里抽出来。
// 它解决什么问题：路由切换、浏览器前进后退和刷新关闭使用同一条保留规则。

export const leaveCopy = {
  title: '当前页面还有未保存的修改',
  content: '离开页面会丢失尚未保存的文字。已保存的草稿可以返回恢复。',
  okText: '离开页面',
  cancelText: '继续编辑',
};

export function decideNavigation(input: { dirty: boolean; currentPath: string; nextPath: string; confirmed: boolean }): { path: string; proceed: boolean } {
  const current = normalize(input.currentPath);
  const next = normalize(input.nextPath);
  if (!input.dirty || current === next) return { path: next, proceed: true };
  if (!input.confirmed) return { path: current, proceed: false };
  return { path: next, proceed: true };
}

export function applyBeforeUnload(dirty: boolean, event: { preventDefault(): void; returnValue: string }): boolean {
  if (!dirty) return false;
  event.preventDefault();
  event.returnValue = leaveCopy.content;
  return true;
}

export function readHistoryIndex(state: unknown): number | null {
  if (!state || typeof state !== 'object') return null;
  const record = state as { app?: unknown; idx?: unknown };
  if (record.app !== true || typeof record.idx !== 'number' || !Number.isFinite(record.idx)) return null;
  return record.idx;
}

export function historyStep(fromIndex: number, toIndex: number | null): number | null {
  if (toIndex === null || toIndex === fromIndex) return null;
  return toIndex - fromIndex;
}

function normalize(path: string): string {
  const value = path.split('?')[0].split('#')[0] || '/';
  return value.length > 1 && value.endsWith('/') ? value.slice(0, -1) : value || '/';
}
