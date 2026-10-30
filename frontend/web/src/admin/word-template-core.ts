// 为什么有这个文件：公司 Word 模板与导出模板选项的纯函数（PRD v1.8 §5.6.2、§5.9.1 主要元素 5 与规则 1；APP-M2-T086、T150）。
// 它解决什么问题：模板接口地址、上传前核对（只收 .docx、不超过 20MB）、导出页“模板与选项”的下拉项与请求体，
// 企业设置页与导出页共用同一套规则。

export type WordTemplate = {
  id: string;
  filename: string;
  sha256: string;
  size_bytes: number;
  uploaded_by: string;
  uploaded_at: string;
  applied: string[];
  defaults: string[];
};

export type TemplateChoice = 'auto' | 'company' | 'platform';

export const TEMPLATE_MAX_BYTES = 20 * 1024 * 1024;

export const wordTemplatePaths = {
  info: (companyId: string) => `/api/v1/companies/${encodeURIComponent(companyId)}/word-template`,
  upload: (companyId: string, filename: string) =>
    `/api/v1/companies/${encodeURIComponent(companyId)}/word-template?${new URLSearchParams({ filename }).toString()}`,
  file: (companyId: string) => `/api/v1/companies/${encodeURIComponent(companyId)}/word-template/file`,
};

export function templateUploadProblem(file: { name: string; size: number }): string | null {
  if (!/\.docx$/i.test(file.name)) return 'Word 模板只接受 .docx 文件（.doc、.dotx、.docm 请先另存为 .docx）。';
  if (file.size > TEMPLATE_MAX_BYTES) return 'Word 模板不能超过 20MB。';
  return null;
}

export function templateOptions(template: WordTemplate | null): { value: TemplateChoice; label: string; disabled?: boolean }[] {
  return [
    { value: 'company', label: template ? `本公司 Word 模板（${template.filename}）` : '本公司 Word 模板（尚未上传）', disabled: !template },
    { value: 'platform', label: '平台默认模板' },
  ];
}

export function defaultTemplateChoice(template: WordTemplate | null): TemplateChoice {
  return template ? 'company' : 'platform';
}

export type ExportOptions = { template: TemplateChoice; insertAttachments: boolean; watermark: string };

export function exportRequestBody(checkId: string, kind: string, volume: string, options: ExportOptions) {
  const watermark = options.watermark.trim();
  return {
    check_id: checkId, kind, volume, template: options.template, insert_attachments: options.insertAttachments,
    ...(watermark ? { attachment_watermark: watermark.slice(0, 60) } : {}),
  };
}

export function templateSourceLabel(template: { source?: string; filename?: string | null } | undefined): string {
  if (!template?.source) return '—';
  return template.source === 'company' ? `公司模板 ${template.filename ?? ''}`.trim() : '平台默认';
}
