// 为什么有这个文件：项目设置“导出设置”的命名规则纯函数（PRD v1.8 §5.1.4 第 9 项、§5.9.1 第 11 条；APP-M2-T086）。
// 它解决什么问题：保存前在页面先核对（递交版不能含 {编写人}、只能用登记的变量），并按示例值预览文件名；后台保存时同样核对。

export type NamingVariable = { name: string; description: string };
export type ExportSettings = {
  revision?: number; internal_template: string; submit_rule: string; updated_by?: string | null; updated_at?: string | null;
  variables: NamingVariable[];
};

export const exportSettingsPath = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/export-settings`;

const VAR = /\{([^{}]+)\}/g;

export function namingProblems(rule: string, kind: 'internal' | 'submission', variables: NamingVariable[]): string[] {
  const known = new Set(variables.map(v => v.name));
  const found: string[] = [];
  const unknown = [...new Set([...rule.matchAll(VAR)].map(m => m[1]).filter(name => !known.has(name)))];
  if (unknown.length) found.push(`不认识的变量：${unknown.map(v => `{${v}}`).join('、')}`);
  if (kind === 'submission' && rule.includes('{编写人}')) found.push('递交版命名不能含 {编写人}');
  if (!rule.replace(VAR, 'x').trim()) found.push('命名规则不能为空');
  return found;
}

export function previewName(rule: string, sample: Record<string, string>): string {
  const name = rule.replace(VAR, (_, key: string) => sample[key] ?? '').replace(/[\\/:*?"<>|\r\n\t]+/g, '_').replace(/^[ ._]+|[ ._]+$/g, '');
  return `${name || '投标文件'}.docx`;
}
