// 为什么有这个文件：平台安全策略保存的纯计算部分（ISSUE-059 组1c）。
// 它解决什么问题：后端 PATCH /api/v1/platform/security-settings 是合并语义（仅上行字段参与覆盖），
// 因此前端只应提交相对服务端快照真正改动的字段——未编辑的字段绝不上行，既不覆盖其他管理员
// 并发修改的同名字段，也不会用前端默认值冲掉服务端已保存但前端未建模的策略项。

export interface SecuritySettingsValues {
  password_min_length: number;
  password_min_char_classes: number;
  max_login_attempts: number;
  session_timeout_minutes: number;
}

export const SECURITY_SETTINGS_KEYS = [
  'password_min_length',
  'password_min_char_classes',
  'max_login_attempts',
  'session_timeout_minutes',
] as const;

export type SecuritySettingsKey = (typeof SECURITY_SETTINGS_KEYS)[number];

/**
 * 计算相对服务端快照真正改动的字段。
 * 只返回值的变了的键；未变化或快照中不存在的键一律不上行。
 */
export function changedSecurityFields(
  baseline: SecuritySettingsValues,
  draft: SecuritySettingsValues,
): Partial<SecuritySettingsValues> {
  const changed: Partial<SecuritySettingsValues> = {};
  for (const key of SECURITY_SETTINGS_KEYS) {
    if (draft[key] !== baseline[key]) changed[key] = draft[key];
  }
  return changed;
}

/** 是否存在未保存修改；无修改时保存按钮应禁用，避免空写更新 updated_at/updated_by。 */
export function hasSecurityChanges(
  baseline: SecuritySettingsValues,
  draft: SecuritySettingsValues,
): boolean {
  return SECURITY_SETTINGS_KEYS.some(key => draft[key] !== baseline[key]);
}

/**
 * 保存前置门禁：只有已成功读回服务端快照（baseline 非空）且未在加载中时才允许保存。
 * GET 尚未完成或失败时严禁保存——彼时表单里只是前端默认值，保存即覆盖事故。
 */
export function canSaveSecuritySettings(state: {
  baseline: SecuritySettingsValues | null;
  draft: SecuritySettingsValues;
  loading: boolean;
  saving: boolean;
}): boolean {
  if (!state.baseline || state.loading || state.saving) return false;
  return hasSecurityChanges(state.baseline, state.draft);
}
