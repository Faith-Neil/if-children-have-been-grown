// 为什么有这个文件：技术分册编辑台精简工具栏与目录节状态推导。
// 它解决什么问题：主路径只保留白名单控件；目录可见未生成/待补/需核对等状态。

export type SectionStatus = '未生成' | '生成中' | '已生成' | '待补' | '需重新生成' | '需核对';

export function sectionBody(content: string, number: string, title: string): string {
  const lines = (content || '').split(/\r?\n/);
  const marker = `${number} ${title}`.trim();
  const start = lines.findIndex(line => line.trim() === marker);
  if (start < 0) return '';
  const end = lines.findIndex((line, index) => index > start && /^\d+(?:\.\d+)*\s+\S/.test(line.trim()));
  return lines.slice(start + 1, end < 0 ? undefined : end).join('\n').trim();
}

export function sectionStatus(opts: {
  content: string;
  number: string;
  title: string;
  requirementId?: string | null;
  reviewTitles?: string[];
  generating?: boolean;
}): SectionStatus | null {
  if (!opts.requirementId) return null;
  if (opts.generating) return '生成中';
  if ((opts.reviewTitles ?? []).includes(opts.title)) return '需核对';
  const body = sectionBody(opts.content, opts.number, opts.title);
  if (!body) return '未生成';
  if (body === '待补' || body.includes('待补')) return '待补';
  if (body.includes('需要核对')) return '需核对';
  return '已生成';
}

export function statusColor(status: SectionStatus): string {
  if (status === '已生成') return 'success';
  if (status === '生成中') return 'processing';
  if (status === '需核对' || status === '待补' || status === '需重新生成') return 'warning';
  return 'default';
}

export function wrapTextareaSelection(
  value: string,
  start: number,
  end: number,
  before: string,
  after: string,
): { value: string; start: number; end: number } {
  const selected = value.slice(start, end);
  const next = `${value.slice(0, start)}${before}${selected || '文本'}${after}${value.slice(end)}`;
  const innerStart = start + before.length;
  const innerEnd = innerStart + (selected || '文本').length;
  return { value: next, start: innerStart, end: innerEnd };
}
