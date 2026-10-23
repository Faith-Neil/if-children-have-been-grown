// 为什么有这个文件：提取 RAGFlow 知识库配置的核心纯逻辑、类型定义与合规校验规则。
// 它解决什么问题：落实用户拍板决策与 PRD §6.2，验证知识库服务地址、Dataset IDs 解析与更新载荷规范。

export interface RagflowConfigData {
  company_id: string;
  base_url: string;
  has_api_key: boolean;
  api_key_masked?: string | null;
  dataset_ids: string[];
  timeout_seconds: number;
  is_enabled: boolean;
  revision: number;
}

export interface RagflowValidationResult {
  valid: boolean;
  errors: Record<string, string>;
}

/**
 * 解析并规范化 Dataset IDs 字符串列表
 */
export function parseDatasetIds(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.map(d => String(d).trim()).filter(Boolean);
  }
  if (typeof raw === 'string') {
    return raw
      .split(/[,，\n]/)
      .map(d => d.trim())
      .filter(Boolean);
  }
  return [];
}

/**
 * 校验 RAGFlow 配置参数合法性
 */
export function validateRagflowConfig(values: Partial<RagflowConfigData> & { dataset_ids?: unknown }): RagflowValidationResult {
  const errors: Record<string, string> = {};

  if (!values.base_url || !values.base_url.trim()) {
    errors.base_url = 'RAGFlow 服务地址不能为空';
  } else {
    try {
      const parsed = new URL(values.base_url.trim());
      if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
        errors.base_url = '服务地址协议必须为 http 或 https';
      }
      if (parsed.search || parsed.hash) {
        errors.base_url = '服务地址不能包含 query 或 fragment';
      }
    } catch {
      errors.base_url = '服务地址格式不合法';
    }
  }

  const datasets = parseDatasetIds(values.dataset_ids);
  if (datasets.length === 0) {
    errors.dataset_ids = '请至少配置一个知识库数据集 (Dataset ID)';
  }

  const timeout = Number(values.timeout_seconds);
  if (isNaN(timeout) || timeout < 1 || timeout > 300) {
    errors.timeout_seconds = '超时时间需在 1 到 300 秒之间';
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * 构造 RAGFlow 更新 Payload
 */
export function buildRagflowUpdatePayload(
  values: Record<string, unknown>,
  currentConfig?: RagflowConfigData | null
): Record<string, unknown> {
  const datasetList = parseDatasetIds(values.dataset_ids);

  const payload: Record<string, unknown> = {
    base_url: String(values.base_url || '').trim().replace(/\/+$/, ''),
    dataset_ids: datasetList,
    timeout_seconds: Number(values.timeout_seconds || 30),
    is_enabled: Boolean(values.is_enabled),
  };

  if (values.api_key !== undefined) {
    const rawKey = String(values.api_key);
    if (rawKey === '') {
      payload.api_key = ''; // 清除
    } else if (currentConfig?.api_key_masked && rawKey === currentConfig.api_key_masked) {
      payload.api_key = currentConfig.api_key_masked; // 保持掩码
    } else {
      payload.api_key = rawKey; // 传入新密钥
    }
  }

  return payload;
}
