const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const test = require('node:test');
const {WorkspaceSync, validateConfig} = require('../../tools/workspace-sync/sync.cjs');

const branch = 'codex/repository-foundation';
function git(directory, ...args){
  return execFileSync('git', args, {cwd:directory, encoding:'utf8', windowsHide:true, stdio:['ignore','pipe','pipe']}).trim();
}
function commit(directory, message){
  git(directory, 'add', '--all');
  git(directory, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@local.invalid', 'commit', '-m', message);
}
function fixture(t){
  const temporary = fs.realpathSync(os.tmpdir());
  const root = fs.mkdtempSync(path.join(temporary, 'icg-sync-'));
  const remote = path.join(root, 'remote.git');
  const repo = path.join(root, 'workspace');
  fs.mkdirSync(repo);
  git(root, 'init', '--bare', '--initial-branch='+branch, remote);
  git(repo, 'init', '--initial-branch='+branch);
  fs.writeFileSync(path.join(repo, 'README.md'), 'Synthetic workspace\n');
  commit(repo, 'fixture seed');
  git(repo, 'remote', 'add', 'origin', remote);
  git(repo, 'push', '-u', 'origin', branch);
  const config = {repoPath:repo, remote:'origin', remoteUrl:remote, permitLocalRemote:true,
    branch, runtimeDir:path.join(root, 'runtime'), pollMs:1, settleMs:10, fetchMs:30};
  const instances = [];
  async function start(){
    const sync = new WorkspaceSync({config, token:['github','_pat_', 'X'.repeat(60)].join('')});
    await sync.start(); instances.push(sync); return sync;
  }
  function write(file, content){
    const target = path.join(repo, file);
    fs.mkdirSync(path.dirname(target), {recursive:true});
    fs.writeFileSync(target, content);
  }
  function other(){
    const second = path.join(root, 'second');
    git(root, 'clone', remote, second); return second;
  }
  t.after(() => {
    instances.forEach(sync => sync.close());
    assert.equal(path.dirname(root), temporary);
    assert.ok(path.basename(root).startsWith('icg-sync-'));
    fs.rmSync(root, {recursive:true, force:true});
  });
  return {root, repo, remote, config, start, write, other};
}

test('本地文件稳定后真实提交推送，自动快照无需修改用户Git身份配置', async t => {
  const f = fixture(t), sync = await f.start(), now = Date.now();
  f.write('notes.md', 'local update\n');
  assert.equal((await sync.tick({now})).state, 'settling');
  const result = await sync.tick({now:now+11});
  assert.equal(result.reason, 'snapshot-pushed');
  assert.equal(git(f.remote, 'show', branch+':notes.md'), 'local update');
  assert.equal(git(f.repo, 'status', '--porcelain'), '');
  assert.equal(git(f.repo, 'log', '-1', '--format=%an'), 'Workspace Sync');
});

test('独立once实例可继承稳定期；单实例锁与停止文件保全未提交文件', async t => {
  const f = fixture(t), first = await f.start(), now = Date.now();
  f.write('notes.md', 'retained stability\n');
  await first.tick({now}); first.close();
  const second = await f.start();
  assert.equal((await second.tick({now:now+11})).reason, 'snapshot-pushed');
  const extra = new WorkspaceSync({config:f.config});
  await assert.rejects(extra.start(), /another-sync-instance/);
  f.write('unfinished.md', 'keep this');
  fs.writeFileSync(second.stopFile, 'stop');
  assert.equal((await second.tick({forceSettle:true})).state, 'stopped');
  assert.equal(fs.readFileSync(path.join(f.repo, 'unfinished.md'), 'utf8'), 'keep this');
});

test('干净工作区真实快进取得另一客户端推送的文件', async t => {
  const f = fixture(t), sync = await f.start(), second = f.other();
  fs.writeFileSync(path.join(second, 'remote.md'), 'cloud update\n');
  commit(second, 'remote update'); git(second, 'push', 'origin', branch);
  assert.equal((await sync.tick({forceFetch:true})).reason, 'fast-forwarded');
  assert.equal(fs.readFileSync(path.join(f.repo, 'remote.md'), 'utf8').replace(/\r\n/g, '\n'), 'cloud update\n');
  assert.equal(git(f.repo, 'rev-parse', 'HEAD'), git(f.remote, 'rev-parse', branch));
});

test('远端领先且本地有未提交变化时暂停，原文和HEAD保持不变', async t => {
  const f = fixture(t), sync = await f.start(), second = f.other();
  f.write('local.md', 'do not overwrite');
  const head = git(f.repo, 'rev-parse', 'HEAD');
  fs.writeFileSync(path.join(second, 'remote.md'), 'remote');
  commit(second, 'remote update'); git(second, 'push', 'origin', branch);
  assert.equal((await sync.tick({forceFetch:true, forceSettle:true})).reason, 'remote-ahead-with-local-changes');
  assert.equal(git(f.repo, 'rev-parse', 'HEAD'), head);
  assert.equal(fs.readFileSync(path.join(f.repo, 'local.md'), 'utf8'), 'do not overwrite');
});

test('双方已有提交分叉时不合并、不强推或丢失任一侧提交', async t => {
  const f = fixture(t), sync = await f.start(), second = f.other();
  f.write('local.md', 'local'); commit(f.repo, 'local commit');
  fs.writeFileSync(path.join(second, 'remote.md'), 'remote');
  commit(second, 'remote commit'); git(second, 'push', 'origin', branch);
  const localHead = git(f.repo, 'rev-parse', 'HEAD'), remoteHead = git(f.remote, 'rev-parse', branch);
  assert.equal((await sync.tick({forceFetch:true})).reason, 'diverged');
  assert.equal(git(f.repo, 'rev-parse', 'HEAD'), localHead);
  assert.equal(git(f.remote, 'rev-parse', branch), remoteHead);
});

test('人工暂存和分支切换优先，自动同步不消费人的暂存', async t => {
  const f = fixture(t), sync = await f.start();
  f.write('notes.md', 'human staged'); git(f.repo, 'add', 'notes.md');
  const staged = git(f.repo, 'diff', '--cached');
  assert.equal((await sync.tick({forceSettle:true})).reason, 'human-staged-changes');
  assert.equal(git(f.repo, 'diff', '--cached'), staged);
  commit(f.repo, 'human commit'); git(f.repo, 'checkout', '-b', 'another-branch');
  assert.equal((await sync.tick()).reason, 'branch-mismatch');
});

test('gitignore排除的合同和凭据不会进入云端，普通文件仍可同步', async t => {
  const f = fixture(t), sync = await f.start();
  f.write('.gitignore', '/C2024-SAL0024-*/\n/C2025-TCH0053-*/\n.env\n');
  f.write('C2024-SAL0024-synthetic/private.txt', 'synthetic customer fixture');
  f.write('C2025-TCH0053-synthetic/private.txt', 'synthetic customer fixture');
  f.write('.env', 'synthetic local settings');
  f.write('notes.md', 'ordinary file');
  assert.equal((await sync.tick({forceSettle:true})).reason, 'snapshot-pushed');
  const files = git(f.remote, 'ls-tree', '-r', '--name-only', branch);
  assert.ok(files.includes('notes.md'));
  assert.ok(!files.includes('private.txt') && !files.includes('.env'));
});

test('UTF8与UTF16完整凭据均阻止上传，状态和日志没有令牌或认证头', async t => {
  const f = fixture(t), sync = await f.start();
  const secret = ['github','_pat_', 'S'.repeat(60)].join('');
  f.write('notes.md', secret);
  assert.equal((await sync.tick({forceSettle:true})).reason, 'secret-pattern');
  f.write('notes.md', Buffer.from(secret, 'utf16le'));
  assert.equal((await sync.tick({forceSettle:true})).reason, 'secret-pattern');
  const log = fs.readFileSync(path.join(f.config.runtimeDir, 'events.jsonl'), 'utf8');
  assert.ok(!log.includes(secret) && !log.includes(sync.token) && !/Authorization|Basic /i.test(log));
  assert.equal(git(f.repo, 'log', '--format=%s'), 'fixture seed');
});

test('已人工提交后又删除的凭据仍按出站历史阻止推送', async t => {
  const f = fixture(t), sync = await f.start(), remoteHead = git(f.remote, 'rev-parse', branch);
  f.write('notes.md', ['github','_pat_', 'H'.repeat(60)].join('')); commit(f.repo, 'unsafe synthetic commit');
  fs.unlinkSync(path.join(f.repo, 'notes.md')); commit(f.repo, 'remove synthetic secret');
  assert.equal((await sync.tick()).reason, 'secret-pattern-in-outgoing-history');
  assert.equal(git(f.remote, 'rev-parse', branch), remoteHead);
});

test('合同未ignore、嵌套Git和工作区内runtime都不能绕过边界', async t => {
  const f = fixture(t), sync = await f.start();
  f.write('C2024-SAL0024-synthetic/private.txt', 'synthetic');
  assert.equal((await sync.tick({forceSettle:true})).reason, 'excluded-client-material');
  fs.unlinkSync(path.join(f.repo, 'C2024-SAL0024-synthetic/private.txt'));
  f.write('nested/note.txt', 'nested');
  git(path.join(f.repo, 'nested'), 'init');
  assert.equal((await sync.tick({forceSettle:true})).reason, 'nested-git');
  assert.throws(() => validateConfig({...f.config, runtimeDir:path.join(f.repo, 'runtime')}), /outside-repository/);
});
