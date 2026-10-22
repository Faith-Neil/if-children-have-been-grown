// 为什么有这个文件：验证元数据驱动表单的核心纯函数、★关键字段变更检测算法与字段置灰门禁。
// 它解决什么问题：
// 1. 验证 areValuesEquivalent 值等价比对规则；
// 2. 验证 getModifiedStarredFields 与 hasModifiedStarredFields 能精准捕捉 ★ 关键字段修改并忽略非关键字段；
// 3. 验证 formatStarredWarning 生成符合合规规范（§5.2.2 与 PRD §5.12）的重核警示文案；
// 4. 验证 resolveFieldDisabledState 对不支持字段（supported: false）、系统只读（editable: false）与无权限用户的置灰与原因输出；
// 5. 验证 resolveTwoLineLabel 双行标签数据模型与内置 FormSchema 完整性。

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  areValuesEquivalent,
  getModifiedStarredFields,
  hasModifiedStarredFields,
  formatStarredWarning,
  resolveFieldDisabledState,
  resolveTwoLineLabel,
  resolveFormSchema,
  FALLBACK_ORG_ENTITY_FORM_SCHEMA,
  FALLBACK_PROJECT_FORM_SCHEMA,
  BUILTIN_FORM_SCHEMAS,
  fetchFieldMetadata,
} from '../../frontend/web/src/metadata-form.ts';

/* ========================================================================= */
/* 1. 值等价性比对函数测试                                                   */
/* ========================================================================= */

test('areValuesEquivalent handles null, undefined, whitespace, numbers, and booleans', () => {
  // 空值等价
  assert.equal(areValuesEquivalent('', null), true);
  assert.equal(areValuesEquivalent(null, undefined), true);
  assert.equal(areValuesEquivalent('   ', ''), true);

  // 相同内容等价
  assert.equal(areValuesEquivalent('中国通信建设第三工程局有限公司', '中国通信建设第三工程局有限公司'), true);
  assert.equal(areValuesEquivalent(' 91110000100000000A ', '91110000100000000A'), true);
  assert.equal(areValuesEquivalent(100, 100), true);
  assert.equal(areValuesEquivalent(true, true), true);

  // 差异内容不等价
  assert.equal(areValuesEquivalent('旧主体', '新主体'), false);
  assert.equal(areValuesEquivalent('91110000100000000A', '91110000100000000B'), false);
  assert.equal(areValuesEquivalent(100, 200), false);
  assert.equal(areValuesEquivalent(true, false), false);
});

/* ========================================================================= */
/* 2. ★ 关键字段修改检测引擎测试（规范 §5.2.2、PRD §5.12）                   */
/* ========================================================================= */

test('getModifiedStarredFields accurately captures changes to starred fields only', () => {
  const fields = [
    { field_key: 'entity_name', label: '主体名称', data_type: 'string', is_starred: true },
    { field_key: 'credit_code', label: '统一代码', data_type: 'string', is_starred: true },
    { field_key: 'short_name', label: '主体简称', data_type: 'string', is_starred: false },
    { field_key: 'remarks', label: '备注说明', data_type: 'string', is_starred: false },
  ];

  const initialValues = {
    entity_name: '中通建三局',
    credit_code: '91110000100000000A',
    short_name: '中通三',
    remarks: '原备注',
  };

  // 1. 未修改任何字段
  assert.equal(hasModifiedStarredFields(initialValues, initialValues, fields), false);
  assert.deepEqual(getModifiedStarredFields(initialValues, initialValues, fields), []);

  // 2. 仅修改非关键字段（short_name、remarks）：不触发 ★ 字段修改
  const nonStarredChange = {
    ...initialValues,
    short_name: '新中通三',
    remarks: '新备注修改',
  };
  assert.equal(hasModifiedStarredFields(initialValues, nonStarredChange, fields), false);
  assert.deepEqual(getModifiedStarredFields(initialValues, nonStarredChange, fields), []);

  // 3. 修改单个关键字段（entity_name）：触发告警并提取详情
  const starredChangeOne = {
    ...initialValues,
    entity_name: '中通建设发展有限公司',
  };
  assert.equal(hasModifiedStarredFields(initialValues, starredChangeOne, fields), true);
  const modifiedOne = getModifiedStarredFields(initialValues, starredChangeOne, fields);
  assert.equal(modifiedOne.length, 1);
  assert.equal(modifiedOne[0].field_key, 'entity_name');
  assert.equal(modifiedOne[0].label, '主体名称');
  assert.equal(modifiedOne[0].initialValue, '中通建三局');
  assert.equal(modifiedOne[0].currentValue, '中通建设发展有限公司');

  // 4. 同时修改两个关键字段
  const starredChangeBoth = {
    ...initialValues,
    entity_name: '新公司名称',
    credit_code: '91110000100000000B',
  };
  const modifiedBoth = getModifiedStarredFields(initialValues, starredChangeBoth, fields);
  assert.equal(modifiedBoth.length, 2);
  const keys = modifiedBoth.map((f) => f.field_key);
  assert.ok(keys.includes('entity_name'));
  assert.ok(keys.includes('credit_code'));

  // 5. 将值改回原初始值：自动解除修改标记
  const restoredChange = {
    ...initialValues,
    entity_name: '中通建三局',
  };
  assert.equal(hasModifiedStarredFields(initialValues, restoredChange, fields), false);
});

/* ========================================================================= */
/* 3. ★ 关键字段合规警示文案生成测试                                        */
/* ========================================================================= */

test('formatStarredWarning generates compliant warning banner message', () => {
  // 无修改时返回空字符串
  assert.equal(formatStarredWarning([]), '');

  const modified = [
    { field_key: 'entity_name', label: '主体名称', initialValue: 'A', currentValue: 'B' },
    { field_key: 'legal_representative', label: '法定代表人', initialValue: '张三', currentValue: '李四' },
  ];

  const warning = formatStarredWarning(modified);
  assert.match(warning, /★ 关键字段（主体名称、法定代表人）已被修改/);
  assert.match(warning, /§5\.2\.2/);
  assert.match(warning, /待确认/);
  assert.match(warning, /重新核对确认/);
});

/* ========================================================================= */
/* 4. 字段置灰（Disabled / Readonly）状态与原因判定测试                      */
/* ========================================================================= */

test('resolveFieldDisabledState handles unsupported, readonly, and permission restrictions', () => {
  // 1. 正常可编辑字段
  const normalField = { field_key: 'title', label: '标题', data_type: 'string', supported: true, editable: true };
  const normalState = resolveFieldDisabledState(normalField, true);
  assert.equal(normalState.disabled, false);
  assert.equal(normalState.reason, null);

  // 2. 当前版本未支持字段（supported: false）：自动置灰并展示原因
  const unsupportedField = {
    field_key: 'bank_account_hash',
    label: '基本户指纹',
    data_type: 'string',
    supported: false,
    disabledReason: '二期自动化生成指纹，暂不支持手填',
  };
  const unsupportedState = resolveFieldDisabledState(unsupportedField, true);
  assert.equal(unsupportedState.disabled, true);
  assert.equal(unsupportedState.reason, '二期自动化生成指纹，暂不支持手填');

  // 未指定具体原因时的默认提示
  const unsupportedDefault = { field_key: 'test_key', label: '未支持', data_type: 'string', supported: false };
  assert.match(resolveFieldDisabledState(unsupportedDefault, true).reason, /当前系统版本暂未开放/);

  // 3. 系统计算或只读字段（editable: false）：自动置灰
  const systemReadonlyField = {
    field_key: 'auto_id',
    label: '系统编号',
    data_type: 'string',
    supported: true,
    editable: false,
  };
  const readonlyState = resolveFieldDisabledState(systemReadonlyField, true);
  assert.equal(readonlyState.disabled, true);
  assert.match(readonlyState.reason, /不可人工编辑/);

  // 4. 用户无编辑权限（userCanEdit: false）：全字段置灰
  const noPermState = resolveFieldDisabledState(normalField, false);
  assert.equal(noPermState.disabled, true);
  assert.match(noPermState.reason, /无编辑权限/);
});

/* ========================================================================= */
/* 5. 双行标签纯数据模型解析测试                                             */
/* ========================================================================= */

test('resolveTwoLineLabel generates primary and secondary labels with starred flag', () => {
  // 1. 包含系统键与 ★ 关键字段
  const starredField = {
    field_key: 'entity_name',
    label: '主体名称',
    system_key: 'entity_name',
    data_type: 'string',
    is_starred: true,
    required: true,
    description: '营业执照主体名称',
  };
  const labelObj = resolveTwoLineLabel(starredField);
  assert.equal(labelObj.primary, '主体名称');
  assert.equal(labelObj.secondary, 'entity_name');
  assert.equal(labelObj.isStarred, true);
  assert.equal(labelObj.required, true);
  assert.equal(labelObj.tooltipText, '营业执照主体名称');

  // 2. 无系统键时退化为 field_key
  const noSysKeyField = {
    field_key: 'credit_code',
    label: '统一社会信用代码',
    data_type: 'string',
    is_starred: false,
    required: false,
  };
  const labelObj2 = resolveTwoLineLabel(noSysKeyField);
  assert.equal(labelObj2.secondary, 'credit_code');
  assert.equal(labelObj2.isStarred, false);
});

/* ========================================================================= */
/* 6. 内置 FormSchema 与解析器测试                                           */
/* ========================================================================= */

test('resolveFormSchema returns valid schemas for org_entity and project', () => {
  // 1. 公司主体 Schema 验证
  const orgSchema = resolveFormSchema('org_entity');
  assert.equal(orgSchema.category, 'org_entity');
  assert.ok(orgSchema.fields.some((f) => f.field_key === 'entity_name' && f.is_starred));
  assert.ok(orgSchema.fields.some((f) => f.field_key === 'credit_code' && f.is_starred));
  assert.ok(orgSchema.fields.some((f) => f.field_key === 'bank_account_hash' && f.supported === false));

  // 2. 投标项目 Schema 验证
  const projSchema = resolveFormSchema('project');
  assert.equal(projSchema.category, 'project');
  assert.ok(projSchema.fields.some((f) => f.field_key === 'project_name' && f.is_starred));
  assert.ok(projSchema.fields.some((f) => f.field_key === 'bid_deadline_at' && f.is_starred));
  assert.ok(projSchema.fields.some((f) => f.field_key === 'is_sensitive' && f.data_type === 'boolean'));

  // 3. 未知 category 兜底
  const fallback = resolveFormSchema('unknown_category');
  assert.equal(fallback.category, 'unknown_category');
  assert.ok(fallback.fields.length >= 2);

  // 4. fetchFieldMetadata 离线降级
  return fetchFieldMetadata('org_entity').then((schema) => {
    assert.equal(schema.category, 'org_entity');
    assert.ok(schema.fields.length > 0);
  });
});
