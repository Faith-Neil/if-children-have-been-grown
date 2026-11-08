// 为什么有这个文件：目录拖放后算出新的顺序和 1～4 级。
// 它解决什么问题：拖动一节时连同它下面更深的子节一起移动，左右拖或工具栏升降级时不能比上一节深超过一级。

export function blockEnd<T extends { level: number }>(items: T[], index: number) {
  const level = items[index]?.level ?? 1;
  let end = index + 1;
  while (end < items.length && items[end].level > level) end += 1;
  return end;
}

export function moveOutline<T extends { level: number }>(items: T[], from: number, to: number, level: number): T[] {
  if (from < 0 || from >= items.length) return items;
  const end = blockEnd(items, from);
  if (to > from && to < end) return items;
  const next = items.map(item => ({ ...item }));
  const block = next.splice(from, end - from);
  const insertAt = Math.max(0, Math.min(next.length, to > from ? to - block.length : to));
  const rootLevel = clampedLevel(next, insertAt, level);
  const delta = rootLevel - block[0].level;
  block.forEach((item, offset) => {
    item.level = offset === 0 ? rootLevel : Math.min(4, Math.max(1, item.level + delta));
  });
  next.splice(insertAt, 0, ...block);
  return next;
}

export function placeHeading<T extends { level: number }>(items: T[], from: number, to: number, level: number): T[] {
  if (from < 0 || from >= items.length) return items;
  const boundedTo = Math.max(0, Math.min(items.length, to));
  const next = items.map(item => ({ ...item }));
  if (boundedTo === from || boundedTo === from + 1) {
    next[from] = { ...next[from], level: clampedLevel(next, from, level) };
    return next;
  }
  const [moved] = next.splice(from, 1);
  const insertAt = boundedTo > from ? boundedTo - 1 : boundedTo;
  moved.level = clampedLevel(next, insertAt, level);
  next.splice(insertAt, 0, moved);
  return next;
}

function clampedLevel<T extends { level: number }>(items: T[], index: number, level: number) {
  if (index <= 0) return 1;
  const ceiling = Math.min(4, (items[index - 1]?.level ?? 1) + 1);
  return Math.min(ceiling, Math.max(1, level));
}
