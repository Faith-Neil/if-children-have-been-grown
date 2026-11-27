import test from 'node:test';
import assert from 'node:assert/strict';

import { parseHonesty } from '../../src/project/parse-honesty.ts';

test('完整抽取不像降质', () => {
  const result = parseHonesty({ extract_degraded: false, outline_source: 'model' });
  assert.equal(result.degraded, false);
  assert.equal(result.text, '');
});

test('抽取超时和目录兜底都写进可见说明', () => {
  const result = parseHonesty({
    extract_degraded: true,
    extract_timeout_count: 12,
    extract_pages_read: 8,
    outline_source: 'rule_fallback',
    tree_model_failed: true,
  });
  assert.equal(result.degraded, true);
  assert.match(result.text, /12 块超时/);
  assert.match(result.text, /只读完 8 块/);
  assert.match(result.text, /规则兜底/);
});

test('规则目录带原因时把原因写出来', () => {
  const result = parseHonesty({
    outline_source: 'rule',
    technical_outline: { outline_source: 'rule', outline_reason: '模型正在编排目录，当前是规则草稿。' },
  });
  assert.equal(result.degraded, true);
  assert.equal(result.text, '模型正在编排目录，当前是规则草稿。');
});

test('模型目录不显示残留原因', () => {
  const result = parseHonesty({ outline_source: 'model', outline_reason: '模型正在编排目录，当前是规则草稿。' });
  assert.equal(result.degraded, false);
});

test('includeOutline=false 时目录失败原因不再重复（由重新生成目录告警承担）', () => {
  const input = {
    extract_degraded: true,
    extract_timeout_count: 12,
    extract_pages_read: 8,
    outline_source: 'rule_fallback',
    tree_model_failed: true,
    outline_reason: '模型拟目录失败（超时），已用规则目录。',
  };
  const excluded = parseHonesty(input, { includeOutline: false });
  assert.equal(excluded.degraded, true);
  assert.match(excluded.text, /12 块超时/);
  assert.doesNotMatch(excluded.text, /规则兜底|规则目录/);

  // 默认行为不变：不传选项时目录原因照常出现
  const included = parseHonesty(input);
  assert.match(included.text, /已用规则目录/);
});

test('includeOutline=false 且没有抽取降质时整体不算降质', () => {
  const result = parseHonesty({ outline_source: 'rule_fallback', tree_model_failed: true }, { includeOutline: false });
  assert.equal(result.degraded, false);
  assert.equal(result.text, '');
});
