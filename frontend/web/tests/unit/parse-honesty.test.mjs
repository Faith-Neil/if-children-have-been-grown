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
