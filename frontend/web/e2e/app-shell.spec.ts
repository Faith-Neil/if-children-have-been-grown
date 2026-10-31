// 为什么有这个文件：在真实浏览器验证APP-M2-T001的布局断点、地址路由和未保存离开保护。
// 它解决什么问题：纯函数测试不能证明浏览器返回、刷新和弹窗确实保留地址与文字；只用合成账号和内存数据。
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const shots = process.env.E2E_SCREENSHOT_DIR || join(tmpdir(), 'icg-e2e', 'screens');
const editor = '/projects/alpha-project/editor';
const marker = '未保存的E2E输入-合成';

async function login(page: Page, path = '/', username = 'alpha-manager', password = 'X_2026') {
  await page.goto(path);
  const usernameInput = page.getByTestId('login-username-input');
  if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await usernameInput.fill(username);
    await page.getByTestId('login-password-input').fill(password);
    await page.getByTestId('login-submit-button').click();
  } else {
    const legacyBtn = page.getByRole('button', { name: '进入工作台' });
    if (await legacyBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await legacyBtn.click();
    }
  }
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

async function tab(page: Page, name: string) {
  // Ant Design在焦点回到页签后会给可访问名称加“Tab n of m”前缀，故按结尾匹配。
  await page.getByRole('tab', { name: new RegExp(`${name}$`) }).click();
}

async function dirtyEditor(page: Page) {
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  const lease = page.getByRole('button', { name: '取得编辑权' }).first();
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

test('reload: dismiss keeps text; autosave keeps it as a personal draft after reload', async ({ page, request }) => {
  await login(page, editor);
  const box = await dirtyEditor(page);
  let seen = 0;
  page.once('dialog', d => { seen += d.type() === 'beforeunload' ? 1 : 0; void d.dismiss(); });
  await page.reload({ timeout: 5_000 }).catch(() => undefined);
  expect(seen).toBe(1);
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(box).toHaveValue(new RegExp(marker));
  // 停止输入后自动保存为本人草稿（PRD §5.11.9，APP-M2-T172）：之后刷新不再丢字
  await expect(page.getByTestId('editor-saved-at')).toContainText('自动');
  page.once('dialog', d => { void d.accept(); });
  await page.reload();
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  const usernameInput = page.getByTestId('login-username-input');
  if (await usernameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await usernameInput.fill('alpha-manager');
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
  } else {
    await page.getByRole('button', { name: '进入工作台' }).click();
  }
  await expect(page).toHaveURL(new RegExp(`${editor}$`));
  await expect(page.locator('.chapter-editor-unheld-view, textarea.chapter-editor')).toContainText(marker);
  // 草稿只是本人草稿，不是正式正文；用例结束删除，避免影响其他用例
  const auth = { Authorization: `Bearer ${(await (await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } })).json()).access_token}` };
  const workspace = await (await request.get('/api/v1/projects/alpha-project/workspace', { headers: auth })).json();
  for (const chapter of workspace.chapters as { id: string }[]) {
    const detail = await (await request.get(`/api/chapters/${chapter.id}`, { headers: auth })).json();
    expect(detail.content).not.toContain(marker);
    if (detail.draft) await request.delete(`/api/chapters/${chapter.id}/draft`, { headers: auth, data: { sequence: detail.draft.sequence } });
  }
});

test('back/forward routing across global and project pages', async ({ page }) => {
  await login(page, '/workbench');
  await page.locator('.ant-pro-sider a[href="/library"]').click();
  await expect(page).toHaveURL(/\/library$/);
  await page.locator('.ant-pro-sider a[href="/workbench"]').click();
  await page.getByRole('button', { name: /进入(项目|工作台)/ }).first().click();
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

test('collapsed sidebar expand control opens the menu at 1280/1440/1680 in light and dark', async ({ page }) => {
  const label = () => page.locator('.ant-pro-sider .ant-menu-title-content', { hasText: '工作台' });
  for (const scheme of ['light', 'dark'] as const) {
    await page.emulateMedia({ colorScheme: scheme });
    for (const width of [1280, 1440, 1680]) {
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(() => {
        try { localStorage.removeItem('icg_sidebar_collapsed'); } catch {}
      });
      await login(page, '/workbench');
      await page.evaluate(() => {
        try { localStorage.removeItem('icg_sidebar_collapsed'); } catch {}
      }).catch(() => undefined);
      const sider = page.locator('.ant-pro-sider');
      const siderWidth = () => sider.evaluateAll(elements => Math.max(...elements.map(element => element.getBoundingClientRect().width)));
      await expect(sider.first()).toHaveClass(/ant-layout-sider-collapsed/);
      expect(await siderWidth()).toBeLessThan(80);
      const toggle = page.getByRole('button', { name: '收起或展开导航' });
      const hit = await toggle.evaluate(element => {
        const box = element.getBoundingClientRect();
        const top = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        return element === top || element.contains(top);
      });
      expect(hit, `${scheme}@${width} expand control is covered`).toBe(true);
      await toggle.click();
      await expect(sider.first()).not.toHaveClass(/ant-layout-sider-collapsed/);
      await expect.poll(siderWidth).toBeGreaterThan(200);
      await expect(label()).toBeVisible();
      await expect(page.getByRole('menuitem', { name: '企业资料库' })).toBeVisible();
      await page.getByRole('button', { name: '退出' }).click();
    }
  }
});

test('overview steps, pending mark and editor meta meet 4.5:1', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await login(page, '/projects/alpha-project/overview');
  const contrast = (element: Element) => {
    const parsed = (value: string) => {
      const match = value.match(/rgba?\(([^)]+)\)/);
      if (!match) return null;
      const parts = match[1].split(',').map(part => Number(part.trim()));
      return { r: parts[0], g: parts[1], b: parts[2], a: parts.length === 4 ? parts[3] : 1 };
    };
    const linear = (channel: number) => {
      const value = channel / 255;
      return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
    };
    const luminance = (color: { r: number; g: number; b: number }) => 0.2126 * linear(color.r) + 0.7152 * linear(color.g) + 0.0722 * linear(color.b);
    const layers = [];
    let node: Element | null = element;
    while (node) {
      const background = parsed(getComputedStyle(node).backgroundColor);
      if (background && background.a > 0) layers.push(background);
      node = node.parentElement;
    }
    let mixed = { r: 255, g: 255, b: 255 };
    for (const layer of layers.reverse()) {
      mixed = {
        r: mixed.r * (1 - layer.a) + layer.r * layer.a,
        g: mixed.g * (1 - layer.a) + layer.g * layer.a,
        b: mixed.b * (1 - layer.a) + layer.b * layer.a,
      };
    }
    const foreground = parsed(getComputedStyle(element).color);
    if (!foreground) return 0;
    const left = luminance(foreground);
    const right = luminance(mixed);
    const [lighter, darker] = left > right ? [left, right] : [right, left];
    return (lighter + 0.05) / (darker + 0.05);
  };
  const read = new Function('element', `return (${contrast.toString()})(element);`) as (element: Element) => number;
  const readAll = new Function('elements', `const contrast = ${contrast.toString()}; return elements.map(element => contrast(element));`) as (elements: Element[]) => number[];
  const circle = page.locator('.todo-circle').first();
  await expect(circle).toBeVisible();
  expect(await circle.evaluate(read)).toBeGreaterThanOrEqual(4.5);
  const orangeTags = page.locator('.ant-tag-orange:visible, .ant-tag-gold:visible, .ant-tag-warning:visible');
  expect(await orangeTags.count()).toBeGreaterThan(0);
  const orangeRatios = await orangeTags.evaluateAll(readAll);
  expect(Math.min(...orangeRatios)).toBeGreaterThanOrEqual(4.5);
  const steps = page.locator('.ant-steps-icon');
  expect(await steps.count()).toBeGreaterThan(0);
  const stepRatios = await steps.evaluateAll(readAll);
  expect(Math.min(...stepRatios)).toBeGreaterThanOrEqual(4.5);
  await tab(page, '编辑台');
  const meta = page.locator('.document-subline').first();
  await expect(meta).toBeVisible();
  expect(await meta.evaluate(read)).toBeGreaterThanOrEqual(4.5);
});
