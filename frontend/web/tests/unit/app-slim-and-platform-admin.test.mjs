// 为什么有这个文件：验证 FE-TECH-DEBT-02 的组件拆分仍然接在 App 上，以及 APP-M2-T022 的平台管理员脱敏。
// 它解决什么问题：400 行只是当时瘦身的结果，不是以后每次改 App 都要守的行数上限。

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  isPlatformAdminRole,
  sanitizePlatformAdminTitle,
  maskTaskForPlatformAdmin,
  canPerformTaskAction,
  normalizeTask,
} from '../../src/shell/task-center.ts';

test('FE-TECH-DEBT-02: App.tsx still delegates shell, modals, workspace and global pages', () => {
  const appContent = readFileSync(new URL('../../src/app/App.tsx', import.meta.url), 'utf8');
  for (const name of ['AppHeaderActions', 'AppModals', 'ProjectWorkspaceContent', 'GlobalPagesContent']) {
    assert.ok(appContent.includes(`<${name}`) || appContent.includes(`${name}(`), `${name} stays wired from App.tsx`);
  }
});

test('FE-TECH-DEBT-02: Extracted shell & app domain components exist and export properly', () => {
  // 1. AppHeaderActions
  const headerPath = new URL('../../src/shell/AppHeaderActions.tsx', import.meta.url);
  const headerContent = readFileSync(headerPath, 'utf8');
  assert.ok(headerContent.includes('export function AppHeaderActions'), 'AppHeaderActions must be exported');
  assert.ok(headerContent.includes('TaskBadge'), 'AppHeaderActions must embed TaskBadge');

  // 2. AppModals
  const modalsPath = new URL('../../src/shell/AppModals.tsx', import.meta.url);
  const modalsContent = readFileSync(modalsPath, 'utf8');
  assert.ok(modalsContent.includes('export function AppModals'), 'AppModals must be exported');
  assert.ok(modalsContent.includes('TaskCenterDrawer'), 'AppModals must embed TaskCenterDrawer');
  assert.ok(modalsContent.includes('CreateProjectModal'), 'AppModals must embed CreateProjectModal');

  // 3. ProjectWorkspaceContent
  const projectPath = new URL('../../src/app/ProjectWorkspaceContent.tsx', import.meta.url);
  const projectContent = readFileSync(projectPath, 'utf8');
  assert.ok(projectContent.includes('export function ProjectWorkspaceContent'), 'ProjectWorkspaceContent must be exported');
  assert.ok(projectContent.includes('ProjectHeader'), 'ProjectWorkspaceContent must render ProjectHeader');
  assert.ok(projectContent.includes('ProjectContext.Provider'), 'ProjectWorkspaceContent must supply ProjectContext');

  // 4. GlobalPagesContent
  const globalPath = new URL('../../src/app/GlobalPagesContent.tsx', import.meta.url);
  const globalContent = readFileSync(globalPath, 'utf8');
  assert.ok(globalContent.includes('export function GlobalPagesContent'), 'GlobalPagesContent must be exported');
  assert.ok(globalContent.includes('ProjectListPage'), 'GlobalPagesContent must render ProjectListPage');
  assert.ok(globalContent.includes('JobsPage'), 'GlobalPagesContent must render JobsPage');
});

test('APP-M2-T022: isPlatformAdminRole correctly identifies platform administrator', () => {
  assert.equal(isPlatformAdminRole('platform_admin'), true);
  assert.equal(isPlatformAdminRole('PLATFORM_ADMIN'), true);
  assert.equal(isPlatformAdminRole(' platform_admin '), true);

  assert.equal(isPlatformAdminRole('project_lead'), false);
  assert.equal(isPlatformAdminRole('bid_writer'), false);
  assert.equal(isPlatformAdminRole('company_admin'), false);
  assert.equal(isPlatformAdminRole('readonly'), false);
  assert.equal(isPlatformAdminRole('bid_auditor'), false);
  assert.equal(isPlatformAdminRole(undefined), false);
  assert.equal(isPlatformAdminRole(''), false);
});

test('APP-M2-T022: sanitizePlatformAdminTitle masks tender file names and project sensitive words', () => {
  // 文件名脱敏为 [招标文件] (脱敏文件)
  const fileTitle = '中国移动2026年政企业务投标文件.pdf 智能解析';
  const sanitizedFile = sanitizePlatformAdminTitle(fileTitle, 'parse');
  assert.equal(sanitizedFile, '招标文件解析 (脱敏文件)');

  const docxTitle = '技术规范书_第3卷.docx 导出';
  const sanitizedDocx = sanitizePlatformAdminTitle(docxTitle, 'export');
  assert.equal(sanitizedDocx, '文档导出 (脱敏文件)');

  // 项目/公司敏感词脱敏
  const sensitiveTitle = '智慧城市一期项目交付方案生成';
  const sanitizedProject = sanitizePlatformAdminTitle(sensitiveTitle, 'generate');
  assert.ok(!sanitizedProject.includes('项目'));
  assert.ok(sanitizedProject.includes('***'));

  // 空值友好回退
  assert.equal(sanitizePlatformAdminTitle('', 'checks'), '合规检查');
});

test('APP-M2-T022: maskTaskForPlatformAdmin enforces security and ops-view masking invariants', () => {
  const originalTask = {
    id: 'job-sec-999',
    type: 'parse',
    status: 'failed',
    progress: 75,
    title: '某涉密军工项目招标文件.pdf 解析',
    projectName: '国家级涉密信息系统工程',
    projectId: 'proj-secret-001',
    companyId: 'company-secure-alpha',
    createdAt: '2026-10-27T10:00:00Z',
    durationMs: 45000,
    traceId: 'tr-999-sec',
    allowedActions: ['retry', 'cancel'],
    isAi: true,
    message: '解析在第3章涉密附录中发生超时',
  };

  const masked = maskTaskForPlatformAdmin(originalTask);

  // 1. 脱敏标记与项目名称遮蔽红线
  assert.equal(masked.isMasked, true, 'isMasked must be true');
  assert.equal(masked.projectName, '*** (业务项目已脱敏)', 'projectName must be masked');
  assert.equal(masked.projectId, '***', 'projectId must be masked to ***');

  // 2. 权限防线：平台管理员严禁重试或取消业务任务
  assert.deepEqual(masked.allowedActions, [], 'allowedActions must be strictly empty');
  assert.equal(canPerformTaskAction(masked, 'retry'), false, 'retry action must be forbidden');
  assert.equal(canPerformTaskAction(masked, 'cancel'), false, 'cancel action must be forbidden');

  // 3. 文件名与业务消息屏蔽
  assert.ok(!masked.title.includes('.pdf'), 'Tender filename must not appear in title');
  assert.ok(!masked.title.includes('军工'), 'Sensitive project terms must not leak in title');
  assert.ok(
    masked.message?.includes('平台运维屏蔽') || masked.message === undefined,
    'Internal business error description must be sanitized'
  );

  // 4. 保留平台运维排障必须字段
  assert.equal(masked.id, 'job-sec-999', 'Job ID must be preserved for trace');
  assert.equal(masked.companyId, 'company-secure-alpha', 'Tenant companyId must be retained for multi-tenant isolation');
  assert.equal(masked.traceId, 'tr-999-sec', 'Trace ID must be retained for ops audit');
  assert.equal(masked.durationMs, 45000, 'Duration must be preserved');
  assert.equal(masked.status, 'failed', 'Status must be preserved');
  assert.equal(masked.progress, 75, 'Progress percentage must be preserved');
});
