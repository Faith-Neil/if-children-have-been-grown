// 为什么有这个文件：用真实浏览器复核失败切页重试与旧账号迟到 401 的修复。
// 它解决什么问题：实际请求失败后仍须保留未保存正文，新账号也不能被旧请求退出。
import { expect, test, type Page } from '@playwright/test';

const editorPath = '/projects/alpha-project/editor';
const matrixPath = '/projects/alpha-project/matrix';
const marker = '复核失败切页后仍须保留的未保存文字-合成';
const leaveDialog = (page: Page) => page.locator('.ant-modal-confirm:not(.ant-zoom-leave)').filter({ hasText: '当前页面还有未保存的修改' });

async function loginManager(page: Page) {
  await page.goto(editorPath);
  const usernameInput = page.getByTestId('login-username-input');
  if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await usernameInput.fill('alpha-manager');
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
  } else {
    await page.getByRole('button', { name: '进入工作台', exact: true }).click();
  }
  await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
  await expect(page.locator('textarea.chapter-editor')).toBeVisible();
}

async function dirtyEditor(page: Page) {
  // 图标参与可访问名称（实际 DOM 为“lock 取得编辑权”）；沿用既有用例的文字匹配。
  const acquire = page.getByRole('button', { name: '取得编辑权' });
  const held = page.getByRole('button', { name: '释放编辑权' });
  await expect(acquire.or(held)).toBeVisible();
  const takeover = page.getByRole('button', { name: '填写理由接管', exact: true });
  if (await takeover.isVisible()) {
    await takeover.click();
    await page.getByLabel('接管理由').fill('复核用例接手上一合成浏览器会话的编辑权');
    await page.getByRole('button', { name: '填写理由并接管', exact: true }).click();
  } else if (await acquire.isVisible()) await acquire.click();
  await expect(held).toBeVisible();
  const box = page.locator('textarea.chapter-editor');
  await box.click(); await page.keyboard.press('End'); await page.keyboard.type(marker);
  await expect(box).toHaveValue(new RegExp(marker));
  return box;
}

test('failed editor-to-matrix load requires confirmation again and cancel retains the actual editor text', async ({ page }) => {
  await loginManager(page);
  const box = await dirtyEditor(page); const originalText = await box.inputValue();
  let workspaceReads = 0;
  await page.route('**/api/v1/projects/alpha-project/workspace', async route => {
    if (route.request().method() !== 'GET') { await route.continue(); return; }
    workspaceReads++;
    await route.fulfill({ status: 500, json: { code: 'INTERNAL_ERROR', message: '复核用工作区读取失败', traceId: 'review-failed-workspace' } });
  });
  await page.getByRole('tab', { name: /响应矩阵$/ }).click();
  await expect(leaveDialog(page)).toBeVisible();
  await page.getByRole('button', { name: '离开页面', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`${matrixPath}$`));
  await expect(page.getByText(/复核用工作区读取失败/)).toBeVisible();
  await expect(page.getByRole('tab', { name: /编辑台$/, selected: true })).toBeVisible();
  await expect(box).toHaveValue(originalText);
  await page.getByRole('tab', { name: /响应矩阵$/ }).click();
  await expect(leaveDialog(page)).toBeVisible();
  await page.getByRole('button', { name: '继续编辑', exact: true }).click();
  await expect(leaveDialog(page)).toHaveCount(0);
  await expect(box).toHaveValue(originalText);
  await expect(page.getByRole('tab', { name: /编辑台$/, selected: true })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`${matrixPath}$`));
  expect(workspaceReads).toBe(1); // 取消重试没有再次读取业务数据。
});

test('an Editor history request returning 401 after another account logs in cannot log out that account', async ({ page }) => {
  page.setDefaultTimeout(15_000);
  await test.step('A通过演示登录进入编辑台', async () => { await loginManager(page); });
  const versionUrl = /\/api\/chapters\/[^/]+\/versions(?:\?.*)?$/;
  let release!: () => void; const released = new Promise<void>(resolve => { release = resolve; });
  let started!: (token: string) => void; const oldToken = new Promise<string>(resolve => { started = resolve; });
  await page.route(versionUrl, async route => {
    if (route.request().method() !== 'GET') { await route.continue(); return; }
    started(route.request().headers().authorization);
    await released;
    await route.fulfill({ status: 401, json: { error: { code: 'SESSION_REQUIRED', message: '旧账号迟到401-复核' }, request_id: 'review-old-history' } });
  });
  try {
    let originToken = '';
    await test.step('点击版本并挂起A的真实历史GET', async () => {
      await page.getByRole('button', { name: '版本' }).click(); // 实际可访问名称为“history 版本”。
      originToken = await oldToken;
      console.log('review-history: A的历史GET已挂起');
    });
    await test.step('A退出并回到登录页', async () => {
      console.log('review-history: 开始点击退出');
      await page.getByRole('button', { name: '退出', exact: true }).click();
      await expect(page.getByTestId('login-submit-button').or(page.getByRole('button', { name: '进入工作台', exact: true }))).toBeVisible();
      console.log('review-history: A退出完成');
    });
    await test.step('在账号输入框输入B (beta-editor)', async () => {
      console.log('review-history: 开始填入B账号');
      const usernameInput = page.getByTestId('login-username-input');
      if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        await usernameInput.fill('beta-editor');
        await page.getByTestId('login-password-input').fill('X_2026');
      } else {
        await page.getByRole('combobox', { name: '演示账号', exact: true }).press('ArrowDown');
        await page.locator('.ant-select-dropdown:visible .ant-select-item-option-content').filter({ hasText: '乙公司编写人（合成）' }).click();
      }
      console.log('review-history: B账号填入完成');
    });
    await test.step('B通过真实登录接口取得独立会话', async () => {
      const loginResponse = page.waitForResponse(result => (result.url().includes('/api/v1/auth/login') || result.url().endsWith('/api/demo/login')) && result.request().method() === 'POST');
      const submitBtn = page.getByTestId('login-submit-button');
      if (await submitBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await submitBtn.click();
      } else {
        await page.getByRole('button', { name: '进入工作台', exact: true }).click();
      }
      const loginBody = await (await loginResponse).json();
      expect(loginBody.user.id).toBe('beta-editor'); expect(originToken).not.toBe(`Bearer ${loginBody.access_token}`);
      await expect(page.locator('.user-name')).toContainText('乙公司编写人（合成）');
      await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
      console.log('review-history: B已登录');
    });
    await test.step('放行A的迟到401并确认B继续登录', async () => {
      const lateResponse = page.waitForResponse(result => versionUrl.test(result.url()) && result.status() === 401);
      release(); await (await lateResponse).finished();
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.user-name')).toContainText('乙公司编写人（合成）');
      await expect(page.getByRole('button', { name: '退出', exact: true })).toBeVisible();
      await expect(page.getByTestId('login-submit-button')).toHaveCount(0);
      await expect(page.getByRole('button', { name: '进入工作台', exact: true })).toHaveCount(0);
      await expect(page.getByText(/旧账号迟到401-复核/)).toHaveCount(0);
    });
  } finally { release(); }
});
