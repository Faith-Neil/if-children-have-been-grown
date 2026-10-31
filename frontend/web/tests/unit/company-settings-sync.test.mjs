// 为什么有这个文件：验证企业设置页与后台设置的字段对应（PRD v1.8 §5.10.2、§5.11.9）。
// 它解决什么问题：页面保存原先什么都不存；这里确认后台字段原样往返，页面独有的项存进 custom_settings 能读回，
// 敏感项目本地模型与废标红线始终开启。
import test from 'node:test';
import assert from 'node:assert/strict';
import { settingsFromApi, settingsPayload } from '../../src/admin/company-settings-sync.ts';
import { buildInitialCompanySettings, validateCompanySettings } from '../../src/admin/company-settings-core.ts';

const api = {
  company_id: 'alpha', company_name: 'Alpha 科技', password_min_length: 12, password_min_char_classes: 4, max_login_attempts: 3,
  session_timeout_minutes: 60, edit_lock_timeout_minutes: 20, edit_lock_heartbeat_seconds: 30, editor_autosave_seconds: 10,
  loop_max_rounds: 3, assistant_suggestion_count: 5, assistant_enabled: false, assistant_kb_default: false, assistant_allow_kb_off: true,
  model_review_enabled: true, dup_min_chars: 10, dup_history_months: 36, parse_confidence_threshold: 0.9,
  custom_settings: { ui_outline_max_depth: 3, ui_custom_fields: [{ id: 'x', field_key: 'custom_x', field_name: 'X', field_type: 'text', required: false, scope: 'project' }] },
};

test('backend settings map onto the page and back', () => {
  const page = settingsFromApi(api);
  assert.equal(page.password_min_length, 12);
  assert.equal(page.max_login_attempts, 3);
  assert.equal(page.assistant_enabled, false);
  assert.equal(page.parse_confidence_threshold, 0.9);
  assert.equal(page.outline_max_depth, 3);
  assert.equal(page.outline_target_words_default, 3000); // 未保存过的页面项用平台默认
  assert.deepEqual(page.custom_fields.map(f => f.field_key), ['custom_x']);
  assert.equal(page.force_local_model, true);
  assert.equal(page.export_redline_blocking, true);
  const payload = settingsPayload(page);
  assert.equal(payload.edit_lock_timeout_minutes, 20);
  assert.equal(payload.assistant_suggestion_count, 5);
  assert.equal(payload.custom_settings.ui_outline_max_depth, 3);
  assert.equal(payload.custom_settings.ui_custom_fields[0].field_key, 'custom_x');
  assert.ok(!('force_local_model' in payload) && !('export_watermark_text' in payload));
});

test('page bounds follow the backend', () => {
  const base = buildInitialCompanySettings();
  assert.equal(validateCompanySettings({ ...base, edit_lock_timeout_minutes: 90 }).valid, false); // 后台上限 60
  assert.equal(validateCompanySettings({ ...base, session_timeout_minutes: 20 }).valid, false);   // 后台下限 30
  assert.equal(validateCompanySettings({ ...base, max_login_attempts: 6 }).valid, false);
  assert.equal(validateCompanySettings({ ...base, parse_confidence_threshold: 0.3 }).valid, false);
  assert.equal(validateCompanySettings(base).valid, true);
});
