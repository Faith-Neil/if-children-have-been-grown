// 为什么有这个文件：测试表单通用交互纯逻辑（脏数据检测、服务端字段错误映射与离开拦截）。
// 它解决什么问题：
// 1. 验证 detectDirtyFields 精确识别已修改项数与 ★ 关键字段变更统计；
// 2. 验证 mapServerFieldErrors 完整解析不同结构的服务端错误体（details 数组、字典映射、单字段对象、嵌套 error）；
// 3. 验证 firstErrorField 提取与 scrollFieldIntoView 在 DOM 与 Node 环境下的安全性；
// 4. 验证 shouldBlockNavigation 与 applyBeforeUnloadEvent 的拦截规则。

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  areValuesEquivalent,
  detectDirtyFields,
  mapServerFieldErrors,
  scrollFieldIntoView,
  shouldBlockNavigation,
  applyBeforeUnloadEvent,
  FORM_LEAVE_COPY,
} from '../../frontend/web/src/form-interactions.ts';

test('areValuesEquivalent safely compares various scalar and array types', () => {
  // 1. null 与 undefined 与 空串视为等价
  assert.equal(areValuesEquivalent(null, undefined), true);
  assert.equal(areValuesEquivalent('', null), true);
  assert.equal(areValuesEquivalent('', undefined), true);
  assert.equal(areValuesEquivalent('   ', ''), true);

  // 2. 字符串两端空白符归一化
  assert.equal(areValuesEquivalent('华东数智', '  华东数智  '), true);
  assert.equal(areValuesEquivalent('华东数智', '华东数智科技'), false);

  // 3. 数值与布尔
  assert.equal(areValuesEquivalent(100, 100), true);
  assert.equal(areValuesEquivalent(100, 200), false);
  assert.equal(areValuesEquivalent(true, true), true);
  assert.equal(areValuesEquivalent(true, false), false);

  // 4. 数组元素深度比对
  assert.equal(areValuesEquivalent(['A', 'B'], ['A', 'B']), true);
  assert.equal(areValuesEquivalent(['A', 'B'], ['A', 'C']), false);
  assert.equal(areValuesEquivalent(['A'], ['A', 'B']), false);
});

test('detectDirtyFields accurately computes modified count and starred fields', () => {
  const initial = {
    entity_name: '华东数智科技股份有限公司',
    credit_code: '91310000X000000001',
    legal_rep: '张三',
    registered_capital: 5000,
    is_active: true,
  };

  const starredKeys = ['entity_name', 'credit_code'];

  // 场景 1: 未修改任何字段
  const cleanSummary = detectDirtyFields(initial, { ...initial }, starredKeys);
  assert.equal(cleanSummary.isDirty, false);
  assert.equal(cleanSummary.modifiedCount, 0);
  assert.deepEqual(cleanSummary.modifiedKeys, []);
  assert.equal(cleanSummary.starredModifiedCount, 0);
  assert.equal(cleanSummary.summaryText, '表单内容与初始版本一致');

  // 场景 2: 修改非关键字段（如 registered_capital）
  const modifiedNonStarred = {
    ...initial,
    registered_capital: 6000,
  };
  const summaryNonStarred = detectDirtyFields(initial, modifiedNonStarred, starredKeys);
  assert.equal(summaryNonStarred.isDirty, true);
  assert.equal(summaryNonStarred.modifiedCount, 1);
  assert.deepEqual(summaryNonStarred.modifiedKeys, ['registered_capital']);
  assert.equal(summaryNonStarred.starredModifiedCount, 0);
  assert.equal(summaryNonStarred.summaryText, '已修改 1 项');

  // 场景 3: 修改了 ★ 关键字段（如 entity_name 与 credit_code）
  const modifiedStarred = {
    ...initial,
    entity_name: '华东数智信息集团',
    registered_capital: 8000,
  };
  const summaryStarred = detectDirtyFields(initial, modifiedStarred, starredKeys);
  assert.equal(summaryStarred.isDirty, true);
  assert.equal(summaryStarred.modifiedCount, 2);
  assert.ok(summaryStarred.modifiedKeys.includes('entity_name'));
  assert.ok(summaryStarred.modifiedKeys.includes('registered_capital'));
  assert.equal(summaryStarred.starredModifiedCount, 1);
  assert.deepEqual(summaryStarred.starredModifiedKeys, ['entity_name']);
  assert.equal(summaryStarred.summaryText, '已修改 2 项（含 1 项 ★ 关键字段）');
});

test('mapServerFieldErrors parses direct field error objects', () => {
  const directError = {
    code: 'VALIDATION_FAILED',
    message: '法定代表人姓名格式不正确',
    field: 'legal_representative',
  };

  const mapped = mapServerFieldErrors(directError);
  assert.equal(mapped.generalMessage, '法定代表人姓名格式不正确');
  assert.equal(mapped.firstErrorField, 'legal_representative');
  assert.deepEqual(mapped.fieldErrors, [
    { name: 'legal_representative', errors: ['法定代表人姓名格式不正确'] },
  ]);
});

test('mapServerFieldErrors parses details array from FastAPI / Pydantic style errors', () => {
  const pydanticError = {
    message: '请求参数验证失败',
    details: [
      { field: 'credit_code', message: '统一社会信用代码必须为18位' },
      { loc: ['body', 'business_term_end'], msg: '营业期限必须是未来有效日期' },
    ],
  };

  const mapped = mapServerFieldErrors(pydanticError);
  assert.equal(mapped.generalMessage, '请求参数验证失败');
  assert.equal(mapped.firstErrorField, 'credit_code');
  assert.equal(mapped.fieldErrors.length, 2);
  assert.deepEqual(mapped.fieldErrors[0], {
    name: 'credit_code',
    errors: ['统一社会信用代码必须为18位'],
  });
  assert.deepEqual(mapped.fieldErrors[1], {
    name: 'business_term_end',
    errors: ['营业期限必须是未来有效日期'],
  });
});

test('mapServerFieldErrors parses dictionary details and nested error structures', () => {
  // 1. 字典格式
  const dictError = {
    message: '表单校验错误',
    details: {
      entity_name: '企业名称已存在',
      registered_capital: ['注册资本必须大于0'],
    },
  };

  const mappedDict = mapServerFieldErrors(dictError);
  assert.equal(mappedDict.firstErrorField, 'entity_name');
  assert.equal(mappedDict.fieldErrors.length, 2);
  assert.deepEqual(mappedDict.fieldErrors[0], {
    name: 'entity_name',
    errors: ['企业名称已存在'],
  });
  assert.deepEqual(mappedDict.fieldErrors[1], {
    name: 'registered_capital',
    errors: ['注册资本必须大于0'],
  });

  // 2. 嵌套结构
  const nestedError = {
    error: {
      field: 'tender_number',
      message: '招标编号不可重复',
    },
  };
  const mappedNested = mapServerFieldErrors(nestedError);
  assert.equal(mappedNested.firstErrorField, 'tender_number');
  assert.deepEqual(mappedNested.fieldErrors, [
    { name: 'tender_number', errors: ['招标编号不可重复'] },
  ]);

  // 3. 空值容错
  assert.deepEqual(mapServerFieldErrors(null), { fieldErrors: [], firstErrorField: null, generalMessage: null });
  assert.deepEqual(mapServerFieldErrors(undefined), { fieldErrors: [], firstErrorField: null, generalMessage: null });
});

test('scrollFieldIntoView handles missing DOM environment gracefully', () => {
  // 在 Node.js 环境下 document 未定义，应安全返回 false 而不抛错
  const scrolled = scrollFieldIntoView('non_existent_field');
  assert.equal(scrolled, false);
});

test('shouldBlockNavigation and applyBeforeUnloadEvent enforce leave protection rules', () => {
  // 1. clean 表单不拦截
  assert.equal(shouldBlockNavigation(false, false), false);
  assert.equal(shouldBlockNavigation(false, true), false);

  // 2. dirty 表单未确认时拦截，已确认时不拦截
  assert.equal(shouldBlockNavigation(true, false), true);
  assert.equal(shouldBlockNavigation(true, true), false);

  // 3. beforeunload 事件拦截
  const cleanEvent = { preventDefault() { this.prevented = true; }, returnValue: '', prevented: false };
  assert.equal(applyBeforeUnloadEvent(false, cleanEvent), false);
  assert.equal(cleanEvent.prevented, false);

  const dirtyEvent = { preventDefault() { this.prevented = true; }, returnValue: '', prevented: false };
  assert.equal(applyBeforeUnloadEvent(true, dirtyEvent), true);
  assert.equal(dirtyEvent.prevented, true);
  assert.equal(dirtyEvent.returnValue, FORM_LEAVE_COPY.content);
});
