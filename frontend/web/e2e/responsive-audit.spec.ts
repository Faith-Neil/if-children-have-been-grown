// 为什么有这个文件：用真实 Chromium 在四个业务视口巡检核心页面。
// 它解决什么问题：自动抓横向溢出、交互元素裁切/遮挡和 Console/Antd 告警，并保存截图供视觉自审。
import { expect, test, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const shots = process.env.E2E_SCREENSHOT_DIR || join(tmpdir(), 'icg-e2e', 'responsive-audit');
const pages = [
  ['workbench', '/workbench'],
  ['coverage', '/projects/alpha-project/analyze'],
  ['editor', '/projects/alpha-project/editor'],
  ['knowledge', '/knowledge'],
  ['admin', '/admin/rules'],
] as const;
const viewports = [
  { width: 1920, height: 1080 },
  { width: 1440, height: 900 },
  { width: 1280, height: 720 },
  { width: 960, height: 720 },
];

async function login(page: Page, username = 'alpha-manager') {
  await page.goto('/workbench');
  const input = page.getByTestId('login-username-input');
  if (await input.isVisible({ timeout: 2000 }).catch(() => false)) {
    await input.fill(username);
    await page.getByTestId('login-password-input').fill('X_2026');
    await page.getByTestId('login-submit-button').click();
  }
  await expect(page.getByRole('button', { name: '退出' })).toBeVisible();
}

test('core pages are clean at 1920/1440/1280/960', async ({ page }) => {
  mkdirSync(shots, { recursive: true });
  const report: Array<Record<string, unknown>> = [];
  for (const viewport of viewports) {
    await page.setViewportSize(viewport);
    let signedInAs = '';
    for (const [name, path] of pages) {
      const neededUser = name === 'admin' ? 'admin' : 'alpha-manager';
      if (signedInAs !== neededUser) {
        if (signedInAs) await page.getByRole('button', { name: '退出' }).click().catch(() => undefined);
        await login(page, neededUser);
        signedInAs = neededUser;
      }
      const consoleProblems: string[] = [];
      const listener = (msg: { type(): string; text(): string }) => {
        const text = msg.text();
        if (msg.type() === 'error' || /deprecated|deprecation|Warning: /.test(text)) consoleProblems.push(text);
      };
      page.on('console', listener);
      await page.evaluate(next => { window.history.pushState({}, '', next); window.dispatchEvent(new PopStateEvent('popstate')); }, path);
      await page.waitForLoadState('networkidle').catch(() => undefined);
      await page.waitForTimeout(700);
      const geometry = await page.evaluate(() => {
        const doc = document.documentElement;
        const horizontalOverflow = doc.scrollWidth - window.innerWidth;
        const visible = (el: Element) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.width > 2 && rect.height > 2 && style.visibility !== 'hidden' && style.display !== 'none' && rect.bottom > 0 && rect.right > 0 && rect.top < innerHeight && rect.left < innerWidth;
        };
        const controls = [...document.querySelectorAll('button:not(:disabled), a[href], input, .ant-select-selector')]
          .filter(visible).map(el => { const scroller = el.closest('.ant-table-content'); return { tag: el.tagName, text: (el.textContent || '').trim().slice(0, 30), rect: el.getBoundingClientRect(), inScrollableTable: !!scroller && scroller.scrollWidth > scroller.clientWidth }; });
        const clipped = controls.filter(item => (item.rect.left < -1 || item.rect.right > innerWidth + 1) && !item.inScrollableTable)
          .map(item => ({ text: item.text, left: item.rect.left, right: item.rect.right }));
        const overlaps: Array<Record<string, unknown>> = [];
        for (let i = 0; i < controls.length; i += 1) {
          for (let j = i + 1; j < controls.length; j += 1) {
            const a = controls[i].rect, b = controls[j].rect;
            const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
            const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
            if (ox > 4 && oy > 4 && !controls[i].text.includes(controls[j].text) && !controls[j].text.includes(controls[i].text)) {
              overlaps.push({ a: controls[i].text, b: controls[j].text, ox, oy });
              if (overlaps.length >= 8) return { horizontalOverflow, clipped, overlaps };
            }
          }
        }
        return { horizontalOverflow, clipped, overlaps };
      });
      if (viewport.width !== 1920) await page.screenshot({ path: join(shots, `${name}-${viewport.width}x${viewport.height}.png`), fullPage: true });
      report.push({ viewport, page: name, path, ...geometry, consoleProblems });
      page.off('console', listener);
      expect(geometry.horizontalOverflow, `${name}@${viewport.width} horizontal overflow`).toBeLessThanOrEqual(1);
      expect(geometry.clipped, `${name}@${viewport.width} clipped controls`).toEqual([]);
      expect(consoleProblems, `${name}@${viewport.width} console problems`).toEqual([]);
    }
    await page.getByRole('button', { name: '退出' }).click().catch(() => undefined);
  }
  writeFileSync(join(shots, 'responsive-audit-report.json'), JSON.stringify(report, null, 2));
});
