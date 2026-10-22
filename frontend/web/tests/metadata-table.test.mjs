// 为什么有这个文件：执行 MetadataTable 组件的 AST 结构与设计规范（9.1 / 9.2）静态断言。
// 它解决什么问题：
// 1. 验证 MetadataTable 与 ProTableWrapper 双命名正确导出；
// 2. 验证深度集成 StatusViews（SkeletonView、EmptyState、ErrorView 携带 traceId 复制）与 BusinessTags（LevelTag、Cite、SourceBar、AiTag、DirectTag）；
// 3. 验证 1280px 标准桌面无横向滚动优先策略及长文本 Drawer 侧边抽屉无障碍查阅；
// 4. 验证行合并（rowSpan）、双行表头与合规批量确认门禁（星号/废标/资格禁止批量确认）。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/MetadataTable.tsx', import.meta.url), 'utf8');
const tree = ts.createSourceFile('MetadataTable.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);

function findFunctionDeclaration(name) {
  for (const statement of tree.statements) {
    if (ts.isFunctionDeclaration(statement) && statement.name && statement.name.text === name) {
      return statement;
    }
  }
  return null;
}

function findVariableDeclaration(name) {
  for (const statement of tree.statements) {
    if (ts.isVariableStatement(statement)) {
      for (const decl of statement.declarationList.declarations) {
        if (ts.isIdentifier(decl.name) && decl.name.text === name) {
          return decl;
        }
      }
    }
  }
  return null;
}

test('MetadataTable and ProTableWrapper are declared and exported', () => {
  const tableFunc = findFunctionDeclaration('MetadataTable');
  assert.ok(tableFunc, 'MetadataTable function component is declared');

  const wrapperDecl = findVariableDeclaration('ProTableWrapper');
  assert.ok(wrapperDecl, 'ProTableWrapper alias is declared and exported');
});

test('MetadataTable deeply integrates StatusViews (SkeletonView, EmptyState, ErrorView)', () => {
  const tableFunc = findFunctionDeclaration('MetadataTable');
  assert.ok(tableFunc, 'MetadataTable is present');
  const text = tableFunc.getText(tree);

  // 1. 骨架屏（SkeletonView 5 行表格骨架）
  assert.match(text, /<SkeletonView/, 'renders SkeletonView when loading without data');
  assert.match(text, /variant="table"/, 'specifies table skeleton variant');
  assert.match(text, /rows=\{5\}/, 'specifies 5 rows skeleton per spec 6.1');

  // 2. 错误态降级（ErrorView 带 traceId 复制）
  assert.match(text, /<ErrorView/, 'renders ErrorView when error is provided');
  assert.match(text, /error=\{error\}/, 'passes error object to ErrorView');
  assert.match(text, /onRetry=\{onRetry/, 'supports retry callback');

  // 3. 空态提示（EmptyState 支持 empty 与 search 模式）
  assert.match(text, /<EmptyState/, 'renders EmptyState in table emptyText locale');
  assert.match(text, /mode=\{searchKeyword \? 'search' : 'empty'\}/, 'dynamically switches between search and empty modes');
});

test('MetadataTable deeply integrates BusinessTags in cell renderers', () => {
  const tableFunc = findFunctionDeclaration('MetadataTable');
  assert.ok(tableFunc, 'MetadataTable is present');
  const text = tableFunc.getText(tree);

  // 1. LevelTag 条款级别渲染
  assert.match(text, /case 'level':/, 'handles level data type');
  assert.match(text, /<LevelTag\s+level=\{levelVal\}/, 'renders LevelTag for clause levels');

  // 2. Cite 证据与切片引用渲染
  assert.match(text, /case 'cite':/, 'handles cite data type');
  assert.match(text, /<Cite\s+type=\{citeType\}/, 'renders Cite for citations');

  // 3. SourceBar 来源指纹溯源渲染
  assert.match(text, /case 'source':/, 'handles source data type');
  assert.match(text, /<SourceBar/, 'renders SourceBar for source provenance');

  // 4. AiTag 专属 AI 标签渲染
  assert.match(text, /case 'ai':/, 'handles ai data type');
  assert.match(text, /<AiTag\s+variant=\{variantVal\}/, 'renders AiTag for AI suggestions');

  // 5. DirectTag 系统直出渲染
  assert.match(text, /case 'direct':/, 'handles direct data type');
  assert.match(text, /<DirectTag\s+label=\{labelVal\}/, 'renders DirectTag for system answers');
});

test('MetadataTable supports dynamic cell merging (rowSpan) and two-line headers', () => {
  const tableFunc = findFunctionDeclaration('MetadataTable');
  assert.ok(tableFunc, 'MetadataTable is present');
  const text = tableFunc.getText(tree);

  // 1. rowSpan 动态合并配置
  assert.match(text, /calculateRowSpans/, 'calculates rowSpans for groupMerge columns');
  assert.match(text, /onCell:\s*\(_record/);
  assert.match(text, /rowSpan:\s*span/, 'returns rowSpan in onCell callback');

  // 2. 双行表头结构（规范 9.2 规则 2：中文名 + 等宽小字系统键）
  assert.match(text, /icg-two-line-header/, 'renders two-line header class');
  assert.match(text, /icg-header-primary/, 'renders primary title');
  assert.match(text, /icg-header-secondary/, 'renders secondary system key');
  assert.match(text, /icg-starred-indicator/, 'renders starred ★ indicator for critical fields');
});

test('MetadataTable enforces zero horizontal scroll priority with side Drawer for long texts', () => {
  const tableFunc = findFunctionDeclaration('MetadataTable');
  assert.ok(tableFunc, 'MetadataTable is present');
  const text = tableFunc.getText(tree);

  // 1. 无横滚优先：scroll.x 在预算充足时不设置
  assert.match(text, /calculateColumnWidthBudget/, 'computes width budget');
  assert.match(text, /budget\.fitsWithoutScroll/, 'checks if columns fit without horizontal scrolling');
  assert.match(text, /forceScrollX \|\| !budget\.fitsWithoutScroll/, 'scroll.x is only enabled when forced or overflowing');

  // 2. 长文本侧栏抽屉（Drawer）查看完整内容
  assert.match(text, /<Drawer/, 'renders Drawer for long text inspection');
  assert.match(text, /open=\{drawerOpen\}/, 'controls drawer visibility');
  assert.match(text, /openDetailDrawer/, 'provides open trigger');
  assert.match(text, /icg-detail-trigger/, 'trigger button in table cell');
});

test('MetadataTable implements compliance batch operations bar (§5.2.2 / Spec 9.1 Rule 6)', () => {
  const tableFunc = findFunctionDeclaration('MetadataTable');
  assert.ok(tableFunc, 'MetadataTable is present');
  const text = tableFunc.getText(tree);

  // 1. 批量操作栏渲染
  assert.match(text, /icg-batch-bar/, 'renders batch action bar');
  assert.match(text, /selectedRecords\.length > 0/, 'conditionally displays when rows are selected');

  // 2. 合规门禁判定（禁止批量确认星号/废标/资格）
  assert.match(text, /canBatchConfirm\(selectedRecords\)/, 'validates batch confirmation eligibility');
  assert.match(text, /batchValidation\.allowed/, 'checks if batch confirmation is allowed');
  assert.match(text, /disabled=\{!batchValidation\.allowed\}/, 'disables confirm button when non-batchable clauses exist');
  assert.match(text, /icg-batch-warning/, 'displays warning notice for prohibited batch items');
});

test('MetadataTable assigns risk row (#FFF5F5) and urgent row classes (Spec 9.1 Rule 4)', () => {
  const tableFunc = findFunctionDeclaration('MetadataTable');
  assert.ok(tableFunc, 'MetadataTable is present');
  const text = tableFunc.getText(tree);

  // 1. 风险行类名（row-danger）
  assert.match(text, /isRiskRow/, 'evaluates risk row predicate');
  assert.match(text, /row-danger/, 'adds row-danger class for #FFF5F5 background');

  // 2. 3 天内截止急迫行类名（row-urgent）
  assert.match(text, /isUrgentRow/, 'evaluates urgent row predicate');
  assert.match(text, /row-urgent/, 'adds row-urgent class');
});
