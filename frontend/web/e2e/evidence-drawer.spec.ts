// 为什么有这个文件：在真实浏览器核对挂证据抽屉的分组、拦截、保存和只读账号。
// 它解决什么问题：单测看不到抽屉、版本号和“证据失效”是否与条款状态分开；只用合成资料。
import { expect, test, type Locator, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const shots = process.env.E2E_SCREENSHOT_DIR || join(tmpdir(), 'icg-e2e', 'screens');
const project = '/projects/alpha-project';
const tender = `${project}/tender`;
const matrix = `${project}/matrix`;
const sample = [
  '合成招标文件：星河数据库维保服务项目',
  '招标编号：DEMO-2026-001',
  '投标截止时间：2026-12-31T17:00:00+08:00',
  '服务期限：12个月',
  '采购人：星河科技（虚构）',
  '★技术要求：提供数据库日常巡检，每月提交巡检报告。',
  '技术要求：重大故障响应不超过30分钟，处理方案由双方核对。',
  '商务要求：投标人应提供有效企业资质证明。',
  '商务要求：提供同类项目业绩证明，所有资料仅使用合成测试数据。',
].join('\n');

async function login(page: Page, accountTitle?: string) {
  await page.goto('/');
  let username = 'alpha-manager';
  if (accountTitle) {
    if (accountTitle.includes('查看人') || accountTitle.includes('viewer')) {
      username = 'alpha-viewer';
    } else if (accountTitle.includes('乙公司') || accountTitle.includes('beta')) {
      username = 'beta-editor';
    } else if (accountTitle.includes('编写人') || accountTitle.includes('editor')) {
      username = 'alpha-editor';
    }
  }
  const usernameInput = page.getByTestId('login-username-input');
  if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await usernameInput.fill(username);
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
  } else {
    if (accountTitle) {
      await page.locator('.login-card .ant-select-selector').click();
      await page.getByTitle(accountTitle).click();
    }
    await page.getByRole('button', { name: '进入工作台' }).click();
  }
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

async function go(page: Page, path: string) {
  await page.evaluate(next => {
    window.history.pushState({}, '', next);
    window.dispatchEvent(new PopStateEvent('popstate'));
  }, path);
  await expect(page).toHaveURL(new RegExp(`${path}$`));
}

async function pick(page: Page, dialog: Locator, label: string, option: string) {
  await dialog.locator('.ant-form-item').filter({ has: page.getByText(label, { exact: true }) }).locator('.ant-select-selector').click();
  await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').getByText(option, { exact: true }).click();
}

async function addLibrary(page: Page, fields: { name: string; type?: string; content: string; validUntil?: string; status?: string; reason?: string }) {
  await page.getByTestId('create-evidence-button').click();
  const dialog = page.getByRole('dialog', { name: '补录企业资料' });
  await dialog.getByLabel('资料名称').fill(fields.name);
  if (fields.type) await pick(page, dialog, '资料类别', fields.type);
  await dialog.getByLabel('资料内容要点与证明事实').fill(fields.content);
  if (fields.validUntil) await dialog.getByLabel('有效期至').fill(fields.validUntil);
  if (fields.status) await pick(page, dialog, '核验状态', fields.status);
  if (fields.reason) await dialog.getByLabel('本次核验说明与依据').fill(fields.reason);
  await dialog.getByRole('button', { name: '保存提交审核' }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('row', { name: new RegExp(fields.name) }).first()).toBeVisible();
}

test('evidence drawer groups records, blocks invalid ones, and keeps status separate from expiry', async ({ page }) => {
  test.setTimeout(120_000);
  mkdirSync(shots, { recursive: true });
  await login(page);
  await go(page, '/library');
  await addLibrary(page, { name: '合成待确认资质', content: '合成待确认正文，不能挂接。' });
  await addLibrary(page, { name: '合成历史标书参考', type: '历史标书（参考）', content: '合成历史标书原文，只能查看。', status: '已逐项核验并确认生效' });

  await go(page, `${project}/settings`);
  await page.getByLabel('投标截止时间').fill('2026-12-31 17:00');
  await page.locator('#project-setting-basic').getByRole('button', { name: '保存基本信息' }).click();
  await expect(page.getByText('基本信息已保存，旧检查与输出需按当前资料重新核对。')).toBeVisible();

  await go(page, tender);
  await page.locator('input[type="file"]').setInputFiles({ name: '合成招标示例.txt', mimeType: 'text/plain', buffer: Buffer.from(sample) });
  await expect(page.getByRole('cell', { name: '合成招标示例.txt' })).toBeVisible();
  await page.getByRole('button', { name: '解析招标文件' }).click();
  await expect(page).toHaveURL(/\/parse$/);
  await expect(page.getByText(/原文抽取 [1-9]\d* 条/)).toBeVisible();

  await go(page, matrix);
  const requirement = page.getByRole('row', { name: /企业资质证明/ });
  await requirement.getByRole('button', { name: '挂证据' }).click();
  const drawer = page.getByRole('dialog', { name: '挂证据' });
  await expect(drawer.getByRole('heading', { name: '结构化资料' })).toBeVisible();
  await expect(drawer.getByRole('heading', { name: '方案片段' })).toBeVisible();
  await expect(drawer.getByText('资料库没有可引用的记录')).toBeVisible();
  const history = drawer.locator('section').filter({ has: page.getByRole('heading', { name: '历史标书（参考）' }) });
  await expect(history.getByText('合成历史标书参考')).toBeVisible();
  await expect(history.getByRole('checkbox')).toHaveCount(0);
  await history.getByRole('button', { name: '查看原文' }).click();
  await expect(drawer.getByText('只能查看，不能勾选，也不能由智能匹配挂为证据。')).toBeVisible();
  const pending = drawer.locator('.evidence-card').filter({ hasText: '合成待确认资质' });
  await expect(pending.getByText('未确认')).toBeVisible();
  await expect(pending.getByRole('checkbox')).toBeDisabled();
  await drawer.getByRole('button', { name: '去补录' }).click();
  await expect(page).toHaveURL(/\/library$/);

  await addLibrary(page, { name: '合成可挂资质', content: '合成已确认资质正文。', validUntil: '2027-06-01', status: '已逐项核验并确认生效' });
  await addLibrary(page, { name: '合成方案片段', type: '方案片段', content: '合成方案片段正文。', status: '已逐项核验并确认生效' });
  await addLibrary(page, { name: '合成过期资质', content: '合成过期资质正文。', validUntil: '2020-01-01', status: '已逐项核验并确认生效' });

  await go(page, matrix);
  await requirement.getByRole('button', { name: '挂证据' }).click();
  await expect(drawer.getByText('资料库没有可引用的记录')).toHaveCount(0);
  const usable = drawer.locator('.evidence-card').filter({ hasText: '合成可挂资质' });
  await expect(usable.getByText(/资料版本 v/)).toBeVisible();
  await usable.getByRole('checkbox').check();
  const expired = drawer.locator('.evidence-card').filter({ hasText: '合成过期资质' });
  await expect(expired.getByText('过期', { exact: true })).toBeVisible();
  await expect(expired.getByRole('checkbox')).toBeDisabled();
  await expect(history.getByRole('checkbox')).toHaveCount(0);
  await expect(drawer.getByText('相对打开时的变动')).toBeVisible();
  await page.screenshot({ path: join(shots, 'evidence-drawer.png') });
  await drawer.getByRole('button', { name: '保存挂接' }).click();
  await expect(drawer).toBeHidden();
  await expect(requirement.getByText(/合成可挂资质 · v/)).toBeVisible();
  await expect(requirement.getByText('证据失效')).toHaveCount(0);
  await expect(requirement.getByText('待确认', { exact: true })).toBeVisible();

  await go(page, '/library');
  await page.getByRole('row', { name: /合成可挂资质/ }).getByRole('button', { name: '核对修改' }).click();
  const editor = page.getByRole('dialog', { name: '核对与编辑企业资料' });
  await editor.getByLabel('有效期至').fill('2020-01-01');
  await editor.getByLabel('本次核验说明与依据').fill('合成核对：把有效期改到截止日之前，用来看证据失效。');
  await editor.getByRole('button', { name: '保存提交审核' }).click();
  await expect(editor).toBeHidden();

  await go(page, matrix);
  await expect(requirement.getByText('证据失效')).toBeVisible();
  await expect(requirement.getByText('待确认', { exact: true })).toBeVisible();
  await expect(requirement).toHaveClass(/evidence-invalid-row/);
  await requirement.getByRole('button', { name: '挂证据' }).click();
  const attached = drawer.locator('section').filter({ has: page.getByRole('heading', { name: '本行已挂证据' }) });
  await expect(attached.getByText('证据失效', { exact: true })).toHaveCount(2);
  await attached.getByRole('button', { name: '刷新', exact: true }).click();
  await expect(attached.getByText('合成可挂资质')).toBeVisible();
  await expect(attached.getByText('证据失效', { exact: true })).toHaveCount(2);
  await drawer.getByRole('button', { name: '移除' }).click();
  await expect(drawer.getByText('相对打开时的变动')).toBeVisible();

  const other = await page.context().newPage();
  await login(other);
  await go(other, matrix);
  const otherRow = other.getByRole('row', { name: /企业资质证明/ });
  await otherRow.getByRole('button', { name: '挂证据' }).click();
  const otherDrawer = other.getByRole('dialog', { name: '挂证据' });
  await otherDrawer.getByRole('button', { name: '移除' }).click();
  await otherDrawer.getByRole('button', { name: '保存挂接' }).click();
  await expect(otherDrawer).toBeHidden();
  await expect(otherRow.getByText('尚未挂接')).toBeVisible();

  await expect(drawer.getByRole('button', { name: '保存挂接' })).toBeEnabled();
  await drawer.getByRole('button', { name: '保存挂接' }).click();
  await expect(drawer).toBeVisible();
  await expect(drawer.getByRole('button', { name: '保存挂接' })).toBeEnabled();
  await drawer.getByRole('button', { name: '保存挂接' }).click();
  await expect(drawer.getByText('本行已被他人修改，请刷新后再保存')).toBeVisible();
  await expect(drawer.getByRole('button', { name: '保存挂接' })).toBeDisabled();
  const conflict = drawer.locator('.ant-alert').filter({ hasText: '本行已被他人修改，请刷新后再保存' });
  await conflict.getByRole('button', { name: '刷新', exact: true }).click();
  await expect(conflict).toHaveCount(0);
  await expect(drawer.getByRole('button', { name: '保存挂接' })).toBeEnabled();
  await drawer.getByRole('button', { name: '保存挂接' }).click();
  await expect(drawer).toBeHidden();
  await expect(requirement.getByText('尚未挂接')).toBeVisible();

  await page.getByRole('button', { name: '退出' }).click();
  await login(page, '甲公司查看人（合成） · 公司只读账号 · 华东数智');
  await go(page, matrix);
  await expect(page.getByRole('row', { name: /企业资质证明/ }).getByRole('button', { name: '挂证据' })).toBeDisabled();
});
