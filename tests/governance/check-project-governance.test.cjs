const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {checkProjectGovernance} = require('../../scripts/check-project-governance.cjs');

function governance(version = 'g1.0', date = '2026-10-09'){
  return `<!-- governance-baseline:start -->
| 项目 | 当前值 |
|---|---|
| 治理版本 | ${version} |
| 更新日期 | ${date} |
| 关联 Issue | ISSUE-003 |
<!-- governance-baseline:end -->`;
}

function fixture(t){
  const temporaryDirectory = fs.realpathSync(os.tmpdir());
  const root = fs.mkdtempSync(path.join(temporaryDirectory, 'icg-governance-'));
  t.after(() => {
    // 清理前核对绝对路径，递归删除仅用于本测试创建的临时仓库。
    assert.equal(path.dirname(root), temporaryDirectory);
    assert.ok(path.basename(root).startsWith('icg-governance-'));
    fs.rmSync(root, {recursive: true, force: true});
  });
  const files = {
    'README.md': '# 测试仓库',
    'AGENTS.md': '# 协作规则',
    'docs/governance/WORKFLOW.md': governance(),
    'docs/PRD.md': governance() + '\n业务依据仍为 PRD v1.4。',
    'docs/ROADMAP.md': governance(),
    'docs/ARCHITECTURE.md': governance(),
    'docs/PROJECT_STATUS.md': '# 当前进度：1 项完成',
    'docs/TASK_BOARD.md': `<!-- task-board:start -->
| 任务ID | 状态 | 交付文档 |
|---|---|---|
| FE-M0-T01 | done（本地验收） | [交付](delivery/FE-M0-T01.md) |
| FE-M1-T01 | planned | — |
<!-- task-board:end -->`,
    'docs/delivery/FE-M0-T01.md': `<!-- task-delivery:start -->
| 项目 | 说明 |
|---|---|
| 任务ID | FE-M0-T01 |
| 代码解释 | 无代码变更，本任务登记协作资料。 |
| 验收 | 已检查资料与索引。 |
| 项目进度 | 完成 1 项，下一项等待输入。 |
<!-- task-delivery:end -->`,
    'issues/index.md': governance() + `
<!-- issue-board:start -->
| 编号 | 类型 | 状态 | 验收证据 | 合入状态 |
|---|---|---|---|---|
| ISSUE-003 | workflow | closed（本地验收） | [验收](../docs/delivery/FE-M0-T01.md) | 未合入 |
| ISSUE-004 | change | triaged | — | 未合入 |
| ISSUE-005 | version | ready | — | 未合入 |
| ISSUE-006 | bug | blocked（外部分支待整合） | — | 未合入 |
| ISSUE-007 | decision | ready | — | 未合入 |
<!-- issue-board:end -->`,
    'issues/ISSUE-003.md': '# 本轮协作维护',
    'docs/templates/task-delivery.md': '<!-- task-delivery:start -->\n任务ID：待填写\n<!-- task-delivery:end -->',
    'docs/reference/product/historical.md': '# 历史产品 v0.2\n无治理头，无当前交付字段。',
    'docs/delivery/historical.md': '# 历史交付\n保留当时事实，不要求现行字段。',
    'prototypes/bidding-ux/README.md': '# 原型说明'
  };
  function write(file, contents){
    const absolute = path.join(root, file);
    fs.mkdirSync(path.dirname(absolute), {recursive: true});
    fs.writeFileSync(absolute, contents, 'utf8');
  }
  for (const [file, contents] of Object.entries(files)) write(file, contents);
  const indexed = Object.keys(files).filter(file => !['README.md', 'docs/reference/product/historical.md'].includes(file));
  write('docs/DOCUMENT_INDEX.md', indexed.map(file => `[${file}](${path.relative('docs', file).split(path.sep).join('/')})`).join('\n'));
  return {root, write, read: file => fs.readFileSync(path.join(root, file), 'utf8')};
}

test('当前治理资料可通过，历史业务版本和模板无需套用当前交付字段', t => {
  const project = fixture(t);
  const result = checkProjectGovernance(project.root);
  assert.deepEqual(result.errors, []);
  assert.equal(result.checkedTasks, 2);
  assert.equal(result.checkedIssues, 5);
  assert.deepEqual(result.baseline, {version: 'g1.0', date: '2026-10-09', issue: 'ISSUE-003'});
});

test('done 任务缺失实际交付文档时报告 missingdelivery', t => {
  const project = fixture(t);
  project.write('docs/TASK_BOARD.md', project.read('docs/TASK_BOARD.md').replace('delivery/FE-M0-T01.md', 'delivery/absent.md'));
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'missingdelivery' && error.file === 'docs/TASK_BOARD.md'));
  assert.ok(result.errors.some(error => error.code === 'brokenlink'));
});

test('三件套治理头偏离 WORKFLOW 时报告 wrongbaseline，正文业务版本不参与比较', t => {
  const project = fixture(t);
  project.write('docs/PRD.md', governance('g0.9') + '\n业务依据为 PRD v1.8。');
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'wrongbaseline' && error.file === 'docs/PRD.md'));
});

test('本地 Markdown 链接缺失时报告 brokenlink，代码示例里的链接不误报', t => {
  const project = fixture(t);
  project.write('README.md', '# 仓库\n[失效入口](docs/absent.md)\n`[示例](docs/code-only.md)`\n```md\n[样例](docs/fenced-only.md)\n```');
  const result = checkProjectGovernance(project.root);
  assert.deepEqual(result.errors.filter(error => error.code === 'brokenlink').map(error => error.message), ['docs/absent.md：目标不存在']);
});

test('done 任务交付必须包含匹配的任务ID及四个完成字段', t => {
  const project = fixture(t);
  project.write('docs/delivery/FE-M0-T01.md', project.read('docs/delivery/FE-M0-T01.md').replace('| 任务ID | FE-M0-T01 |', '| 任务ID | FE-M0-T99 |').replace('| 代码解释 | 无代码变更，本任务登记协作资料。 |', '| 代码解释 | |'));
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'invaliddelivery'));
});

test('closed Issue 缺少证据或独立合入状态时不能通过', t => {
  const project = fixture(t);
  project.write('issues/index.md', project.read('issues/index.md').replace('[验收](../docs/delivery/FE-M0-T01.md) | 未合入', '已通过 | closed'));
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'closedwithoutevidence'));
  assert.ok(result.errors.some(error => error.code === 'missingmergestatus'));
});

test('Issue 看板拒绝五种约定类型之外的未知类型', t => {
  const project = fixture(t);
  project.write('issues/index.md', project.read('issues/index.md').replace('| ISSUE-004 | change |', '| ISSUE-004 | enhancement |'));
  const result = checkProjectGovernance(project.root);
  assert.equal(result.ok, false);
  assert.ok(result.errors.some(error => error.code === 'invalidissuetype' && error.file === 'issues/index.md' && error.message.includes('ISSUE-004')));
});

test('新增维护文档和完成交付遗漏索引时报告登记问题', t => {
  const project = fixture(t);
  project.write('docs/code/FE-M0-T01.md', '# 新增代码说明');
  project.write('docs/DOCUMENT_INDEX.md', project.read('docs/DOCUMENT_INDEX.md').replace('[docs/delivery/FE-M0-T01.md](delivery/FE-M0-T01.md)', ''));
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'unindexeddocument' && error.file === 'docs/code/FE-M0-T01.md'));
  assert.ok(result.errors.some(error => error.code === 'unindexeddelivery'));
});

test('治理检查程序自身也须登记到文档索引', t => {
  const project = fixture(t);
  project.write('scripts/check-project-governance.cjs', '// 测试仓库中的程序占位文件');
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'unindexedprogram' && error.file === 'scripts/check-project-governance.cjs'));
});

test('关键文档缺失时报告 missingdocument', t => {
  const project = fixture(t);
  const absolute = path.resolve(project.root, 'docs/PROJECT_STATUS.md');
  assert.equal(path.dirname(path.dirname(absolute)), project.root);
  fs.unlinkSync(absolute);
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'missingdocument' && error.file === 'docs/PROJECT_STATUS.md'));
});

test('工作区历史来源与排除的客户目录不套用活动文档规则，活动链接仍检查', t => {
  const project = fixture(t);
  project.write('ICG/product doc/old.md', '[历史环境路径](/workspace/old/spec.md)');
  project.write('C2024-SAL0024-fixture/private.md', '[客户材料路径](missing-private.md)');
  project.write('C2025-TCH0053-fixture/private.md', '[客户材料路径](missing-private.md)');
  project.write('README.md', '[来源](ICG/product%20doc/old.md)');
  assert.deepEqual(checkProjectGovernance(project.root).errors, []);
  project.write('README.md', '[失效的活动入口](docs/missing.md)');
  const result = checkProjectGovernance(project.root);
  assert.ok(result.errors.some(error => error.code === 'brokenlink' && error.file === 'README.md'));
  assert.ok(result.errors.every(error => !error.file.startsWith('ICG/') && !error.file.startsWith('C202')));
});
