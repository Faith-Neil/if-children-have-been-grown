// 为什么有这个文件：端到端用例读写纸面正文，不再依赖已经撤掉的文本框。
// 它解决什么问题：章节正文在 ProseMirror 上，断言用可见文字；整篇替换走编辑器自己的 Markdown 回写。
import { expect, type Locator, type Page } from '@playwright/test';

export function paper(page: Page): Locator {
  return page.locator('[data-testid="paper-editor"] .ProseMirror');
}

export async function replacePaper(page: Page, text: string) {
  const sheet = page.locator('[data-testid="paper-editor"]');
  await sheet.evaluate((node, value) => {
    node.dispatchEvent(new CustomEvent('icg-set-markdown', { detail: value }));
  }, text);
  const sample = text.split('\n').map(line => line.trim()).find(Boolean) ?? '';
  if (sample) await expect(paper(page)).toContainText(sample);
}
