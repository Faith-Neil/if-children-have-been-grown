const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const prototypeDir = path.resolve(__dirname, '../../prototypes/bidding-ux');
const html = fs.readFileSync(path.join(prototypeDir, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(prototypeDir, 'app.js'), 'utf8');

// 用最小 DOM 环境执行实际 app.js，无需安装浏览器依赖。
// 仅模拟原型使用的元素查询和事件，不复写业务逻辑。
function createPrototype(){
  function element(attrs = {}, text = ''){
    const classes = new Set((attrs.class || '').split(/\s+/).filter(Boolean));
    const listeners = new Map();
    return {
      id: attrs.id || '', attrs, textContent: text, innerText: text,
      dataset: Object.fromEntries(Object.entries(attrs)
        .filter(([key]) => key.startsWith('data-'))
        .map(([key, value]) => [key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase()), value])),
      value: '', checked: 'checked' in attrs, disabled: 'disabled' in attrs,
      contentEditable: attrs.contenteditable, style: {},
      classList: {
        contains: name => classes.has(name),
        add: name => classes.add(name),
        remove: name => classes.delete(name),
        toggle(name, force){
          const enabled = force === undefined ? !classes.has(name) : force;
          enabled ? classes.add(name) : classes.delete(name);
          return enabled;
        }
      },
      addEventListener(type, handler){
        if (!listeners.has(type)) listeners.set(type, []);
        listeners.get(type).push(handler);
      },
      dispatch(type){
        const event = {preventDefault(){}, stopPropagation(){}};
        for (const handler of listeners.get(type) || []) handler(event);
      },
      click(){ if (!this.disabled) this.dispatch('click'); },
      focus(){ this.focused = true; },
      closest(){ return this.parentElement; },
      contains(node){
        for (let current = node; current; current = current.parentElement){
          if (current === this) return true;
        }
        return false;
      }
    };
  }

  const elements = [...html.matchAll(/<([a-z][\w-]*)\b([^>]*)>/gi)].map(match => {
    const attrs = {};
    for (const attr of match[2].matchAll(/([\w-]+)(?:="([^"]*)")?/g)){
      attrs[attr[1]] = attr[2] ?? '';
    }
    return element(attrs);
  });
  const ids = new Map(elements.filter(el => el.id).map(el => [el.id, el]));
  const rows = [...html.matchAll(/<tr\s+data-state="([^"]*)">([\s\S]*?)<\/tr>/g)]
    .map(match => element({'data-state': match[1]}, match[2].replace(/<[^>]+>/g, '')));
  const selectedWrap = elements.find(el => el.classList.contains('selected-demo'));
  const selectedHtml = html.match(/<div class="paragraph-wrap selected-demo"[^>]*>([\s\S]*?)<\/div>/)[1];
  const paragraph = element({}, selectedHtml.match(/<p>([\s\S]*?)<\/p>/)[1].replace(/<[^>]+>/g, ''));
  paragraph.parentElement = selectedWrap;
  selectedWrap.parentElement = ids.get('document-editor');

  const commands = [];
  const documentEvents = new Map();
  function matches(el, selector){
    if (selector.startsWith('.')) return selector.slice(1).split('.').every(name => el.classList.contains(name));
    const attr = selector.match(/^\[([\w-]+)\]$/);
    return attr ? attr[1] in el.attrs : false;
  }
  const document = {
    getElementById: id => ids.get(id) || null,
    querySelectorAll(selector){
      if (selector === '#matrix-body tr') return rows;
      return elements.filter(el => selector.split(',').some(part => matches(el, part.trim())));
    },
    querySelector(selector){
      if (selector === '.paragraph-wrap.selected-demo p') return paragraph;
      return this.querySelectorAll(selector)[0] || null;
    },
    addEventListener(type, handler){ documentEvents.set(type, handler); },
    execCommand(command){ commands.push(command); return true; }
  };
  const timers = new Map();
  let timerId = 0;
  const window = {scrollTo(){}, getSelection(){ return window.selection || null; }};
  const context = vm.createContext({
    document, window, Date,
    setTimeout(handler){ timers.set(++timerId, handler); return timerId; },
    clearTimeout(id){ timers.delete(id); }
  });
  vm.runInContext(app, context, {filename: 'prototypes/bidding-ux/app.js'});

  return {
    elements, document, paragraph, commands, window,
    get: id => ids.get(id),
    click: id => ids.get(id).click(),
    dispatch: id => ids.get(id).dispatch('click'),
    selectionChanged: () => documentEvents.get('selectionchange')(),
    editControls: () => [
      ...document.querySelectorAll('[data-ai-action], .show-diff'),
      ...['generate-suggestions', 'confirm-diff', 'undo-btn', 'redo-btn'].map(id => ids.get(id))
    ]
  };
}

test('the moved prototype has its local assets and unique element IDs', () => {
  const resources = [...html.matchAll(/(?:href|src)="([^"]+)"/g)].map(match => match[1]);
  assert.deepEqual(resources, ['styles.css', 'app.js']);
  for (const resource of resources) assert.ok(fs.existsSync(path.join(prototypeDir, resource)));
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(ids).size, ids.length);
});

test('a Diff opened before locking cannot write even through a dispatched click', () => {
  const page = createPrototype();
  page.document.querySelectorAll('.show-diff')[0].click();
  assert.equal(page.get('diff-modal').classList.contains('hidden'), false);
  const original = page.paragraph.textContent;
  const source = page.paragraph.parentElement.dataset.source;
  const saveState = page.get('save-indicator').textContent;

  page.click('demo-lock');
  assert.equal(page.get('document-editor').contentEditable, 'false');
  page.dispatch('confirm-diff'); // 直接派发事件仍能触发禁用按钮的监听器。

  assert.equal(page.paragraph.textContent, original);
  assert.equal(page.paragraph.parentElement.dataset.source, source);
  assert.equal(page.get('save-indicator').textContent, saveState);
  assert.ok(page.editControls().every(control => control.disabled));
  assert.match(page.get('toast').textContent, /只读模式/);
});

test('locking blocks generation, AI actions, Diff opening and editing commands', () => {
  const page = createPrototype();
  page.click('demo-lock');
  page.dispatch('generate-suggestions');
  for (const action of page.document.querySelectorAll('[data-ai-action]')) action.dispatch('click');
  for (const action of page.document.querySelectorAll('.show-diff')) action.dispatch('click');
  page.dispatch('undo-btn');
  page.dispatch('redo-btn');
  page.window.selection = {isCollapsed: false, anchorNode: page.paragraph};
  page.selectionChanged();

  assert.equal(page.get('suggestions').classList.contains('hidden'), true);
  assert.equal(page.get('diff-modal').classList.contains('hidden'), true);
  assert.equal(page.get('selection-toolbar').classList.contains('hidden'), true);
  assert.deepEqual(page.commands, []);
});

test('an empty or whitespace takeover reason leaves the editor locked', () => {
  const page = createPrototype();
  page.click('demo-lock');
  page.click('takeover-btn');
  page.get('takeover-reason').value = '   ';
  page.click('confirm-takeover');

  assert.equal(page.get('document-editor').contentEditable, 'false');
  assert.equal(page.get('lock-banner').classList.contains('hidden'), false);
  assert.equal(page.get('takeover-modal').classList.contains('hidden'), false);
  assert.ok(page.editControls().every(control => control.disabled));
  assert.match(page.get('toast').textContent, /填写接管原因/);
});

test('takeover with a reason restores generation and confirmed writing', () => {
  const page = createPrototype();
  const original = page.paragraph.textContent;
  page.click('demo-lock');
  page.click('takeover-btn');
  page.get('takeover-reason').value = '负责人已授权本次修改';
  page.click('confirm-takeover');

  assert.equal(page.get('document-editor').contentEditable, 'true');
  assert.equal(page.get('lock-banner').classList.contains('hidden'), true);
  assert.equal(page.get('takeover-modal').classList.contains('hidden'), true);
  assert.ok(page.editControls().every(control => !control.disabled));
  page.click('generate-suggestions');
  assert.equal(page.get('suggestions').classList.contains('hidden'), false);
  page.document.querySelectorAll('.show-diff')[0].click();
  page.click('confirm-diff');
  assert.notEqual(page.paragraph.textContent, original);
  assert.equal(page.get('diff-modal').classList.contains('hidden'), true);
});

test('the demo lock toggle restores editing when the lock is removed', () => {
  const page = createPrototype();
  page.click('demo-lock');
  page.click('demo-lock');
  assert.equal(page.get('document-editor').contentEditable, 'true');
  assert.ok(page.editControls().every(control => !control.disabled));
  page.click('undo-btn');
  page.click('redo-btn');
  assert.deepEqual(page.commands, ['undo', 'redo']);
});
