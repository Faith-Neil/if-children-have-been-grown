// 为什么有这个文件：提供企业设置与安全策略的标准化前端 API 交互胶水层（APP-M2-T025 / INT-COMPANY-SETTINGS-RBAC-GLUE）。
// 它解决什么问题：
// 1. 对齐 /api/v1/companies/{company_id}/settings 后端契约；
// 2. 统一处理 Bearer Token 传递与 RFC 7807 统一错误响应解析（SETTING_VALUE_OUT_OF_BOUNDS、FORBIDDEN、NOT_FOUND）；
// 3. 为企业设置页面与端到端集成测试提供类型安全的数据请求接口。

import { request, ApiError } from '../shared/api.ts';

export interface ApiCompanySettings {
  company_id: string;
  company_name: string;
  password_min_length: number;
  password_min_char_classes: number;
  max_login_attempts: number;
  session_timeout_minutes: number;
  edit_lock_timeout_minutes: number;
  edit_lock_heartbeat_seconds: number;
  editor_autosave_seconds: number;
  loop_max_rounds: number;
  assistant_suggestion_count: number;
  assistant_enabled: boolean;
  assistant_kb_default: boolean;
  assistant_allow_kb_off: boolean;
  model_review_enabled: boolean;
  dup_min_chars: number;
  dup_history_months: number;
  updated_at?: string | null;
  updated_by?: string | null;
  custom_settings?: Record<string, unknown>;
}

export interface ApiUpdateCompanySettingsPayload {
  company_name?: string;
  password_min_length?: number;
  password_min_char_classes?: number;
  max_login_attempts?: number;
  session_timeout_minutes?: number;
  edit_lock_timeout_minutes?: number;
  edit_lock_heartbeat_seconds?: number;
  editor_autosave_seconds?: number;
  loop_max_rounds?: number;
  assistant_suggestion_count?: number;
  assistant_enabled?: boolean;
  assistant_kb_default?: boolean;
  assistant_allow_kb_off?: boolean;
  model_review_enabled?: boolean;
  dup_min_chars?: number;
  dup_history_months?: number;
  custom_settings?: Record<string, unknown>;
}

/**
 * 获取指定企业的配置与安全策略
 */
export async function fetchCompanySettings(companyId: string, token: string | null): Promise<ApiCompanySettings> {
  return request<ApiCompanySettings>(`/api/v1/companies/${encodeURIComponent(companyId)}/settings`, token, 'GET');
}

/**
 * 更新指定企业的配置与安全策略
 */
export async function updateCompanySettings(
  companyId: string,
  payload: ApiUpdateCompanySettingsPayload,
  token: string | null
): Promise<ApiCompanySettings> {
  return request<ApiCompanySettings>(
    `/api/v1/companies/${encodeURIComponent(companyId)}/settings`,
    token,
    'PATCH',
    payload
  );
}
