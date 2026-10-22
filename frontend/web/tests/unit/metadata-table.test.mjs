// 为什么有这个文件：验证元数据驱动表格的核心纯函数、行合并算法、1280px 宽度预算引擎与合规门禁。
// 它解决什么问题：
// 1. 验证 calculateRowSpans 动态单元格合并（连续相同值首行计数，后续行置 0）；
// 2. 验证 calculateColumnWidthBudget 在 1280px 标准桌面宽度（1040px 内容宽）下实现无横向滚动优先；
// 3. 验证 canBatchConfirm 严格落地合规规范 §5.2.2 与设计规范 9.1 规则 6（星号/废标/资格禁止批量确认）；
// 4. 验证 isRiskRow 风险行浅红底判定（规范 9.1 规则 4）与 isUrgentRow 3 天截止判定；
// 5. 验证 formatDateTimeMonospace 等宽时间格式化与内置 Mock 元数据 Schema 完整性。

import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  calculateRowSpans,
  calculateColumnWidthBudget,
  canBatchConfirm,
  isRiskRow,
  isUrgentRow,
  formatDateTimeMonospace,
  resolveTableMeta,
  STANDARD_TABLE_AVAILABLE_WIDTH,
  REQUIREMENTS_MATRIX_SCHEMA,
  LIBRARY_RECORDS_SCHEMA,
  FACTS_MATRIX_SCHEMA,
  BUILTIN_TABLE_SCHEMAS,
} from '../../src/library/metadata-table.ts';

/* ========================================================================= */
/* 1. 动态单元格纵向合并（rowSpan）算法验证                                  */
/* ========================================================================= */

test('calculateRowSpans properly computes rowSpan for consecutive identical values', () => {
  // 空数据
  assert.deepEqual(calculateRowSpans([], 'category'), []);

  // 单行数据
  assert.deepEqual(calculateRowSpans([{ category: '资质' }], 'category'), [1]);

  // 连续分类合并
  const data = [
    { id: 1, category: '资质' },
    { id: 2, category: '资质' },
    { id: 3, category: '人员' },
    { id: 4, category: '人员' },
    { id: 5, category: '人员' },
    { id: 6, category: '业绩' },
  ];
  const spans = calculateRowSpans(data, 'category');
  assert.deepEqual(spans, [2, 0, 3, 0, 0, 1], 'first occurrence has count N, subsequent occurrences have 0');

  // 支持函数式取值访问器
  const getterSpans = calculateRowSpans(data, (item) => item.category);
  assert.deepEqual(getterSpans, [2, 0, 3, 0, 0, 1]);

  // 全不相同情况
  const uniqueData = [{ id: 1, val: 'A' }, { id: 2, val: 'B' }, { id: 3, val: 'C' }];
  assert.deepEqual(calculateRowSpans(uniqueData, 'val'), [1, 1, 1]);
});

/* ========================================================================= */
/* 2. 1280px 标准桌面宽度无横向滚动预算分配引擎验证                         */
/* ========================================================================= */

test('calculateColumnWidthBudget prioritizes zero horizontal scroll on 1280px screen', () => {
  // 1. 常规矩阵字段配置（要求矩阵 8 列：固定列总和约 790px，剩余 250px 分配给长文本列）
  const result = calculateColumnWidthBudget(
    REQUIREMENTS_MATRIX_SCHEMA.fields,
    STANDARD_TABLE_AVAILABLE_WIDTH // 1040px
  );

  assert.equal(result.availableWidth, 1040);
  assert.equal(result.fitsWithoutScroll, true, 'Standard matrix columns must fit within 1040px without horizontal scroll');
  assert.equal(result.scrollX, undefined, 'scroll.x should be undefined to avoid forcing horizontal scrollbar');

  // 长文本自适应列检查（requirement_text 与 our_response 动态分配了剩余宽度，且启用了 ellipsis 与 viewInDrawer）
  const longtextCols = result.columns.filter((col) => col.dataType === 'longtext');
  assert.equal(longtextCols.length, 2, 'two longtext columns (text & response)');
  for (const col of longtextCols) {
    assert.ok(col.isFlexible, 'longtext column is flexible');
    assert.equal(col.ellipsis, true, 'ellipsis must be true to prevent overflow');
    assert.equal(col.viewInDrawer, true, 'viewInDrawer must be true for drawer inspection');
    assert.ok(col.allocatedWidth >= 100, `allocated width ${col.allocatedWidth} must be sufficient`);
  }

  // 2. 超出预算时的优雅降级（例如配置过多宽列时开启横滚并固定首列和操作列）
  const wideFields = [
    { key: 'col1', label: '列1', dataType: 'text', width: 300 },
    { key: 'col2', label: '列2', dataType: 'text', width: 300 },
    { key: 'col3', label: '列3', dataType: 'text', width: 300 },
    { key: 'col4', label: '列4', dataType: 'text', width: 300 },
    { key: 'actions', label: '操作', dataType: 'actions', width: 120 },
  ];
  const overflowResult = calculateColumnWidthBudget(wideFields, 1040);
  assert.equal(overflowResult.fitsWithoutScroll, false, 'total width > 1040 results in fitsWithoutScroll = false');
  assert.ok(overflowResult.scrollX && overflowResult.scrollX > 1040, 'scroll.x is set to total required width');

  // 必须横滚时固定首列和操作列（规范 9.1 规则 2）
  assert.equal(overflowResult.columns[0].fixed, 'left', 'first column must be pinned left when scrolling');
  const actionCol = overflowResult.columns.find((c) => c.key === 'actions');
  assert.equal(actionCol.fixed, 'right', 'action column must be pinned right when scrolling');
});

/* ========================================================================= */
/* 3. 合规批量确认门禁校验（规范 9.1 规则 6 / 5.2.2）                         */
/* ========================================================================= */

test('canBatchConfirm disallows batch confirmation for star, blocker and qualification clauses', () => {
  // 1. 空选择或全为一般/加分/提示条款：允许批量确认
  assert.equal(canBatchConfirm([]).allowed, true);

  const safeRecords = [
    { id: 1, level: 'general', category: 'general', title: '一般要求 1' },
    { id: 2, level: 'bonus', category: 'bonus', title: '加分项 2' },
    { id: 3, level: 'hint', category: 'hint', title: '提示 3' },
  ];
  const safeRes = canBatchConfirm(safeRecords);
  assert.equal(safeRes.allowed, true);
  assert.equal(safeRes.nonBatchableCount, 0);
  assert.equal(safeRes.reasons.length, 0);

  // 2. 含有星号条款（★）：严禁批量确认（规范 §5.2.2）
  const starRecords = [
    { id: 1, level: 'general', category: 'general' },
    { id: 2, level: 'star', category: 'star' },
  ];
  const starRes = canBatchConfirm(starRecords);
  assert.equal(starRes.allowed, false);
  assert.equal(starRes.nonBatchableCount, 1);
  assert.match(starRes.reasons[0], /5\.2\.2/, 'reason cites section 5.2.2');
  assert.match(starRes.reasons[0], /星号/, 'reason mentions star clauses');

  // 3. 含有废标/阻断条款（blocker / disqualification）：严禁批量确认
  const blockerRecords = [
    { id: 1, level: 'blocker', category: 'blocker' },
  ];
  const blockerRes = canBatchConfirm(blockerRecords);
  assert.equal(blockerRes.allowed, false);
  assert.equal(blockerRes.nonBatchableCount, 1);

  // 4. 含有资格审查条款（qualification）：严禁批量确认
  const qualRecords = [
    { id: 1, level: 'qualification', category: 'qualification' },
    { id: 2, level: 'star', category: 'star' },
  ];
  const qualRes = canBatchConfirm(qualRecords);
  assert.equal(qualRes.allowed, false);
  assert.equal(qualRes.nonBatchableCount, 2);
});

/* ========================================================================= */
/* 4. 风险行浅红底（#FFF5F5）与急迫行判定规则（规范 9.1 规则 4）             */
/* ========================================================================= */

test('isRiskRow accurately identifies risk records requiring red background', () => {
  // 阻断与废标
  assert.equal(isRiskRow({ level: 'blocker' }), true);
  assert.equal(isRiskRow({ category: 'blocker' }), true);
  assert.equal(isRiskRow({ category: 'disqualification' }), true);

  // 证据失效或待审核
  assert.equal(isRiskRow({ status: 'pending' }), true);
  assert.equal(isRiskRow({ status: 'rejected' }), true);
  assert.equal(isRiskRow({ evidence_invalid: true }), true);
  assert.equal(isRiskRow({ risk: true }), true);

  // 已确认的正常条款不是风险行
  assert.equal(isRiskRow({ status: 'confirmed', level: 'general' }), false);

  // 支持外部传入自定义断言
  assert.equal(isRiskRow({ customFlag: true }, (item) => item.customFlag === true), true);
});

test('isUrgentRow detects deadline within 3 days for urgent highlight', () => {
  const baseTime = new Date('2026-10-21T12:00:00Z');

  // 截止日在 2 天后（<= 3 天）：属于急迫项目
  const urgentRecord = { deadline: '2026-10-23T12:00:00Z' };
  assert.equal(isUrgentRow(urgentRecord, 3, undefined, baseTime), true);

  // 截止日在 5 天后（> 3 天）：不属于急迫项目
  const normalRecord = { deadline: '2026-10-26T12:00:00Z' };
  assert.equal(isUrgentRow(normalRecord, 3, undefined, baseTime), false);

  // 无截止日期或格式错误
  assert.equal(isUrgentRow({}, 3, undefined, baseTime), false);
  assert.equal(isUrgentRow({ deadline: 'invalid-date' }, 3, undefined, baseTime), false);
});

/* ========================================================================= */
/* 5. 等宽时间格式化（规范 9.1 规则 3）                                      */
/* ========================================================================= */

test('formatDateTimeMonospace formats valid timestamps into monospace standard', () => {
  assert.equal(formatDateTimeMonospace(null), '—');
  assert.equal(formatDateTimeMonospace(undefined), '—');
  assert.equal(formatDateTimeMonospace(''), '—');

  // 格式化输出形如 YYYY-MM-DD HH:mm
  const formatted = formatDateTimeMonospace('2026-10-21T16:30:00Z');
  assert.match(formatted, /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
});

/* ========================================================================= */
/* 6. 内置 Mock 元数据 Schema 与解析器验证                                   */
/* ========================================================================= */

test('resolveTableMeta resolves built-in schemas and creates fallback schemas', () => {
  // 1. 解析要求矩阵 Schema
  const reqSchema = resolveTableMeta('requirements-matrix');
  assert.equal(reqSchema.schemaId, 'requirements-matrix');
  assert.equal(reqSchema.defaultSize, 'small', 'matrix uses size="small" per spec 9.1 rule 1');
  assert.ok(reqSchema.fields.some((f) => f.key === 'level' && f.dataType === 'level'));
  assert.ok(reqSchema.fields.some((f) => f.key === 'cite' && f.dataType === 'cite'));
  assert.ok(reqSchema.fields.some((f) => f.key === 'source' && f.dataType === 'source'));
  assert.ok(reqSchema.fields.some((f) => f.key === 'actions' && f.dataType === 'actions'));

  // 2. 解析资料库 Schema
  const libSchema = resolveTableMeta('library-records');
  assert.equal(libSchema.schemaId, 'library-records');
  assert.equal(libSchema.defaultSize, 'small', 'library list uses size="small" per spec 9.1 rule 1');
  assert.equal(libSchema.groupField, 'category');

  // 3. 解析事实表 Schema
  const factsSchema = resolveTableMeta('facts-matrix');
  assert.equal(factsSchema.schemaId, 'facts-matrix');
  const numCol = factsSchema.fields.find((f) => f.dataType === 'number');
  assert.ok(numCol, 'numeric column exists');
  assert.equal(numCol.align, 'right', 'numeric columns are right aligned per spec 9.1 rule 3');

  // 4. 未知 schemaId 提供安全兜底
  const fallback = resolveTableMeta('unknown-custom-schema');
  assert.equal(fallback.schemaId, 'unknown-custom-schema');
  assert.ok(fallback.fields.length >= 3, 'fallback schema has default columns');

  // 5. 传入完整 TableMeta 对象时直接透传
  const directObj = { schemaId: 'my-custom', name: '自定义', fields: [{ key: 'x', label: 'X', dataType: 'text' }] };
  assert.equal(resolveTableMeta(directObj), directObj);
});
