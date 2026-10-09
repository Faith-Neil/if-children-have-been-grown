const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {spawn} = require('node:child_process');

const BRANCH = 'codex/repository-foundation';
const MAX_BYTES = 100 * 1024 * 1024;
const SECRET_PATTERNS = [
  /\bgh[pousr]_[A-Za-z0-9]{20,}\b/,
  /\bgithub_pat_[A-Za-z0-9_]{20,}\b/,
  /-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----/,
  /\bAKIA[A-Z0-9]{16}\b/
];

function inside(parent, child){
  const relative = path.relative(parent, child);
  return relative === '' || (!relative.startsWith('..' + path.sep) && relative !== '..' && !path.isAbsolute(relative));
}
function validateConfig(input){
  const config = {...input};
  if (config.branch !== BRANCH) throw new Error('invalid-config-branch');
  if (!path.isAbsolute(config.repoPath || '') || !path.isAbsolute(config.runtimeDir || '')) throw new Error('config-paths-must-be-absolute');
  config.repoPath = path.resolve(config.repoPath);
  config.runtimeDir = path.resolve(config.runtimeDir);
  if (inside(config.repoPath, config.runtimeDir)) throw new Error('runtime-must-be-outside-repository');
  if (config.tokenFile && (!path.isAbsolute(config.tokenFile) || inside(config.repoPath, path.resolve(config.tokenFile)))) throw new Error('token-must-be-outside-repository');
  config.remote = config.remote || 'origin';
  if (!/^[A-Za-z][A-Za-z0-9_-]*$/.test(config.remote)) throw new Error('invalid-remote-name');
  if (config.permitLocalRemote === true){
    if (!path.isAbsolute(config.remoteUrl || '')) throw new Error('test-remote-must-be-absolute');
    config.remoteUrl = path.resolve(config.remoteUrl);
  } else {
    let url;
    try { url = new URL(config.remoteUrl); } catch { throw new Error('invalid-remote-url'); }
    if (url.protocol !== 'https:' || url.hostname !== 'github.com' || url.username || url.password || url.search || url.hash || !/^\/[\w.-]+\/[\w.-]+\.git$/.test(url.pathname)) throw new Error('unsafe-remote-url');
    config.remoteUrl = url.href;
  }
  for (const [field, fallback] of Object.entries({pollMs:3000, settleMs:10000, fetchMs:30000})){
    config[field] = config[field] ?? fallback;
    if (!Number.isSafeInteger(config[field]) || config[field] < 1) throw new Error('invalid-sync-interval');
  }
  return config;
}
function loadConfig(file){
  try { return validateConfig(JSON.parse(fs.readFileSync(file, 'utf8'))); }
  catch (error){ throw new Error(error.message.startsWith('invalid-') || error.message.includes('must-be-') || error.message === 'unsafe-remote-url' ? error.message : 'cannot-load-config'); }
}
function sensitivePath(file){
  const portable = file.replace(/\\/g, '/');
  if (/^C2024-SAL0024-[^/]*(?:\/|$)|^C2025-TCH0053-[^/]*(?:\/|$)/i.test(portable)) return 'excluded-client-material';
  const name = path.posix.basename(portable).toLowerCase();
  if (portable.split('/').some(part => /^(?:secrets?|credentials?)$/i.test(part))) return 'sensitive-file';
  if ((/^\.env(?:\.|$)/.test(name) && name !== '.env.example') || /\.(?:pem|key|p12|pfx|dpapi|kdbx)$/.test(name)
      || /^(?:credentials?|secrets?|tokens?)(?:[._-]|$)/.test(name) || /^id_(?:rsa|dsa|ecdsa|ed25519)(?:\.|$)/.test(name)) return 'sensitive-file';
  if (/^~\$|\.(?:swp|tmp)$/.test(name)) return 'temporary-file';
  return null;
}
function statusEntries(output){
  const fields = output.split('\0');
  const entries = [];
  for (let index = 0; index < fields.length; index++){
    const value = fields[index];
    if (!value) continue;
    const xy = value.slice(0, 2);
    const file = value.slice(3);
    const entry = {xy, file};
    if (/[RC]/.test(xy)) entry.previous = fields[++index];
    entries.push(entry);
  }
  return entries;
}
class WorkspaceSync {
  constructor({config, token, runtimeDir} = {}){
    this.config = validateConfig({...config, ...(runtimeDir ? {runtimeDir} : {})});
    this.token = token || process.env.WORKSPACE_SYNC_TOKEN || '';
    this.runtime = this.config.runtimeDir;
    this.lockFile = path.join(this.runtime, 'instance.lock');
    this.stopFile = path.join(this.runtime, 'stop');
    this.nonce = crypto.randomBytes(16).toString('hex');
    this.started = false;
    this.lastFetch = null;
    this.lastSignature = null;
    this.stableSince = null;
    this.retryAt = 0;
    this.failures = 0;
    this.busy = false;
  }
  async start(){
    fs.mkdirSync(this.runtime, {recursive:true});
    const realRuntime = fs.realpathSync(this.runtime);
    const realRepo = fs.realpathSync(this.config.repoPath);
    if (inside(realRepo, realRuntime)) throw new Error('runtime-must-be-outside-repository');
    this.runtime = realRuntime;
    this.lockFile = path.join(realRuntime, 'instance.lock');
    this.stopFile = path.join(realRuntime, 'stop');
    if (fs.existsSync(this.lockFile)){
      let owner;
      try { owner = JSON.parse(fs.readFileSync(this.lockFile, 'utf8')); } catch { throw new Error('instance-lock-needs-review'); }
      let alive = true;
      try { process.kill(owner.pid, 0); } catch (error){ alive = error.code !== 'ESRCH'; }
      if (alive) throw new Error('another-sync-instance');
      fs.unlinkSync(this.lockFile);
    }
    let handle;
    try { handle = fs.openSync(this.lockFile, 'wx'); } catch { throw new Error('another-sync-instance'); }
    fs.writeFileSync(handle, JSON.stringify({pid:process.pid, nonce:this.nonce, startedAt:new Date().toISOString()}));
    fs.closeSync(handle);
    this.started = true;
    try {
      const stable = JSON.parse(fs.readFileSync(path.join(this.runtime, 'stable.json'), 'utf8'));
      if (/^[a-f0-9]{64}$/.test(stable.signature) && Number.isFinite(stable.since)) {
        this.lastSignature = stable.signature;
        this.stableSince = stable.since;
      }
    } catch { /* 首次运行或无有效稳定期记录时重新等待。 */ }
    return this.record('starting', 'initializing');
  }
  close(){
    if (!this.started) return;
    try {
      const owner = JSON.parse(fs.readFileSync(this.lockFile, 'utf8'));
      if (owner.nonce === this.nonce) fs.unlinkSync(this.lockFile);
    } catch { /* 保留无法确认归属的锁，不删除其他实例的文件。 */ }
    this.started = false;
  }
  record(state, reason, extra = {}){
    // 只记录固定状态字段；Git输出、令牌、认证头及文件正文不进入日志。
    const status = {state, reason, pid:process.pid, updatedAt:new Date().toISOString(), branch:this.config.branch, ...extra};
    const destination = path.join(this.runtime, 'status.json');
    const temporary = destination + '.' + this.nonce + '.tmp';
    fs.writeFileSync(temporary, JSON.stringify(status, null, 2) + '\n');
    fs.renameSync(temporary, destination);
    const log = path.join(this.runtime, 'events.jsonl');
    if (fs.existsSync(log) && fs.statSync(log).size > 2 * 1024 * 1024){
      const previous = log + '.1';
      if (fs.existsSync(previous)) fs.unlinkSync(previous);
      fs.renameSync(log, previous);
    }
    fs.appendFileSync(log, JSON.stringify(status) + '\n');
    this.status = status;
    return status;
  }
  git(args, {network = false, maxOutputBytes = 8 * 1024 * 1024} = {}){
    const environment = {...process.env, GIT_TERMINAL_PROMPT:'0', GCM_INTERACTIVE:'Never', GIT_LFS_SKIP_SMUDGE:'1'};
    // launcher令牌不会传给非网络Git命令，也不会用命令行参数传递。
    delete environment.WORKSPACE_SYNC_TOKEN;
    for (const key of Object.keys(environment)) {
      if (key.startsWith('GIT_TRACE')) environment[key] = '0';
      if (key.startsWith('GIT_CONFIG_')) delete environment[key];
    }
    if (network && this.token && !this.config.permitLocalRemote){
      environment.GIT_CONFIG_COUNT = '2';
      environment.GIT_CONFIG_KEY_0 = 'http.https://github.com/.extraHeader';
      environment.GIT_CONFIG_VALUE_0 = 'Authorization: Basic ' + Buffer.from('x-access-token:' + this.token).toString('base64');
      environment.GIT_CONFIG_KEY_1 = 'credential.helper';
      environment.GIT_CONFIG_VALUE_1 = '';
    }
    return new Promise(resolve => {
      const child = spawn(this.config.gitPath || 'git', args, {cwd:this.config.repoPath, env:environment, shell:false, windowsHide:true, stdio:['ignore','pipe','pipe']});
      const stdoutChunks = [], stderrChunks = [];
      let stdoutSize = 0, stderrSize = 0, truncated = false, finished = false;
      const timer = setTimeout(() => child.kill(), 45000);
      const done = result => { if (!finished){ finished = true; clearTimeout(timer); resolve(result); } };
      child.stdout.on('data', data => {
        stdoutSize += data.length;
        if (stdoutSize <= maxOutputBytes) stdoutChunks.push(data); else truncated = true;
      });
      child.stderr.on('data', data => {
        stderrSize += data.length;
        if (stderrSize <= 1024 * 1024) stderrChunks.push(data);
      });
      child.on('error', () => done({code:-1, stdout:'', stderr:''}));
      child.on('close', code => {
        const bytes = Buffer.concat(stdoutChunks);
        done({code:code ?? -1, stdout:bytes.toString('utf8'), bytes, stderr:Buffer.concat(stderrChunks).toString('utf8'), truncated});
      });
    });
  }
  retry(reason, now){
    this.failures++;
    this.retryAt = now + Math.min(60000, 5000 * 2 ** Math.min(this.failures - 1, 4));
    return this.record('retrying', reason, {retryAfterMs:this.retryAt - now});
  }
  async preflight(){
    const top = await this.git(['rev-parse', '--show-toplevel']);
    if (top.code !== 0 || fs.realpathSync(top.stdout.trim()) !== fs.realpathSync(this.config.repoPath)) return 'repository-root-mismatch';
    const gitDirectory = await this.git(['rev-parse', '--absolute-git-dir']);
    if (gitDirectory.code !== 0) return 'git-directory-unavailable';
    this.gitDirectory = gitDirectory.stdout.trim();
    for (const marker of ['index.lock','MERGE_HEAD','rebase-merge','rebase-apply','CHERRY_PICK_HEAD','REVERT_HEAD']){
      if (fs.existsSync(path.join(this.gitDirectory, marker))) return 'git-operation-active';
    }
    const branch = await this.git(['symbolic-ref','--quiet','--short','HEAD']);
    if (branch.code !== 0 || branch.stdout.trim() !== this.config.branch) return 'branch-mismatch';
    const remote = await this.git(['remote','get-url',this.config.remote]);
    if (remote.code !== 0 || remote.stdout.trim() !== this.config.remoteUrl) return 'remote-url-mismatch';
    const pushRemote = await this.git(['remote','get-url','--push',this.config.remote]);
    if (pushRemote.code !== 0 || pushRemote.stdout.trim() !== this.config.remoteUrl) return 'push-url-mismatch';
    const staged = await this.git(['diff','--cached','--quiet']);
    if (staged.code !== 0) return 'human-staged-changes';
    const tracked = await this.git(['ls-files','--stage','-z']);
    if (tracked.code !== 0) return 'tracked-files-unavailable';
    if (tracked.stdout.split('\0').some(entry => /^160000 |^120000 /.test(entry))) return 'nested-git-or-symbolic-link';
    return null;
  }
  scan(entries){
    const hash = crypto.createHash('sha256');
    for (const entry of [...entries].sort((a,b) => a.file.localeCompare(b.file))){
      const reason = sensitivePath(entry.file) || (entry.previous && sensitivePath(entry.previous));
      if (reason) return {reason};
      const absolute = path.resolve(this.config.repoPath, entry.file);
      if (!inside(this.config.repoPath, absolute)) return {reason:'path-outside-repository'};
      hash.update(entry.xy + '\0' + entry.file + '\0');
      if (!fs.existsSync(absolute)) continue;
      // 每一层都检查链接及嵌套.git，防止读取被链接到工作区外的文件。
      const relativeParts = path.relative(this.config.repoPath, absolute).split(path.sep);
      let current = this.config.repoPath;
      for (const part of relativeParts){
        current = path.join(current, part);
        const stat = fs.lstatSync(current);
        if (stat.isSymbolicLink()) return {reason:'symbolic-link'};
        if (stat.isDirectory() && fs.existsSync(path.join(current, '.git'))) return {reason:'nested-git'};
      }
      const before = fs.statSync(absolute);
      if (!before.isFile()) return {reason:'non-file-candidate'};
      if (before.size >= MAX_BYTES) return {reason:'large-file'};
      const bytes = fs.readFileSync(absolute);
      const after = fs.statSync(absolute);
      if (before.size !== after.size || before.mtimeMs !== after.mtimeMs) return {reason:'file-still-changing'};
      const text = bytes.includes(0) ? bytes.toString('utf16le') : bytes.toString('utf8');
      if (SECRET_PATTERNS.some(pattern => pattern.test(text))) return {reason:'secret-pattern'};
      hash.update(String(after.mtimeMs));
      hash.update(bytes);
    }
    return {signature:hash.digest('hex')};
  }
  async scanOutgoing(remoteRef){
    const commits = await this.git(['rev-list', `${remoteRef}..HEAD`]);
    if (commits.code !== 0 || commits.truncated) return 'outgoing-scan-unavailable';
    const inspected = new Set();
    for (const commit of commits.stdout.trim().split(/\s+/).filter(Boolean)) {
      const changed = await this.git(['diff-tree','--root','--no-commit-id','--no-renames','--name-only','-r','-z',commit]);
      if (changed.code !== 0 || changed.truncated) return 'outgoing-scan-unavailable';
      for (const file of changed.stdout.split('\0').filter(Boolean)) {
        const tree = await this.git(['ls-tree','-z',commit,'--',file]);
        if (tree.code !== 0) return 'outgoing-scan-unavailable';
        if (!tree.stdout) continue; // 删除已有文件不引入该文件的内容。
        const mode = tree.stdout.match(/^(\d{6}) \w+ ([a-f0-9]+)\t/);
        if (!mode) return 'outgoing-scan-unavailable';
        const forbidden = sensitivePath(file);
        if (forbidden) return forbidden;
        if (['120000','160000'].includes(mode[1])) return 'nested-git-or-symbolic-link';
        const object = mode[2];
        if (inspected.has(object)) continue;
        inspected.add(object);
        const size = await this.git(['cat-file','-s',object]);
        if (size.code !== 0 || !/^\d+\s*$/.test(size.stdout)) return 'outgoing-scan-unavailable';
        if (Number(size.stdout.trim()) >= MAX_BYTES) return 'large-file';
        const blob = await this.git(['cat-file','blob',object], {maxOutputBytes:MAX_BYTES});
        if (blob.code !== 0 || blob.truncated) return 'outgoing-scan-unavailable';
        const text = blob.bytes.includes(0) ? blob.bytes.toString('utf16le') : blob.stdout;
        if (SECRET_PATTERNS.some(pattern => pattern.test(text))) return 'secret-pattern-in-outgoing-history';
      }
    }
    return null;
  }
  async tick({now = Date.now(), forceSettle = false, forceFetch = false} = {}){
    if (!this.started) throw new Error('sync-not-started');
    if (this.busy) return this.status;
    this.busy = true;
    try {
      if (fs.existsSync(this.stopFile)) return this.record('stopped','stop-requested');
      const pause = await this.preflight();
      if (pause) return this.record('paused',pause);
      if (!this.config.permitLocalRemote && !this.token) return this.record('paused','missing-token');
      if (now < this.retryAt) return this.record('retrying','waiting-for-network-retry',{retryAfterMs:this.retryAt-now});
      const remoteRef = `refs/remotes/${this.config.remote}/${this.config.branch}`;
      if (forceFetch || this.lastFetch === null || now - this.lastFetch >= this.config.fetchMs){
        const fetched = await this.git(['fetch','--no-tags','--no-recurse-submodules',this.config.remote,`refs/heads/${this.config.branch}:${remoteRef}`], {network:true});
        if (fetched.code !== 0) return this.retry('fetch-failed',now);
        this.lastFetch = now;
        this.failures = 0;
        this.retryAt = 0;
      }
      const relation = await this.git(['rev-list','--left-right','--count',`HEAD...${remoteRef}`]);
      if (relation.code !== 0) return this.record('paused','remote-ref-unavailable');
      const [ahead, behind] = relation.stdout.trim().split(/\s+/).map(Number);
      if (ahead > 0 && behind > 0) return this.record('paused','diverged',{ahead,behind});
      const changed = await this.git(['status','--porcelain=v1','-z','--untracked-files=all']);
      if (changed.code !== 0 || changed.truncated) return this.record('paused','status-unavailable');
      const entries = statusEntries(changed.stdout);
      if (entries.some(entry => entry.xy !== '??' && entry.xy[0] !== ' ')) return this.record('paused','human-staged-changes');
      const scanned = this.scan(entries);
      if (scanned.reason) return this.record(scanned.reason === 'file-still-changing' ? 'settling' : 'paused',scanned.reason,{dirtyCount:entries.length});
      if (behind > 0){
        if (entries.length) return this.record('paused','remote-ahead-with-local-changes',{ahead,behind,dirtyCount:entries.length});
        const pulled = await this.git(['pull','--ff-only','--no-rebase','--no-tags',this.config.remote,this.config.branch], {network:true});
        if (pulled.code !== 0) return this.retry('fast-forward-failed',now);
        this.lastSignature = null;
        return this.record('synced','fast-forwarded',{ahead:0,behind:0});
      }
      if (entries.length){
        if (scanned.signature !== this.lastSignature){
          this.lastSignature = scanned.signature; this.stableSince = now;
          fs.writeFileSync(path.join(this.runtime, 'stable.json'), JSON.stringify({signature:scanned.signature, since:now}));
        }
        if (!forceSettle && now - this.stableSince < this.config.settleMs) return this.record('settling','waiting-for-stable-files',{dirtyCount:entries.length});
        // 写入前再检查，人的暂存、切分支及正在执行的Git操作一律优先保全。
        const finalPause = await this.preflight();
        if (finalPause) return this.record('paused',finalPause);
        const finalStatus = await this.git(['status','--porcelain=v1','-z','--untracked-files=all']);
        if (finalStatus.code !== 0 || finalStatus.stdout !== changed.stdout) return this.record('settling','files-changed-before-snapshot');
        const finalScan = this.scan(entries);
        if (finalScan.reason || finalScan.signature !== scanned.signature) return this.record('settling','files-changed-before-snapshot');
        if (fs.existsSync(this.stopFile)) return this.record('stopped','stop-requested');
        const candidates = [...new Set(entries.flatMap(entry => [entry.file, ...(entry.previous ? [entry.previous] : [])]))];
        const added = await this.git(['add','--',...candidates]);
        if (added.code !== 0) return this.record('paused','snapshot-stage-failed');
        const stagedNames = await this.git(['diff','--cached','--name-only','-z']);
        if (stagedNames.code !== 0 || stagedNames.stdout.split('\0').filter(Boolean).some(file => !candidates.includes(file))) return this.record('paused','concurrent-staging-detected');
        const commit = await this.git(['-c','user.name=Workspace Sync','-c','user.email=workspace-sync@local.invalid','commit','-m',`WIP: workspace snapshot ${new Date(now).toISOString()}`]);
        if (commit.code !== 0) return this.record('paused','snapshot-commit-failed');
        this.lastSignature = null;
        this.stableSince = null;
      }
      const outgoing = await this.git(['rev-list','--count',`${remoteRef}..HEAD`]);
      if (outgoing.code !== 0) return this.record('paused','outgoing-ref-unavailable');
      if (Number(outgoing.stdout.trim()) > 0){
        const unsafeOutgoing = await this.scanOutgoing(remoteRef);
        if (unsafeOutgoing) return this.record('paused',unsafeOutgoing);
        if (fs.existsSync(this.stopFile)) return this.record('stopped','stop-requested');
        const push = await this.git(['push',this.config.remote,`HEAD:refs/heads/${this.config.branch}`], {network:true});
        if (push.code !== 0){
          this.lastFetch = null;
          if (/non-fast-forward|fetch first/.test(push.stderr)) return this.record('paused','remote-rejected-snapshot');
          return this.retry('push-failed',now);
        }
        this.failures = 0;
        this.retryAt = 0;
        return this.record('synced','snapshot-pushed',{ahead:0,behind:0});
      }
      return this.record('synced','no-changes',{ahead:0,behind:0});
    } catch {
      return this.record('paused','local-operation-failed');
    } finally { this.busy = false; }
  }
  async run(){
    while (this.started){
      const result = await this.tick();
      if (result.state === 'stopped') return result;
      await new Promise(resolve => setTimeout(resolve, this.config.pollMs));
    }
    return this.status;
  }
}

async function main(){
  const args = process.argv.slice(2);
  const configIndex = args.indexOf('--config');
  if (configIndex < 0 || !args[configIndex+1] || args.some((value,index) => !['--once','--run','--config'].includes(value) && index !== configIndex+1)) throw new Error('usage-config-once-or-run');
  const sync = new WorkspaceSync({config:loadConfig(args[configIndex+1])});
  // Ctrl+C只请求退出；不reset、不移除暂存，也不取消已有提交。
  const stop = () => { try { fs.writeFileSync(sync.stopFile, 'stop\n'); } catch { /* 外部目录不可写时仍保留Git状态。 */ } };
  process.once('SIGINT',stop);
  process.once('SIGTERM',stop);
  try {
    await sync.start();
    const result = args.includes('--once') ? await sync.tick() : await sync.run();
    process.stdout.write(JSON.stringify({state:result.state,reason:result.reason}) + '\n');
    if (args.includes('--once') && ['paused','retrying'].includes(result.state)) process.exitCode = 2;
  } finally { sync.close(); }
}
if (require.main === module) main().catch(() => { process.stderr.write('Workspace sync could not start; check external configuration and instance lock.\n'); process.exitCode = 1; });
module.exports = {WorkspaceSync,loadConfig,validateConfig,sensitivePath,statusEntries};
