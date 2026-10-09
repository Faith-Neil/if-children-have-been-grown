/* 为什么有这个文件：保存旧草稿冲突与本页面编辑权判断的回归验证。
   它解决什么问题：直接执行实际 app.js 的事件处理器，防止旧草稿无提示覆盖新正文。
   此处模拟 DOM 和 HTTP 返回，不替代真实浏览器排版或后台权限测试。 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {randomUUID} = require('node:crypto');

const staticDirectory = path.resolve(__dirname, '../../backend/bid-core/icg_demo/static');
const actualScript = fs.readFileSync(path.join(staticDirectory, 'app.js'), 'utf8');
const actualHtml = fs.readFileSync(path.join(staticDirectory, 'index.html'), 'utf8');
const htmlIds = [...actualHtml.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
assert.equal(new Set(htmlIds).size, htmlIds.length, '真实 HTML 的元素编号不能重复');
const currentContent = '经理已经提交的第二版正文，保留最新服务范围。';
const originalDraft = '编写人基于第一版保存的旧草稿，不能自动覆盖经理的新正文。';
const clone = value => JSON.parse(JSON.stringify(value));
const flush = () => new Promise(resolve => setImmediate(resolve));

class Element {
  constructor(tagName = 'div') {
    this.tagName = tagName;
    this.value = '';
    this.textContent = '';
    this.className = '';
    this.disabled = false;
    this.hidden = false;
    this.checked = false;
    this.readOnly = false;
    this.children = [];
  }
  replaceChildren(...children) {
    this.children = children;
    if (this.tagName === 'select') this.value = children[0]?.value || '';
  }
}

async function page({matchingDraft = false, otherSession = false, failRestore = false} = {}) {
  const elements = Object.fromEntries(htmlIds.map(id => [id, new Element(
    ['account', 'project', 'chapter'].includes(id) ? 'select' : 'div'
  )]));
  const account = {id: 'alpha-editor', name: '合成编写人', company_id: 'alpha', role: 'editor'};
  const expiry = new Date(Date.now() + 120_000).toISOString();
  const chapter = {
    id: 'alpha-tech', project_id: 'alpha-project', title: '技术方案', volume: 'technical',
    revision: 2, content: currentContent,
    draft: {base_revision: matchingDraft ? 2 : 1, sequence: 4, content: originalDraft},
    lock: otherSession ? {owner_id: account.id, expires_at: expiry} : null
  };
  const requests = [];
  const intervals = [];
  const reply = (body, status = 200) => ({ok: status >= 200 && status < 300, status,
    json: async () => clone(body)});
  const failure = (code, message, status) => reply({error: {code, message}, request_id: 'test-request'}, status);
  const lease = {lease_token: 'this-page-lease', owner_id: account.id, expires_at: expiry};
  const fetch = async (url, options = {}) => {
    const method = options.method || 'GET';
    const payload = options.body ? JSON.parse(options.body) : undefined;
    requests.push({url, method, payload});
    if (url === '/api/demo/accounts') return reply({accounts: [account]});
    if (url === '/api/demo/login') return reply({access_token: 'new-session-token', token_type: 'bearer', user: account});
    if (url === '/api/projects') return reply({projects: [{id: 'alpha-project', name: '合成项目', company_id: 'alpha'}]});
    if (url === '/api/projects/alpha-project/chapters') return reply({chapters: [{id: chapter.id, title: chapter.title, volume: chapter.volume, revision: chapter.revision}]});
    if (url === '/api/chapters/alpha-tech' && method === 'GET') return reply(chapter);
    if (url.endsWith('/versions') && method === 'GET') return reply({versions: []});
    if (url.endsWith('/audit')) return reply({events: []});
    if (url.endsWith('/lock') && method === 'POST') {
      if (otherSession) return failure('LOCK_HELD', '此账号的另一个登录会话正在编辑。', 423);
      chapter.lock = {owner_id: lease.owner_id, expires_at: lease.expires_at};
      return reply(lease);
    }
    if (url.endsWith('/lock/renew')) return reply(lease);
    if (url.endsWith('/draft') && method === 'PUT') {
      if (failRestore) return failure('LOCK_LOST', '编辑权已被接管。', 423);
      // 只按已约定的字段返回结果；版本/锁拒绝规则由真实后台测试负责。
      chapter.draft = {base_revision: payload.base_revision, sequence: payload.sequence, content: payload.content};
      return reply(chapter.draft);
    }
    if (url.endsWith('/versions') && method === 'POST') {
      chapter.revision += 1;
      chapter.content = payload.content;
      chapter.draft = null;
      return reply({revision: chapter.revision, content: chapter.content});
    }
    throw new Error('测试未预期的页面请求：' + method + ' ' + url);
  };
  const sandbox = vm.createContext({
    document: {getElementById(id) {
      assert.ok(elements[id], '页面脚本引用的元素必须在真实 HTML 中存在：' + id);
      return elements[id];
    }, createElement: tag => new Element(tag)},
    fetch, Date, crypto: {randomUUID},
    setInterval: callback => {intervals.push(callback); return intervals.length;},
    setTimeout: callback => {callback(); return 1;},
    URL: {createObjectURL: () => 'blob:test', revokeObjectURL() {}}
  });
  vm.runInContext(actualScript, sandbox, {filename: 'actual-demo-app.js'});
  await flush();
  const event = async id => {
    assert.equal(typeof elements[id].onclick, 'function');
    // 也直接调用禁用按钮的处理器，验证保护不只依赖按钮外观。
    await elements[id].onclick();
    await flush();
  };
  await event('login');
  return {elements, chapter, requests, intervals, event,
    read: expression => vm.runInContext(expression, sandbox),
    confirmLatest() {elements['review-latest'].checked = true; elements['review-latest'].onchange();},
    writes: suffix => requests.filter(request => request.url.endsWith(suffix) && ['PUT', 'POST'].includes(request.method))};
}

test('旧草稿独立显示，拿到编辑权也不能跳过核对提交或保存', async () => {
  const actual = await page();
  assert.equal(actual.elements.content.value, currentContent);
  assert.equal(actual.elements['saved-draft-content'].value, originalDraft);
  assert.match(actual.elements['saved-draft-status'].textContent, /版本 1.*版本为 2.*冲突/);
  await actual.event('acquire');
  assert.equal(actual.elements.content.readOnly, true);
  assert.equal(actual.elements.commit.disabled, true);
  await actual.event('commit');
  await actual.event('save-draft');
  await actual.event('restore-draft');
  assert.equal(actual.writes('/versions').length, 0);
  assert.equal(actual.writes('/draft').length, 0);
  assert.equal(actual.elements.content.value, currentContent);
});

test('明确核对后先重建当前版本草稿，再允许提交；原草稿仍可复制', async () => {
  const actual = await page();
  await actual.event('acquire');
  actual.confirmLatest();
  await actual.event('restore-draft');
  assert.deepEqual(actual.writes('/draft')[0].payload,
    {lease_token: 'this-page-lease', base_revision: 2, sequence: 1, content: originalDraft});
  assert.equal(actual.writes('/versions').length, 0);
  assert.equal(actual.chapter.revision, 2);
  assert.equal(actual.elements.content.value, originalDraft);
  assert.equal(actual.elements['saved-draft-content'].value, originalDraft);
  assert.equal(actual.read('state.editBaseRevision'), 2);
  assert.equal(actual.elements.content.readOnly, false);
  await actual.event('commit');
  assert.equal(actual.writes('/versions')[0].payload.base_revision, 2);
  assert.equal(actual.writes('/versions')[0].payload.content, originalDraft);
});

test('明确选择最新正文后不恢复旧草稿，后续新编辑仍使用已核对版本', async () => {
  const actual = await page();
  await actual.event('acquire');
  actual.confirmLatest();
  await actual.event('use-latest');
  assert.equal(actual.writes('/draft').length, 0);
  assert.equal(actual.elements.content.value, currentContent);
  assert.equal(actual.elements['saved-draft-content'].value, originalDraft);
  assert.equal(actual.elements.commit.disabled, false);
  actual.elements.content.value = '基于经理第二版继续修改的正文。';
  actual.elements.content.oninput();
  await actual.event('save-draft');
  assert.equal(actual.writes('/draft')[0].payload.base_revision, 2);
  assert.equal(actual.writes('/draft')[0].payload.content, '基于经理第二版继续修改的正文。');
});

test('核对期间又出现新版本时必须重新看正文，不暗中换到新基线', async () => {
  const actual = await page();
  await actual.event('acquire');
  actual.confirmLatest();
  actual.chapter.revision = 3;
  actual.chapter.content = '核对期间经理又提交的第三版正文。';
  await actual.event('restore-draft');
  assert.equal(actual.writes('/draft').length, 0);
  assert.equal(actual.elements.content.value, actual.chapter.content);
  assert.equal(actual.elements['review-latest'].checked, false);
  assert.equal(actual.elements.commit.disabled, true);
  await actual.event('commit');
  assert.equal(actual.writes('/versions').length, 0);
  actual.confirmLatest();
  await actual.event('restore-draft');
  assert.equal(actual.writes('/draft')[0].payload.base_revision, 3);
});

test('恢复请求失去编辑权时不换正文、不解除旧草稿冲突', async () => {
  const actual = await page({failRestore: true});
  await actual.event('acquire');
  actual.confirmLatest();
  await actual.event('restore-draft');
  assert.equal(actual.elements.content.value, currentContent);
  assert.equal(actual.elements['saved-draft-content'].value, originalDraft);
  assert.equal(actual.read('state.draftConflict'), true);
  assert.equal(actual.read('state.lease'), null);
  assert.equal(actual.writes('/versions').length, 0);
});

test('同一账号其他会话的锁摘要不会让本页面误判已取得编辑权', async () => {
  const actual = await page({otherSession: true});
  assert.match(actual.elements['lock-state'].textContent, /其他登录会话.*本页面只读/);
  assert.equal(actual.elements.content.readOnly, true);
  assert.equal(actual.read('state.lease'), null);
  await actual.event('commit');
  await actual.event('acquire');
  assert.equal(actual.read('state.lease'), null);
  assert.equal(actual.writes('/versions').length, 0);
  assert.equal(actual.elements['save-draft'].disabled, true);
});

test('同版本草稿也需明确恢复，续租后仍保留本页面的章节绑定', async () => {
  const actual = await page({matchingDraft: true});
  assert.equal(actual.elements.content.value, currentContent);
  await actual.event('acquire');
  await actual.event('restore-draft');
  assert.equal(actual.writes('/draft').length, 0);
  actual.confirmLatest();
  await actual.event('restore-draft');
  assert.equal(actual.writes('/draft')[0].payload.sequence, 5);
  assert.equal(actual.writes('/draft')[0].payload.base_revision, 2);
  await actual.intervals[0]();
  assert.equal(actual.read('hasLease()'), true);
});
