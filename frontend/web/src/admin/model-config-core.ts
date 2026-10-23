// 为什么有这个文件：提取大模型配置的核心纯逻辑、类型定义与合规校验规则。
// 它解决什么问题：落实 PRD §6.4、§6.6.1 与 APP-M2-T036、T037，保证敏感项目本地模型规则一致性与密钥更新语义。

export interface ModelConfigItem {
  id: string;
  name: string;
  provider: string;
  base_url: string;
  model: string;
  is_local: boolean;
  allow_sensitive: boolean;
  stream_enabled: boolean;
  json_mode_enabled: boolean;
  revision: number;
  has_api_key: boolean;
  api_key_masked?: string | null;
  timeout_seconds: number;
  max_tokens: number;
}

export interface ModelConfigValidationResult {
  valid: boolean;
  errors: Record<string, string>;
}

/**
 * 校验模型配置参数合法性
 */
export function validateModelConfig(values: Partial<ModelConfigItem>): ModelConfigValidationResult {
  const errors: Record<string, string> = {};

  if (!values.name || !values.name.trim()) {
    errors.name = '配置名称不能为空';
  }

  if (!values.base_url || !values.base_url.trim()) {
    errors.base_url = '服务 Base URL 不能为空';
  } else {
    try {
      const parsed = new URL(values.base_url.trim());
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        errors.base_url = '服务地址协议必须为 http 或 https';
      }
    } catch {
      errors.base_url = '服务地址格式不合法';
    }
  }

  if (!values.model || !values.model.trim()) {
    errors.model = '模型标识不能为空';
  }

  const timeout = Number(values.timeout_seconds);
  if (isNaN(timeout) || timeout <= 0 || timeout > 600) {
    errors.timeout_seconds = '超时时间需在 1 到 600 秒之间';
  }

  const maxTokens = Number(values.max_tokens);
  if (isNaN(maxTokens) || maxTokens < 1 || maxTokens > 1_000_000) {
    errors.max_tokens = 'Max Tokens 需在 1 到 1,000,000 之间';
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * 判断模型是否满足涉密与敏感项目的合规要求（PRD §6.4）
 */
export function isModelAllowedForSensitiveProject(config: Partial<ModelConfigItem>): boolean {
  return Boolean(config.is_local && config.allow_sensitive);
}

/**
 * 构造模型更新 Payload，精确遵守密钥更新四项语义（省略/空/掩码/新密钥）
 */
export function buildModelUpdatePayload(
  values: Record<string, unknown>,
  currentConfig?: ModelConfigItem | null
): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    name: values.name,
    provider: values.provider,
    base_url: values.base_url,
    model: values.model,
    is_local: Boolean(values.is_local),
    allow_sensitive: Boolean(values.allow_sensitive),
    stream_enabled: Boolean(values.stream_enabled),
    json_mode_enabled: Boolean(values.json_mode_enabled),
    timeout_seconds: Number(values.timeout_seconds),
    max_tokens: Number(values.max_tokens),
  };

  if (values.api_key !== undefined) {
    const rawKey = String(values.api_key);
    if (rawKey === '') {
      payload.api_key = ''; // 清除
    } else if (currentConfig?.api_key_masked && rawKey === currentConfig.api_key_masked) {
      // 保持原密钥不变，不传入或传回掩码
      payload.api_key = currentConfig.api_key_masked;
    } else {
      payload.api_key = rawKey; // 传入新密钥加密
    }
  }

  return payload;
}
