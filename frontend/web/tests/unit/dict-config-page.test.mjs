// 为什么有这个文件：验证 APP-M2-T024 A-03 字典配置页的业务功能、权限门禁与“已使用代码只能停用不可硬删除”核心红线。
// 它解决什么问题：
// 1. 验证 6 大核心业务状态码表与字段元数据的数据完整性与初始化加载；
// 2. 验证 8 大标准 RBAC 角色的权限感知矩阵（平台管理员/公司管理员可编辑停用，写作者/只读角色严格只读）；
// 3. 验证核心安全红线：“已使用代码只能停用，不可直接硬删除”；
// 4. 验证多维过滤、关键字检索与分类统计聚合函数；
// 5. 验证 DictConfigPage.tsx 组件结构、无障碍与 AST 测试契约。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';

import {
  buildInitialDictItems,
  checkDictPermission,
  computeCategorySummaries,
  filterDictItems,
  toggleDictItemActive,
  validateCodeDeactivation,
} from '../../src/admin/dict-config-core.ts';

// 辅助：加载并解析源码 AST
function parseSource(relPath) {
  const fullPath = path.resolve(import.meta.dirname, relPath);
  const content = fs.readFileSync(fullPath, 'utf8');
  const tree = ts.createSourceFile(
    fullPath,
    content,
    ts.ScriptTarget.Latest,
    true
  );
  return { content, tree };
}

test('1. 字典项初始化加载：涵盖 6 大核心业务状态码表与字段元数据', () => {
  const items = buildInitialDictItems();
  assert.ok(items.length >= 30, `must have at least 30 initial dict items, got ${items.length}`);

  // 1.1 必须包含 6 大业务状态码表全部分类
  const expectedStatusCategories = [
    'status_project',
    'status_chapter',
    'status_job',
    'status_check',
    'status_export',
    'status_lock',
  ];

  for (const cat of expectedStatusCategories) {
    const catItems = items.filter(i => i.category === cat);
    assert.ok(catItems.length >= 3, `category ${cat} must contain at least 3 items, got ${catItems.length}`);
    for (const item of catItems) {
      assert.ok(item.domain, 'status items must specify domain');
      assert.equal(item.isInUse, true, 'status items must be marked as in-use');
      assert.equal(item.isBuiltin, true, 'status items must be marked as builtin');
      assert.equal(item.isActive, true, 'initial status items must be active');
    }
  }

  // 1.2 必须包含核心字段元数据分类
  const expectedFieldCategories = ['field_project', 'field_tender', 'field_evidence', 'field_sla'];
  for (const cat of expectedFieldCategories) {
    const catItems = items.filter(i => i.category === cat);
    assert.ok(catItems.length >= 2, `field category ${cat} must contain items`);
  }

  // 1.3 核心关键字段校验
  const projectNameField = items.find(i => i.code === 'project_name');
  assert.ok(projectNameField, 'must include project_name metadata');
  assert.equal(projectNameField.metadata?.isStarred, true, 'project_name is starred');

  const blockerStatus = items.find(i => i.category === 'status_check' && i.code === 'blocker');
  assert.ok(blockerStatus, 'must include check blocker status');
  assert.equal(blockerStatus.label, '废标阻断');
  assert.equal(blockerStatus.metadata?.isBlocker, true, 'blocker has isBlocker flag');
});

test('2. 角色感知与权限判定：区分平台管理员、公司管理员与只读人员', () => {
  // 2.1 平台管理员（具备平台管理与编辑权限）
  const platformAdminPerm = checkDictPermission('platform_admin');
  assert.equal(platformAdminPerm.canEdit, true);
  assert.equal(platformAdminPerm.canToggleStatus, true);
  assert.equal(platformAdminPerm.canDelete, false, 'hard delete is strictly blocked for in-use codes');
  assert.equal(platformAdminPerm.isPlatformAdmin, true);
  assert.equal(platformAdminPerm.isReadOnly, false);
  assert.equal(platformAdminPerm.roleLabel, '平台管理员');

  // 2.2 公司管理员（具备本租户编辑与停用权限）
  const companyAdminPerm = checkDictPermission('company_admin');
  assert.equal(companyAdminPerm.canEdit, true);
  assert.equal(companyAdminPerm.canToggleStatus, true);
  assert.equal(companyAdminPerm.isCompanyAdmin, true);
  assert.equal(companyAdminPerm.isReadOnly, false);
  assert.equal(companyAdminPerm.roleLabel, '公司管理员');

  // 2.3 只读角色矩阵（严格只读）
  const readonlyRoles = [
    'viewer',
    'auditor',
    'group_admin',
    'project_lead',
    'bid_writer',
    'data_admin',
    'unknown_role',
    null,
    undefined,
  ];

  for (const role of readonlyRoles) {
    const perm = checkDictPermission(role);
    assert.equal(perm.canEdit, false, `role ${role} must NOT have edit permission`);
    assert.equal(perm.canToggleStatus, false, `role ${role} must NOT have toggle permission`);
    assert.equal(perm.isReadOnly, true, `role ${role} must be read-only`);
  }
});

test('3. 核心红线：“已使用代码只能停用，不可直接硬删除”', () => {
  const items = buildInitialDictItems();

  // 3.1 在用状态代码验证硬删除被严格拦截
  const inUseItem = items.find(i => i.isInUse);
  assert.ok(inUseItem, 'must find an in-use item');
  const deactivationCheck = validateCodeDeactivation(inUseItem);
  assert.equal(deactivationCheck.allowed, true, 'deactivation must be allowed');
  assert.equal(deactivationCheck.canHardDelete, false, 'hard delete must be prohibited');
  assert.equal(deactivationCheck.reason, '已使用代码只能停用，不可直接硬删除');

  // 3.2 系统内置代码验证硬删除拦截
  const builtinItem = items.find(i => i.isBuiltin && !i.isInUse);
  if (builtinItem) {
    const builtinCheck = validateCodeDeactivation(builtinItem);
    assert.equal(builtinCheck.canHardDelete, false);
  }

  // 3.3 未被引用的自定义代码允许硬删除
  const customUnusedItem = {
    id: 'dict_custom_test',
    category: 'custom',
    categoryLabel: '自定义',
    code: 'custom_code',
    label: '自定义代码',
    description: '未被引用代码',
    sortOrder: 100,
    isActive: true,
    isInUse: false,
    isBuiltin: false,
  };
  const customCheck = validateCodeDeactivation(customUnusedItem);
  assert.equal(customCheck.canHardDelete, true, 'unused custom item can be deleted');

  // 3.4 停用 / 启用状态切换逻辑与数据不可变性
  const initialActiveCount = items.filter(i => i.isActive).length;
  const toggleRes = toggleDictItemActive(items, inUseItem.id, false);
  assert.equal(toggleRes.error, undefined);
  assert.equal(toggleRes.modifiedItem?.isActive, false);
  assert.equal(toggleRes.updatedItems.filter(i => i.isActive).length, initialActiveCount - 1);

  // 重新启用
  const reEnableRes = toggleDictItemActive(toggleRes.updatedItems, inUseItem.id, true);
  assert.equal(reEnableRes.error, undefined);
  assert.equal(reEnableRes.modifiedItem?.isActive, true);
  assert.equal(reEnableRes.updatedItems.filter(i => i.isActive).length, initialActiveCount);
});

test('4. 分类汇总与多维检索过滤逻辑验证', () => {
  const items = buildInitialDictItems();

  // 4.1 分类汇总统计
  const summaries = computeCategorySummaries(items);
  assert.ok(summaries.length >= 10, 'must have at least 10 categories');
  for (const s of summaries) {
    assert.ok(s.totalCount > 0, 'category total count > 0');
    assert.ok(s.activeCount <= s.totalCount, 'active count <= total count');
  }

  // 4.2 关键字搜索 (匹配 code)
  const codeMatches = filterDictItems(items, { keyword: 'draft' });
  assert.ok(codeMatches.length >= 2, 'should match project draft and chapter draft');
  for (const m of codeMatches) {
    const matched =
      m.code.includes('draft') ||
      m.label.includes('draft') ||
      m.description.includes('draft');
    assert.ok(matched);
  }

  // 4.3 关键字搜索 (匹配 label)
  const labelMatches = filterDictItems(items, { keyword: '废标' });
  assert.ok(labelMatches.length >= 1);
  assert.ok(labelMatches.some(i => i.label.includes('废标')));

  // 4.4 分类精确匹配
  const projectStatusMatches = filterDictItems(items, { category: 'status_project' });
  assert.equal(projectStatusMatches.length, 5, 'project status has exactly 5 items');
  for (const m of projectStatusMatches) {
    assert.equal(m.category, 'status_project');
  }

  // 4.5 状态过滤 (active vs inactive)
  const deactRes = toggleDictItemActive(items, items[0].id, false);
  const activeOnly = filterDictItems(deactRes.updatedItems, { statusFilter: 'active' });
  assert.equal(activeOnly.length, items.length - 1);
  const inactiveOnly = filterDictItems(deactRes.updatedItems, { statusFilter: 'inactive' });
  assert.equal(inactiveOnly.length, 1);
  assert.equal(inactiveOnly[0].id, items[0].id);
});

test('5. DictConfigPage.tsx AST 静态契约与组件规范断言', () => {
  const { content, tree } = parseSource('../../src/admin/DictConfigPage.tsx');

  // 导出断言
  const exported = new Set();
  ts.forEachChild(tree, node => {
    if (ts.isVariableStatement(node) && node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword)) {
      for (const decl of node.declarationList.declarations) {
        if (decl.name && ts.isIdentifier(decl.name)) {
          exported.add(decl.name.text);
        }
      }
    }
  });

  assert.ok(exported.has('DictConfigPage'), 'must export DictConfigPage component');

  // 关键测试 ID 与无障碍契约断言
  assert.ok(content.includes('data-testid="dict-config-page"'), 'must include page root testid');
  assert.ok(content.includes('data-testid="dict-permission-tag"'), 'must include permission tag testid');
  assert.ok(content.includes('data-testid="dict-redline-alert"'), 'must include redline alert testid');
  assert.ok(content.includes('data-testid="dict-search-input"'), 'must include search input testid');
  assert.ok(content.includes('data-testid="dict-category-tabs"'), 'must include category tabs testid');
  assert.ok(content.includes('data-testid="dict-table"'), 'must include dict table testid');
  assert.ok(content.includes('data-testid="dict-detail-drawer"'), 'must include detail drawer testid');

  // 核心业务组件与规则文案断言
  assert.ok(content.includes('<StatusTag'), 'must mount StatusTag component for preview');
  assert.ok(content.includes('已使用代码只能停用，不可直接硬删除'), 'must display redline rule text');
});

test('6. GlobalPagesContent.tsx 路由装配断言', () => {
  const { content } = parseSource('../../src/app/GlobalPagesContent.tsx');
  assert.ok(content.includes('DictConfigPage'), 'GlobalPagesContent must reference DictConfigPage');
  assert.ok(content.includes("key: 'dict'"), "GlobalPagesContent must include key: 'dict' tab");
  assert.ok(content.includes('A-03 字典配置'), "GlobalPagesContent must display tab label 'A-03 字典配置'");
});
