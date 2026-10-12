// 为什么有这个文件：在真实浏览器验证APP-M2-T001的布局断点、地址路由和未保存离开保护。
// 它解决什么问题：纯函数测试不能证明浏览器返回、刷新和弹窗确实保留地址与文字；只用合成账号和内存数据。
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const shots = process.env.E2E_SCREENSHOT_DIR || join(tmpdir(), 'icg-e2e', 'screens');
const editor = '/projects/alpha-project/editor';
const marker = '未保存的E2E输入-合成';

async function login(page: Page, path = '/') {
  await page.goto(path);
  await page.getByRole('button', { name: '进入工作台' }).click();
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

async function tab(page: Page, name: string) {
  // Ant Design在焦点回到页签后会给可访问名称加“Tab n of m”前缀，故按结尾匹配。
  await page.getByRole('tab', { name: new RegExp(`${name}$`) }).click();
}

async function dirtyEditor(page: Page) {
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  const lease = page.getByRole('button', { name: '取得编辑权' });
  const held = page.getByRole('button', { name: '释放编辑权' });
  await expect(lease.or(held)).toBeVisible();
  const takeover = page.getByRole('button', { name: '填写理由接管' });
  if (await takeover.isVisible()) {
    // 前一个用例的浏览器会话仍持有编辑权；按产品流程填写理由接管，不绕过后台。
    await takeover.click();
    await page.getByLabel('接管理由').fill('E2E用例切换会话，合成数据');
    await page.getByRole('button', { name: '填写理由并接管' }).click();
  } else if (await lease.isVisible()) await lease.click();
  await expect(page.getByRole('button', { name: '释放编辑权' })).toBeVisible();
  const box = page.locator('textarea.chapter-editor');
  await box.click();
  await page.keyboard.press('End');
  await page.keyboard.type(marker);
  await expect(box).toHaveValue(new RegExp(marker));
  return box;
}

const dialog = (page: Page) => page.locator('.ant-modal-confirm:not(.ant-zoom-leave)').filter({ hasText: '当前页面还有未保存的修改' });

async function cancelLeave(page: Page) {
  await page.getByRole('button', { name: '继续编辑' }).click();
  await expect(page.locator('.ant-modal-confirm').filter({ hasText: '当前页面还有未保存的修改' })).toHaveCount(0);
}

test('core pages render at 1280/1440/1680 after login', async ({ page }) => {
  mkdirSync(shots, { recursive: true });
  for (const width of [1280, 1440, 1680]) {
    await page.setViewportSize({ width, height: 900 });
    await login(page, '/workbench');
    for (const [name, path] of [['workbench', '/workbench'], ['overview', '/projects/alpha-project/overview'],
      ['matrix', '/projects/alpha-project/matrix'], ['editor', editor], ['export', '/projects/alpha-project/export']] as const) {
      await page.evaluate(p => { window.history.pushState({}, '', p); window.dispatchEvent(new PopStateEvent('popstate')); }, path);
      await expect(page).toHaveURL(new RegExp(`${path}$`));
      await page.waitForLoadState('networkidle');
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${name}@${width} horizontal overflow`).toBeLessThanOrEqual(1);
      await page.screenshot({ path: join(shots, `${name}-${width}.png`), fullPage: true });
    }
    await page.getByRole('button', { name: '退出' }).click();
  }
});

test('in-app navigation: cancel keeps URL/page/text, confirm leaves', async ({ page }) => {
  await login(page, editor);
  const box = await dirtyEditor(page);
  await tab(page, '概览');
  await expect(dialog(page)).toBeVisible();
  await cancelLeave(page);
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(box).toHaveValue(new RegExp(marker));
  await tab(page, '概览');
  await page.getByRole('button', { name: '离开页面' }).click();
  await expect(page).toHaveURL(/\/projects\/alpha-project\/overview$/);
});

async function editorWithHistory(page: Page) {
  // 历史：overview → editor → export，再返回editor，使editor前后都有记录。
  await login(page, '/projects/alpha-project/overview');
  await tab(page, '编辑台');
  await tab(page, '导出');
  await expect(page).toHaveURL(/\/export$/);
  await page.goBack();
  return dirtyEditor(page);
}

test('browser back: cancel keeps state, confirm leaves to previous page', async ({ page }) => {
  const box = await editorWithHistory(page);
  await page.goBack();
  await expect(dialog(page)).toBeVisible();
  await cancelLeave(page);
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(box).toHaveValue(new RegExp(marker));
  await page.goBack();
  await expect(dialog(page)).toBeVisible();
  await page.getByRole('button', { name: '离开页面' }).click();
  await expect(page).toHaveURL(/\/projects\/alpha-project\/overview$/);
});

test('browser forward: cancel keeps URL/page/text', async ({ page }) => {
  const box = await editorWithHistory(page);
  await page.goForward();
  await expect(dialog(page)).toBeVisible();
  await cancelLeave(page);
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(box).toHaveValue(new RegExp(marker));
});

test('browser forward: confirm leaves to next page', async ({ page }) => {
  await editorWithHistory(page);
  await page.goForward();
  await expect(dialog(page)).toBeVisible();
  await page.getByRole('button', { name: '离开页面' }).click();
  await expect(page).toHaveURL(/\/projects\/alpha-project\/export$/);
});

test('forward history remains after cancelling a forward', async ({ page }) => {
  await editorWithHistory(page);
  await page.goForward();
  await cancelLeave(page);
  await page.goForward();
  await expect(dialog(page)).toBeVisible({ timeout: 3_000 });
});

test('back after a cancelled forward confirms to the previous page', async ({ page }) => {
  await editorWithHistory(page);
  await page.goForward();
  await cancelLeave(page);
  await page.goBack();
  await expect(dialog(page)).toBeVisible();
  await page.getByRole('button', { name: '离开页面' }).click();
  await expect(page).toHaveURL(/\/projects\/alpha-project\/overview$/, { timeout: 3_000 });
});

test('reload: dismiss keeps text, accept reloads', async ({ page }) => {
  await login(page, editor);
  const box = await dirtyEditor(page);
  let seen = 0;
  page.once('dialog', d => { seen += d.type() === 'beforeunload' ? 1 : 0; void d.dismiss(); });
  await page.reload({ timeout: 5_000 }).catch(() => undefined);
  expect(seen).toBe(1);
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(box).toHaveValue(new RegExp(marker));
  page.once('dialog', d => { seen += 1; void d.accept(); });
  await page.reload();
  expect(seen).toBe(2);
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(page.locator('textarea.chapter-editor')).toHaveCount(0); // 会话只在内存，刷新后回到登录
  await page.getByRole('button', { name: '进入工作台' }).click();
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(page.locator('textarea.chapter-editor')).not.toHaveValue(new RegExp(marker));
});

test('back/forward routing across global and project pages', async ({ page }) => {
  await login(page, '/workbench');
  await page.locator('.ant-pro-sider a[href="/library"]').click();
  await expect(page).toHaveURL(/\/library$/);
  await page.locator('.ant-pro-sider a[href="/workbench"]').click();
  await page.getByRole('button', { name: '进入项目' }).first().click();
  await expect(page).toHaveURL(/\/projects\/alpha-project\/[a-z]+$/);
  const projectUrl = page.url();
  await tab(page, '响应矩阵');
  await expect(page).toHaveURL(/\/matrix$/);
  await page.goBack();
  await expect(page).toHaveURL(projectUrl);
  await page.goBack();
  await expect(page).toHaveURL(/\/workbench$/);
  await page.goBack();
  await expect(page).toHaveURL(/\/library$/);
  await page.goForward();
  await page.goForward();
  await page.goForward();
  await expect(page).toHaveURL(/\/matrix$/);
  await expect(page.getByRole('tab', { name: '响应矩阵', selected: true })).toBeVisible();
});

test('light content keeps readable card backgrounds', async ({ page }) => {
  await login(page, '/workbench');
  const bg = await page.locator('.ant-card').first().evaluate(e => getComputedStyle(e).backgroundColor);
  expect(bg).not.toBe('rgb(20, 20, 20)');
});

test('logout stays in the top header', async ({ page }) => {
  await login(page, '/workbench');
  const box = await page.getByRole('button', { name: '退出' }).boundingBox();
  expect(box && box.y).toBeLessThan(80);
});
