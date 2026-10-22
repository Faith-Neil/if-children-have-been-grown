// 为什么有这个文件：覆盖 APP-M2-T018 公司掩码规则读取与留痕提示的静态契约与 AST 测试。
// 它解决什么问题：验证 company-mask-settings、useCompanyMaskSettings 与 MaskNoticeBanner 结构契约及零 storage 泄露调用。

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, '../src');

test('1. 静态契约：company-mask-settings.ts 核心常量与纯函数导出完整', () => {
  const filePath = path.join(srcDir, 'admin', 'company-mask-settings.ts');
  assert.ok(fs.existsSync(filePath), 'company-mask-settings.ts 必须存在');
  const content = fs.readFileSync(filePath, 'utf8');

  assert.ok(content.includes('export const COMPANY_MASK_RULES_KEY'), '必须导出 COMPANY_MASK_RULES_KEY');
  assert.ok(content.includes('export const DEFAULT_AUDIT_TRACE_NOTICE'), '必须导出 DEFAULT_AUDIT_TRACE_NOTICE');
  assert.ok(content.includes('export const DEFAULT_AUDIT_TRACE_DETAIL'), '必须导出 DEFAULT_AUDIT_TRACE_DETAIL');
  assert.ok(content.includes('export function sanitizeMaskRule'), '必须导出 sanitizeMaskRule');
  assert.ok(content.includes('export function extractMaskRulesFromCompanySettings'), '必须导出 extractMaskRulesFromCompanySettings');

  // 严禁在纯函数模块中直接读写持久化 storage
  assert.ok(!content.includes('localStorage.setItem'), '禁止在 company-mask-settings 中写入 localStorage');
  assert.ok(!content.includes('sessionStorage.setItem'), '禁止在 company-mask-settings 中写入 sessionStorage');
});

test('2. 静态契约：useCompanyMaskSettings.ts 提供 Provider 与 Hook 且支持动态响应更新', () => {
  const filePath = path.join(srcDir, 'admin', 'useCompanyMaskSettings.ts');
  assert.ok(fs.existsSync(filePath), 'useCompanyMaskSettings.ts 必须存在');
  const content = fs.readFileSync(filePath, 'utf8');

  assert.ok(content.includes('export function CompanyMaskProvider'), '必须导出 CompanyMaskProvider');
  assert.ok(content.includes('export function useCompanyMaskSettings'), '必须导出 useCompanyMaskSettings');
  assert.ok(content.includes('updateRules'), 'Provider 内部必须提供 updateRules 支持动态切规则');
  assert.ok(content.includes('resetRules'), 'Provider 内部必须提供 resetRules 兜底重置');
});

test('3. 静态契约：MaskNoticeBanner.tsx 导出留痕提示组件与 AuditTraceHint 别名', () => {
  const filePath = path.join(srcDir, 'admin', 'MaskNoticeBanner.tsx');
  assert.ok(fs.existsSync(filePath), 'MaskNoticeBanner.tsx 必须存在');
  const content = fs.readFileSync(filePath, 'utf8');

  assert.ok(content.includes('export function MaskNoticeBanner'), '必须导出 MaskNoticeBanner 组件');
  assert.ok(content.includes('export function AuditTraceHint'), '必须导出 AuditTraceHint 快捷别名');
  assert.ok(content.includes('data-testid'), '必须支持 data-testid 测试属性');
  assert.ok(content.includes('DEFAULT_AUDIT_TRACE_NOTICE'), '必须引用标准审计告警常量');

  // 确保无持久化副作用
  assert.ok(!content.includes('localStorage.setItem'), 'MaskNoticeBanner 禁止写入 localStorage');
  assert.ok(!content.includes('sessionStorage.setItem'), 'MaskNoticeBanner 禁止写入 sessionStorage');
});

test('4. 静态契约：MaskedField.tsx 深度集成 useCompanyMaskSettings 响应式获取生效掩码规则', () => {
  const filePath = path.join(srcDir, 'admin', 'MaskedField.tsx');
  const content = fs.readFileSync(filePath, 'utf8');

  assert.ok(content.includes('useCompanyMaskSettings'), 'MaskedField 必须引入 useCompanyMaskSettings');
  assert.ok(content.includes('effectiveRule'), 'MaskedField 必须计算 effectiveRule 动态规则');
});
