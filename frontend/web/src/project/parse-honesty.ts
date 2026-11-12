// 为什么有这个文件：解析完成页要能区分完整抽取和降质结果。
// 它解决什么问题：抽取大面积超时或目录模型失败后，覆盖视图和解析状态不能再显示成完整成功。

export type ParseHonestyInput = {
  extract_degraded?: boolean;
  extract_timeout_count?: number;
  extract_pages_read?: number;
  outline_source?: string;
  tree_model_failed?: boolean;
  technical_outline?: { outline_source?: string; tree_model_failed?: boolean } | null;
};

export function parseHonesty(input: ParseHonestyInput): { degraded: boolean; text: string } {
  const lines: string[] = [];
  if (input.extract_degraded) {
    const timeouts = input.extract_timeout_count ?? 0;
    const read = input.extract_pages_read ?? 0;
    lines.push(`抽取降质：${timeouts} 块超时，只读完 ${read} 块。`);
  }
  const source = input.outline_source || input.technical_outline?.outline_source || '';
  const treeFailed = Boolean(
    input.tree_model_failed
    || input.technical_outline?.tree_model_failed
    || source === 'rule_fallback',
  );
  if (treeFailed) {
    lines.push('目录是规则兜底，模型编排目录失败。');
  }
  return { degraded: lines.length > 0, text: lines.join('') };
}
