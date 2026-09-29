const views = [...document.querySelectorAll('.view')];
const navItems = [...document.querySelectorAll('.nav-item')];

function showView(id){
  views.forEach(v => v.classList.toggle('active-view', v.id === id));
  navItems.forEach(n => n.classList.toggle('active', n.dataset.view === id));
  window.scrollTo({top:0,behavior:'smooth'});
}
navItems.forEach(n => n.addEventListener('click', () => showView(n.dataset.view)));
document.querySelectorAll('[data-jump]').forEach(b => b.addEventListener('click', () => showView(b.dataset.jump)));

document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k'){
    e.preventDefault();
    document.getElementById('global-search').focus();
  }
});

const segments = [...document.querySelectorAll('.segment')];
const matrixRows = [...document.querySelectorAll('#matrix-body tr')];
const matrixSearch = document.getElementById('matrix-search');
let matrixFilter = 'all';

function refreshMatrix(){
  const q = matrixSearch.value.trim().toLowerCase();
  matrixRows.forEach(row => {
    const state = row.dataset.state || '';
    const matchesFilter = matrixFilter === 'all' || state.includes(matrixFilter);
    const matchesQuery = !q || row.innerText.toLowerCase().includes(q);
    row.style.display = matchesFilter && matchesQuery ? '' : 'none';
  });
}
segments.forEach(s => s.addEventListener('click', () => {
  segments.forEach(x => x.classList.remove('active'));
  s.classList.add('active');
  matrixFilter = s.dataset.filter;
  refreshMatrix();
}));
matrixSearch.addEventListener('input', refreshMatrix);

const drawer = document.getElementById('matrix-drawer');
document.querySelectorAll('.row-detail').forEach(b => b.addEventListener('click', () => drawer.classList.remove('hidden')));
document.querySelectorAll('.drawer-close,.drawer-backdrop').forEach(x => x.addEventListener('click', () => drawer.classList.add('hidden')));

const tabs = [...document.querySelectorAll('.right-tab')];
const tabContents = {
  assistant: document.getElementById('assistant-tab'),
  issues: document.getElementById('issues-tab'),
  sources: document.getElementById('sources-tab')
};
function setRightTab(tab){
  tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  Object.entries(tabContents).forEach(([k,el]) => el.classList.toggle('active', k === tab));
}
tabs.forEach(t => t.addEventListener('click', () => setRightTab(t.dataset.tab)));
document.querySelectorAll('[data-tab-jump]').forEach(x => x.addEventListener('click', () => setRightTab(x.dataset.tabJump)));

const kbSwitch = document.getElementById('kb-switch');
const kbLabel = document.getElementById('kb-label');
kbSwitch.addEventListener('change', () => {
  kbLabel.textContent = kbSwitch.checked ? '开启 · 本公司已发布资料' : '关闭 · 本次不使用企业知识库';
});

const suggestions = document.getElementById('suggestions');
document.getElementById('generate-suggestions').addEventListener('click', () => {
  suggestions.classList.remove('hidden');
  toast('已生成 3 条修改建议');
});

document.querySelectorAll('[data-ai-action]').forEach(btn => btn.addEventListener('click', () => {
  setRightTab('assistant');
  suggestions.classList.remove('hidden');
  toast(`已按“${btn.dataset.aiAction}”生成建议`);
}));

const diffModal = document.getElementById('diff-modal');
document.querySelectorAll('.show-diff').forEach(b => b.addEventListener('click', () => diffModal.classList.remove('hidden')));
document.querySelectorAll('.modal-close').forEach(b => b.addEventListener('click', () => diffModal.classList.add('hidden')));

const editor = document.getElementById('document-editor');
const saveIndicator = document.getElementById('save-indicator');
let saveTimer;

editor.addEventListener('input', () => {
  saveIndicator.textContent = '保存中…';
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2,'0');
    const mm = String(now.getMinutes()).padStart(2,'0');
    saveIndicator.textContent = `已保存 ${hh}:${mm}`;
  }, 800);
});

document.getElementById('confirm-diff').addEventListener('click', () => {
  const target = document.querySelector('.paragraph-wrap.selected-demo p');
  target.textContent = '结合近三年数据库维保项目经验，本项目巡检将按日常检查、周期分析和问题闭环执行，并重点覆盖实例状态、备份有效性及高可用运行情况。';
  target.parentElement.dataset.source = 'XX银行数据库维保项目；项目事实 · Oracle 19c';
  diffModal.classList.add('hidden');
  saveIndicator.textContent = '保存中…';
  setTimeout(() => {
    saveIndicator.textContent = '已保存 · 正在增量检查…';
    setTimeout(() => saveIndicator.textContent = '已保存 · 增量检查通过', 950);
  }, 600);
  toast('修改已写入，并创建新版本 V9');
});

const selectionToolbar = document.getElementById('selection-toolbar');
document.addEventListener('selectionchange', () => {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || !editor.contains(sel.anchorNode)){
    selectionToolbar.classList.add('hidden');
    return;
  }
  selectionToolbar.classList.remove('hidden');
});

const lockBanner = document.getElementById('lock-banner');
const takeoverModal = document.getElementById('takeover-modal');
document.getElementById('demo-lock').addEventListener('click', () => {
  lockBanner.classList.toggle('hidden');
  editor.contentEditable = lockBanner.classList.contains('hidden') ? 'true' : 'false';
});
document.getElementById('takeover-btn').addEventListener('click', () => takeoverModal.classList.remove('hidden'));
document.querySelectorAll('.takeover-close').forEach(x => x.addEventListener('click', () => takeoverModal.classList.add('hidden')));
document.getElementById('confirm-takeover').addEventListener('click', () => {
  const reason = document.getElementById('takeover-reason').value.trim();
  if (!reason){ toast('请填写接管原因'); return; }
  takeoverModal.classList.add('hidden');
  lockBanner.classList.add('hidden');
  editor.contentEditable = 'true';
  toast('已强制接管章节，操作已记录');
});
document.getElementById('refresh-lock').addEventListener('click', () => toast('锁状态已刷新'));

document.getElementById('send-ai').addEventListener('click', () => {
  const input = document.getElementById('assistant-input');
  if (!input.value.trim()) return;
  toast('问题已发送');
  input.value = '';
});

function toast(message){
  const el = document.getElementById('toast');
  el.textContent = message;
  el.classList.remove('hidden');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.add('hidden'), 1800);
}

// Demo paragraph menu behavior: clicking the ⋮ switches to source tab and selects contextual source.
document.querySelectorAll('.para-menu').forEach(btn => btn.addEventListener('click', e => {
  e.preventDefault();
  e.stopPropagation();
  const wrap = btn.closest('.paragraph-wrap');
  setRightTab('sources');
  toast(`来源：${wrap.dataset.source || '暂无来源'}`);
}));

// Undo / redo demo using browser editing commands where available.
document.getElementById('undo-btn').addEventListener('click', () => document.execCommand('undo'));
document.getElementById('redo-btn').addEventListener('click', () => document.execCommand('redo'));
