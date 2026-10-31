// 为什么有这个文件：统一新建和设置页面的项目输入、北京时间显示与接口时间格式。
// 它解决什么问题：空日期不发送非法null，换时区也不会改变截止时间，两个页面不会各用一套规则。
export function projectBasis(project: { name: string; tender_number?: string; deadline?: string | null; sensitive?: boolean }): string {
  return JSON.stringify({ name: project.name, tender_number: project.tender_number ?? '', deadline: project.deadline ?? '', sensitive: !!project.sensitive });
}

export function deadlineForApi(value?: string | null): string {
  if (!value?.trim()) return '';
  const normalized = value.trim().replace(' ', 'T');
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(normalized)) throw new Error('截止时间请填写 YYYY-MM-DD HH:mm，按北京时间计算。');
  const date = new Date(normalized + '+08:00');
  if (!Number.isFinite(date.getTime()) || deadlineForForm(date.toISOString()).replace(' ', 'T') !== normalized.slice(0, 16)) throw new Error('截止日期或时间无效，请核对。');
  return date.toISOString();
}

export function deadlineForForm(value?: string | null): string {
  if (!value) return '';
  // 兼容早期接口保存的无时区日期；新的输入统一写成UTC。
  const normalized = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value) ? value + '+08:00' : value;
  const date = new Date(normalized);
  if (!Number.isFinite(date.getTime())) return '';
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(date);
  const part = (type: string) => parts.find(item => item.type === type)?.value ?? '';
  return `${part('year')}-${part('month')}-${part('day')} ${part('hour')}:${part('minute')}`;
}

export function projectFields(values: { name?: string; tender_number?: string; deadline?: string | null; sensitive?: boolean }) {
  return { ...(values.name !== undefined ? { name: values.name } : {}), tender_number: values.tender_number || '', deadline: deadlineForApi(values.deadline), sensitive: !!values.sensitive };
}

export const BASIC_INFO_KEYS = ['tenderee_name', 'agency_name', 'lot_name', 'client_address', 'open_at', 'service_period', 'project_location'] as const;

/** 解析后带出、可人工修改的基本信息；只发送字符串，后台比较旧值后才记“已人工修改” */
export function basicInfoFields(values: Partial<Record<(typeof BASIC_INFO_KEYS)[number], string | null | undefined>>) {
  return Object.fromEntries(BASIC_INFO_KEYS.map(key => [key, (values[key] ?? '').trim()]));
}
