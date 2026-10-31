// 为什么有这个文件：项目状态、基本信息人工修改标记、合作方协议、规则覆盖、分册格式与递交版完整值的纯函数
// （PRD v1.8 §4.3、§5.1.3、§5.1.4；APP-M2-T097～T100）。
// 它解决什么问题：页面保存前先按后台同样的口径核对，状态按钮按当前状态显示，设置读回与概览待办用同一份数据，不在组件里散落判断。

export type VolumeCode = 'technical' | 'business';
export type StatusInfo = { status: string; label: string; read_only: boolean; registered: boolean; result?: string | null; result_label?: string | null; history: Array<Record<string, unknown>> };
export type PartnerRow = { partner_entity_id: string; agreement_attachment_id?: string | null; agreement_ok: boolean; problem?: string | null; relation_type?: string | null; work_share?: string | null };
export type RuleOverrideRow = { rule_key: string; value: boolean | number; source_requirement_id?: string | null };
export type VolumeSettingRow = { volume: VolumeCode; compile_mode: 'system' | 'external'; internal_deadline?: string | null; separate_seal: boolean; page_numbering: 'per_volume' | 'continuous'; blind_bid: boolean; cover_template?: string | null; submit_file_name?: string | null };
export type FullValueInfo = { categories: string[]; basis_requirement_ids: string[]; confirmed_by?: string | null; confirmed_at?: string | null };
export type SettingsTodo = { code: string; title: string; detail: string; tab: string };
export type ProjectSettingsData = {
  revision: number; status: StatusInfo; basic_info: Record<string, string>; manual_edits: Record<string, { by: string; at: string }>;
  partners: PartnerRow[]; rule_overrides: RuleOverrideRow[]; volume_settings: VolumeSettingRow[]; submit_full_value: FullValueInfo;
  sla: { template_name: string; template_stale: boolean; row_count: number; exceeds_capability_count: number; needs_review_count: number } | null;
  staff_occupancy: Array<{ person_name: string; role: string; other_project_name: string; other_role: string }>; todos: SettingsTodo[];
};

export const settingsPath = (projectId: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/settings`;
export const projectSubPath = (projectId: string, tail: string) => `/api/v1/projects/${encodeURIComponent(projectId)}/${tail}`;

export const FULL_VALUE_LABELS: Record<string, string> = { id_number: '身份证件号码', phone: '手机号', bank_account: '银行账号' };
export const BASIC_FIELD_LABELS: Record<string, string> = {
  name: '项目名称', tender_number: '招标编号', deadline: '投标截止时间', tenderee_name: '招标人', agency_name: '代理机构', lot_name: '标段',
  client_address: '对招标人称呼', open_at: '开标时间', service_period: '服务期', project_location: '项目地点',
};
export const RESULT_LABELS: Record<string, string> = { won: '中标', lost: '未中标', void: '废标', failed_tender: '流标' };

export type StatusAction = 'submit' | 'open' | 'result' | 'cancel';

/** 当前状态下可办理的状态变更（与后台 ACTION_FROM 一致）；已取消或已结束没有可办理的动作 */
export function availableStatusActions(status: string): StatusAction[] {
  if (status === 'exported') return ['submit'];
  if (status === 'submitted') return ['open'];
  if (status === 'opened') return ['result'];
  if (['draft', 'pending_confirm', 'compiling'].includes(status)) return ['cancel'];
  return [];
}

export const ACTION_LABELS: Record<StatusAction, string> = { submit: '登记递交', open: '登记开标', result: '登记结果', cancel: '取消项目' };

export function statusRequest(action: StatusAction, reason: string, result?: string): { action: StatusAction; reason: string; result?: string } {
  const text = reason.trim();
  if (action === 'cancel' && text.length < 2) throw new Error('取消项目须填写原因。');
  if (action === 'result') {
    if (!result || !(result in RESULT_LABELS)) throw new Error('登记结果须选择中标、未中标、废标或流标。');
    return { action, reason: text, result };
  }
  return { action, reason: text };
}

/** 基本信息某字段被人工修改过就显示“已人工修改”，返回提示文字，没有则 null */
export function manualEditNote(edits: ProjectSettingsData['manual_edits'] | undefined, field: string, nameOf: (id: string) => string): string | null {
  const mark = edits?.[field];
  return mark ? `已人工修改（${nameOf(mark.by)}，${mark.at.slice(0, 16).replace('T', ' ')}）` : null;
}

export function partnerNeedsAgreement(partners: PartnerRow[]): PartnerRow[] {
  return partners.filter(partner => !partner.agreement_ok);
}

export function partnersPayload(rows: Array<{ partner_entity_id: string; agreement_attachment_id?: string | null; relation_type?: string | null; work_share?: string | null }>) {
  const seen = new Set<string>();
  return rows.filter(row => row.partner_entity_id?.trim()).map(row => {
    const id = row.partner_entity_id.trim();
    if (seen.has(id)) throw new Error('同一合作方不要重复添加。');
    seen.add(id);
    return {
      partner_entity_id: id, agreement_attachment_id: row.agreement_attachment_id?.trim() || null,
      ...(row.relation_type ? { relation_type: row.relation_type } : {}), ...(row.work_share?.trim() ? { work_share: row.work_share.trim() } : {}),
    };
  });
}

/** 规则覆盖整组提交：证明材料有效天数 1～3650、社保月数 0～120，开关为是/否 */
export function ruleOverridesPayload(rows: RuleOverrideRow[]) {
  const seen = new Set<string>();
  return { overrides: rows.map(row => {
    const key = row.rule_key.trim();
    if (seen.has(key)) throw new Error(`规则 ${key} 重复。`);
    seen.add(key);
    if (key.startsWith('proof_valid_days.')) {
      if (key.length === 'proof_valid_days.'.length || !Number.isInteger(row.value) || Number(row.value) < 1 || Number(row.value) > 3650) throw new Error('证明材料有效天数须为 1～3650 的整数，并写明材料类型。');
    } else if (key === 'social_insurance_months') {
      if (!Number.isInteger(row.value) || Number(row.value) < 0 || Number(row.value) > 120) throw new Error('连续缴纳社保月数须为 0～120 的整数。');
    } else if (key === 'require_own_staff' || key === 'check_service_period') {
      if (typeof row.value !== 'boolean') throw new Error('该规则的取值只能是“是”或“否”。');
    } else throw new Error(`不认识的规则：${key}`);
    return { rule_key: key, value: row.value, ...(row.source_requirement_id ? { source_requirement_id: row.source_requirement_id } : {}) };
  }) };
}

/** 分册设置保存前核对；writerNames 为本项目成员姓名，递交文件名不得含编写人变量或姓名 */
export function volumeSettingsPayload(rows: VolumeSettingRow[], writerNames: string[]) {
  return { volumes: rows.map(row => {
    const name = (row.submit_file_name ?? '').trim();
    if (name.includes('{编写人}')) throw new Error('递交文件名不能含 {编写人}。');
    const leaked = writerNames.filter(writer => writer && name.includes(writer));
    if (leaked.length) throw new Error(`递交文件名不能含编写人姓名：${leaked.join('、')}。`);
    const deadline = (row.internal_deadline ?? '').trim();
    if (deadline && Number.isNaN(new Date(deadline).getTime())) throw new Error('内部截止时间格式无效，请用 2026-12-30T17:00 这样的写法。');
    return { volume: row.volume, compile_mode: row.compile_mode, internal_deadline: deadline || null, separate_seal: row.separate_seal,
      page_numbering: row.page_numbering, blind_bid: row.blind_bid, cover_template: row.cover_template?.trim() || null, submit_file_name: name || null };
  }) };
}

export function fullValuePayload(categories: string[], basisIds: string[]) {
  if (categories.length && !basisIds.length) throw new Error('勾选需填完整值的类别须选择依据的招标要求。');
  return { categories, basis_requirement_ids: categories.length ? basisIds : [] };
}

/** 完整值类别只有项目负责人可勾选（后台同样校验）；其他人只读 */
export const canConfirmFullValue = (permissions?: { manage_project?: boolean }) => permissions?.manage_project === true;

/** 概览待办：现有流程待办之后追加后台给出的待办，每项可一键跳转到对应页签 */
export function mergeTodoItems<T extends { tab: string; title: string }>(base: T[], extra: SettingsTodo[]): Array<T | { title: string; detail: string; tab: string; done: false }> {
  return [...base, ...extra.map(item => ({ title: item.title, detail: item.detail, tab: item.tab, done: false as const }))];
}
