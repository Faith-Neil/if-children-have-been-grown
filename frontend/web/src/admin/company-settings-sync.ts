// 为什么有这个文件：企业设置页与后台 /api/v1/companies/{id}/settings 之间的字段对应（PRD v1.8 §5.10.2、§5.11.9、§6.9）。
// 它解决什么问题：页面原先“保存”只弹提示、什么都不存；这里把后台返回的设置换成页面数据，把页面数据换成更新请求。
// 后台有同名字段的直接对应；大纲层级、默认篇幅、AI 上下文预算与自定义扩展字段后台还没有专门字段，
// 存在 custom_settings 的 ui_* 键里（保存后能读回，但生成流程尚未读取，进度表里登记为缺口）。

import { buildInitialCompanySettings, type CompanySettingsData, type CustomFieldMetadata } from './company-settings-core.ts';
import type { ApiCompanySettings, ApiUpdateCompanySettingsPayload } from './company-settings-api.ts';

const DIRECT = [
  'password_min_length', 'password_min_char_classes', 'max_login_attempts', 'session_timeout_minutes',
  'edit_lock_timeout_minutes', 'edit_lock_heartbeat_seconds', 'editor_autosave_seconds',
  'assistant_enabled', 'assistant_suggestion_count', 'assistant_kb_default', 'assistant_allow_kb_off',
  'dup_min_chars', 'dup_history_months', 'parse_confidence_threshold', 'assistant_paste_match_ratio',
] as const;
const STORED = {
  outline_max_depth: 'ui_outline_max_depth',
  outline_target_words_default: 'ui_outline_target_words_default',
  ai_token_budget_per_chapter: 'ui_ai_token_budget_per_chapter',
  custom_fields: 'ui_custom_fields',
} as const;

export function settingsFromApi(api: ApiCompanySettings): CompanySettingsData {
  const base = buildInitialCompanySettings(api.company_id, api.company_name || api.company_id);
  const result: Record<string, unknown> = { ...base, company_name: api.company_name || base.company_name };
  for (const key of DIRECT) {
    const value = (api as unknown as Record<string, unknown>)[key];
    if (value !== undefined && value !== null) result[key] = value;
  }
  const custom = api.custom_settings ?? {};
  for (const [field, stored] of Object.entries(STORED)) {
    if (custom[stored] !== undefined) result[field] = custom[stored];
  }
  // 敏感项目只用本地模型、废标红线阻断由系统强制，不由公司设置开关
  result.force_local_model = true;
  result.export_redline_blocking = true;
  return result as unknown as CompanySettingsData;
}

export function settingsPayload(data: CompanySettingsData): ApiUpdateCompanySettingsPayload {
  const payload: Record<string, unknown> = {};
  for (const key of DIRECT) payload[key] = data[key];
  const custom: Record<string, unknown> = {};
  for (const [field, stored] of Object.entries(STORED)) {
    const value = (data as unknown as Record<string, unknown>)[field];
    custom[stored] = field === 'custom_fields' ? (value as CustomFieldMetadata[]).map(f => ({ ...f })) : value;
  }
  payload.custom_settings = custom;
  return payload as ApiUpdateCompanySettingsPayload;
}
