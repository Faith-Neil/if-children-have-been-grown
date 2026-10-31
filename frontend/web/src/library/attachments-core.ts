// 为什么有这个文件：资料附件扫描件的纯函数（PRD v1.8 §5.4.7、§5.9.1 规则 7；APP-M2-T059、T198）。
// 它解决什么问题：附件接口地址、上传前类型与大小核对、页码范围校验、功能点标签整理与表格里的文字说明，
// 页面组件只管展示和调用，规则可以单独测试。

export type LibraryAttachment = {
  id: string;
  library_id: string;
  filename: string;
  kind: 'pdf' | 'png' | 'jpeg' | string;
  size_bytes: number;
  sha256: string;
  page_count: number;
  page_from: number;
  page_to: number;
  is_sensitive: boolean;
  shows_identity: boolean;
  feature_tags: string[];
  uploaded_by: string;
  uploaded_at: string;
  revision: number;
};

export const ATTACHMENT_ACCEPT = '.pdf,.png,.jpg,.jpeg';
const ALLOWED = /\.(pdf|png|jpe?g)$/i;

export const attachmentPaths = {
  list: (itemId: string) => `/api/v1/library/${encodeURIComponent(itemId)}/attachments`,
  upload: (itemId: string, filename: string) =>
    `/api/v1/library/${encodeURIComponent(itemId)}/attachments/raw?${new URLSearchParams({ filename }).toString()}`,
  item: (attachmentId: string) => `/api/v1/library/attachments/${encodeURIComponent(attachmentId)}`,
  file: (attachmentId: string) => `/api/v1/library/attachments/${encodeURIComponent(attachmentId)}/file`,
};

export function uploadProblem(file: { name: string; size: number }, maxBytes: number): string | null {
  if (!ALLOWED.test(file.name)) return '附件扫描件只支持 PDF、PNG、JPG。';
  if (file.size === 0) return '文件为空。';
  if (file.size > maxBytes) return `单个文件不能超过 ${Math.round(maxBytes / 1024 / 1024)}MB。`;
  return null;
}

export function pageRangeProblem(from: number | null | undefined, to: number | null | undefined, pageCount: number): string | null {
  if (!Number.isInteger(from) || !Number.isInteger(to)) return '请填写整数页码。';
  if ((from as number) < 1 || (to as number) > pageCount) return `页码须在第 1～${pageCount} 页之间。`;
  if ((from as number) > (to as number)) return '起始页不能大于结束页。';
  return null;
}

export function normalizeTags(values: string[]): string[] {
  const result: string[] = [];
  for (const value of values.flatMap(v => v.split(/[,，、;；\n]/))) {
    const tag = value.trim();
    if (tag && !result.includes(tag)) result.push(tag);
  }
  return result.slice(0, 30);
}

export function pageRangeLabel(item: Pick<LibraryAttachment, 'page_from' | 'page_to' | 'page_count'>): string {
  if (item.page_from === 1 && item.page_to === item.page_count) return item.page_count === 1 ? '1 页（全部）' : `全部 ${item.page_count} 页`;
  return `第 ${item.page_from}～${item.page_to} 页（共 ${item.page_count} 页）`;
}

export function sizeLabel(bytes: number): string {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}
