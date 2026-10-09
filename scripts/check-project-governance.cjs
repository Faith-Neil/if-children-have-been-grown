const fs = require('node:fs');
const path = require('node:path');

const requiredDocuments = [
  'README.md', 'AGENTS.md', 'docs/PRD.md', 'docs/ROADMAP.md',
  'docs/ARCHITECTURE.md', 'docs/PROJECT_STATUS.md', 'docs/DOCUMENT_INDEX.md',
  'docs/TASK_BOARD.md', 'docs/governance/WORKFLOW.md', 'issues/index.md',
  'issues/ISSUE-003.md'
];
const baselineDocuments = ['docs/PRD.md', 'docs/ROADMAP.md', 'docs/ARCHITECTURE.md', 'issues/index.md'];
const indexedPrograms = ['scripts/check-project-governance.cjs', 'tests/governance/check-project-governance.test.cjs'];
const baselineFields = ['治理版本', '更新日期', '关联 Issue'];
const deliveryFields = ['任务ID', '代码解释', '验收', '项目进度'];
const taskStates = ['planned', 'ready', 'in-progress', 'in-review', 'done', 'blocked', 'cancelled'];
const issueStates = ['new', 'triaged', 'ready', 'in-progress', 'in-review', 'closed', 'blocked'];
const issueTypes = new Set(['change', 'version', 'bug', 'workflow', 'decision']);
const ignoredDirectories = new Set(['.git', 'node_modules', 'dist', 'build', '.cache']);

function portable(value){ return value.split(path.sep).join('/'); }
function parseState(value, states){
  return plainText(value).toLowerCase().match(new RegExp(`^(${states.join('|')})(?=\\s|[（(]|$)`));
}
function plainText(value){
  return value.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/[`*_]/g, '').trim();
}

function markdownFiles(root){
  const files = [];
  function visit(directory){
    for (const entry of fs.readdirSync(directory, {withFileTypes: true})){
      if (entry.isSymbolicLink()) continue;
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory() && !ignoredDirectories.has(entry.name)) visit(absolute);
      else if (entry.isFile() && entry.name.endsWith('.md')) files.push(portable(path.relative(root, absolute)));
    }
  }
  visit(root);
  return files.sort();
}

function withoutCode(markdown){
  let fence = null;
  return markdown.split(/\r?\n/).map(line => {
    const marker = line.match(/^\s{0,3}(`{3,}|~{3,})/);
    if (marker){
      if (!fence) fence = marker[1];
      else if (marker[1][0] === fence[0] && marker[1].length >= fence.length) fence = null;
      return '';
    }
    if (fence) return '';
    return line.replace(/(`+).*?\1/g, '');
  }).join('\n').replace(/<!--[\s\S]*?-->/g, comment => comment.replace(/[^\n]/g, ' '));
}

function extractMarkdownLinks(markdown){
  const source = withoutCode(markdown);
  const links = [];
  const starts = /!?\[[^\]\n]*\]\(/g;
  let match;
  while ((match = starts.exec(source))){
    let cursor = starts.lastIndex;
    while (/\s/.test(source[cursor] || '') && cursor < source.length) cursor++;
    let target = '';
    if (source[cursor] === '<'){
      const end = source.indexOf('>', cursor + 1);
      if (end < 0) continue;
      target = source.slice(cursor + 1, end);
    } else {
      let depth = 0;
      while (cursor < source.length){
        const character = source[cursor];
        if (character === '\\' && cursor + 1 < source.length){
          target += source[++cursor];
        } else if (character === '('){ depth++; target += character; }
        else if (character === ')'){
          if (depth === 0) break;
          depth--; target += character;
        } else if (/\s/.test(character)) break;
        else target += character;
        cursor++;
      }
    }
    if (target) links.push({target, line: source.slice(0, match.index).split('\n').length});
  }
  for (const [index, line] of source.split('\n').entries()){
    const reference = line.match(/^\s{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))/);
    if (reference) links.push({target: reference[1] || reference[2], line: index + 1});
  }
  return links;
}

function localTarget(root, sourceFile, target){
  if (/^[a-z][a-z\d+.-]*:/i.test(target) && !/^[a-z]:[\\/]/i.test(target)) return null;
  const pathname = target.split(/[?#]/)[0];
  if (!pathname) return null;
  let decoded;
  try { decoded = decodeURIComponent(pathname); } catch { return {error: '链接路径编码无效'}; }
  const absolute = decoded.startsWith('/')
    ? path.resolve(root, '.' + decoded)
    : path.resolve(root, path.dirname(sourceFile), decoded);
  const relative = path.relative(root, absolute);
  if (relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)){
    return {error: '本地链接超出仓库范围'};
  }
  return {absolute, relative: portable(relative)};
}

function markedBlock(markdown, name){
  const start = `<!-- ${name}:start -->`;
  const end = `<!-- ${name}:end -->`;
  const begin = markdown.indexOf(start);
  const finish = markdown.indexOf(end, begin + start.length);
  if (begin < 0 || finish < 0 || markdown.indexOf(start, begin + start.length) >= 0) return null;
  return {text: markdown.slice(begin + start.length, finish), line: markdown.slice(0, begin + start.length).split('\n').length};
}

function tableRows(block){
  if (!block) return [];
  return block.text.split(/\r?\n/).map((text, index) => {
    if (!text.trim().startsWith('|')) return null;
    const cells = text.trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/).map(cell => cell.trim());
    if (cells.every(cell => /^:?-{3,}:?$/.test(cell))) return null;
    return {cells, line: block.line + index};
  }).filter(Boolean);
}

function fieldsFrom(block){
  return new Map(tableRows(block).filter(row => row.cells.length >= 2).map(row => [plainText(row.cells[0]), row.cells[1]]));
}

function parseBoard(markdown, name){
  const block = markedBlock(markdown, name);
  const rows = tableRows(block);
  if (!block || !rows.length) return null;
  const headers = rows[0].cells.map(plainText);
  return {headers, rows: rows.slice(1).map(row => ({
    line: row.line, fields: Object.fromEntries(headers.map((header, index) => [header, row.cells[index] || '']))
  }))};
}

function maintenanceDocument(file){
  return file === 'AGENTS.md'
    || (file.startsWith('docs/') && !file.startsWith('docs/reference/') && file !== 'docs/DOCUMENT_INDEX.md')
    || file.startsWith('issues/')
    || /^prototypes\/.+\/README\.md$/.test(file);
}

function checkProjectGovernance(rootDirectory){
  const root = path.resolve(rootDirectory);
  const errors = [];
  const add = (code, file, message, line = 1) => errors.push({code, file, line, message});
  const files = markdownFiles(root);
  const contents = new Map(files.map(file => [file, fs.readFileSync(path.join(root, file), 'utf8')]));
  const read = file => contents.get(file) || '';
  for (const file of requiredDocuments){
    if (!contents.has(file)) add('missingdocument', file, '缺少关键维护文档');
  }

  for (const file of files){
    for (const link of extractMarkdownLinks(read(file))){
      const resolved = localTarget(root, file, link.target);
      if (resolved && (resolved.error || !fs.existsSync(resolved.absolute))){
        add('brokenlink', file, `${link.target}：${resolved.error || '目标不存在'}`, link.line);
      }
    }
  }

  function baseline(file){
    const block = markedBlock(read(file), 'governance-baseline');
    const fields = fieldsFrom(block);
    if (!block || baselineFields.some(field => !plainText(fields.get(field) || ''))){
      add('missingbaseline', file, '治理修订固定块须包含治理版本、更新日期、关联 Issue');
      return null;
    }
    const issue = plainText(fields.get('关联 Issue')).match(/\bISSUE-\d+\b/);
    const value = {
      version: plainText(fields.get('治理版本')),
      date: plainText(fields.get('更新日期')),
      issue: issue ? issue[0] : ''
    };
    if (!/^g\d+(?:\.\d+)+$/.test(value.version) || !/^\d{4}-\d{2}-\d{2}$/.test(value.date) || !value.issue){
      add('invalidbaseline', file, '治理版本、更新日期或关联 Issue 的格式无效', block.line);
      return null;
    }
    return value;
  }
  const expectedBaseline = baseline('docs/governance/WORKFLOW.md');
  for (const file of baselineDocuments){
    const actual = baseline(file);
    if (expectedBaseline && actual && JSON.stringify(actual) !== JSON.stringify(expectedBaseline)){
      add('wrongbaseline', file, `治理修订头与 WORKFLOW 不一致，应为 ${expectedBaseline.version} / ${expectedBaseline.date} / ${expectedBaseline.issue}`);
    }
  }

  const registered = new Set(extractMarkdownLinks(read('docs/DOCUMENT_INDEX.md')).map(link => {
    const resolved = localTarget(root, 'docs/DOCUMENT_INDEX.md', link.target);
    return resolved && !resolved.error ? resolved.relative : null;
  }).filter(Boolean));
  for (const file of files.filter(maintenanceDocument)){
    if (!registered.has(file)) add('unindexeddocument', file, '维护文档尚未登记到 DOCUMENT_INDEX');
  }
  for (const file of indexedPrograms){
    if (fs.existsSync(path.join(root, file)) && !registered.has(file)){
      add('unindexedprogram', file, '治理检查程序或回归测试尚未登记到 DOCUMENT_INDEX');
    }
  }

  function evidenceLinks(sourceFile, value){
    return extractMarkdownLinks(value).filter(link => {
      const resolved = localTarget(root, sourceFile, link.target);
      if (resolved) return !resolved.error && fs.existsSync(resolved.absolute) && fs.statSync(resolved.absolute).isFile();
      try { return ['http:', 'https:'].includes(new URL(link.target).protocol); } catch { return false; }
    });
  }
  function requireBoard(file, marker, headers){
    const board = parseBoard(read(file), marker);
    if (!board || headers.some(header => !board.headers.includes(header))){
      add('invalidboard', file, `${marker} 固定块缺失或表格缺少列：${headers.join('、')}`);
      return null;
    }
    return board;
  }

  const taskFile = 'docs/TASK_BOARD.md';
  const tasks = requireBoard(taskFile, 'task-board', ['任务ID', '状态', '交付文档']);
  if (tasks){
    const ids = new Set();
    for (const row of tasks.rows){
      const id = plainText(row.fields['任务ID']);
      const state = parseState(row.fields['状态'], taskStates);
      if (!id || ids.has(id) || !state){
        add('invalidtask', taskFile, `任务ID须非空且唯一，状态须为 ${taskStates.join(' / ')}`, row.line);
        continue;
      }
      ids.add(id);
      if (state[1] !== 'done') continue;
      const deliveries = evidenceLinks(taskFile, row.fields['交付文档']).map(link => localTarget(root, taskFile, link.target))
        .filter(resolved => resolved && !resolved.error && resolved.relative.startsWith('docs/delivery/') && resolved.relative.endsWith('.md'));
      if (!deliveries.length){
        add('missingdelivery', taskFile, `${id} 为 done，但没有存在于 docs/delivery/ 的交付文档链接`, row.line);
        continue;
      }
      for (const delivery of deliveries){
        const fields = fieldsFrom(markedBlock(read(delivery.relative), 'task-delivery'));
        if (deliveryFields.some(field => !plainText(fields.get(field) || '')) || plainText(fields.get('任务ID') || '') !== id){
          add('invaliddelivery', delivery.relative, `${id} 的 task-delivery 固定块须记录相同任务ID、代码解释、验收和项目进度`);
        }
        if (!registered.has(delivery.relative)) add('unindexeddelivery', delivery.relative, `${id} 的交付文档未登记到 DOCUMENT_INDEX`);
      }
    }
  }

  const issueFile = 'issues/index.md';
  const issues = requireBoard(issueFile, 'issue-board', ['编号', '类型', '状态', '验收证据', '合入状态']);
  if (issues){
    const ids = new Set();
    for (const row of issues.rows){
      const id = plainText(row.fields['编号']);
      const state = parseState(row.fields['状态'], issueStates);
      if (!/^ISSUE-\d+$/.test(id) || ids.has(id) || !state){
        add('invalidissue', issueFile, `Issue 编号须有效且唯一，状态须为 ${issueStates.join(' / ')}`, row.line);
        continue;
      }
      ids.add(id);
      if (!issueTypes.has(plainText(row.fields['类型']))){
        add('invalidissuetype', issueFile, `${id} 的类型须为 ${[...issueTypes].join(' / ')}`, row.line);
      }
      if (state[1] === 'closed' && !evidenceLinks(issueFile, row.fields['验收证据']).length){
        add('closedwithoutevidence', issueFile, `${id} 已关闭，须链接本地验收记录或外部证据`, row.line);
      }
      if (!plainText(row.fields['合入状态']) || plainText(row.fields['合入状态']).toLowerCase() === 'closed'){
        add('missingmergestatus', issueFile, `${id} 须独立记录合入状态，验收关闭不等同于合入`, row.line);
      }
    }
  }
  return {ok: errors.length === 0, errors, checkedFiles: files.length,
    checkedTasks: tasks ? tasks.rows.length : 0, checkedIssues: issues ? issues.rows.length : 0,
    baseline: expectedBaseline};
}

if (require.main === module){
  const result = checkProjectGovernance(process.argv[2] || process.cwd());
  for (const error of result.errors) console.error(`[${error.code}] ${error.file}:${error.line} ${error.message}`);
  if (result.ok) console.log(`治理检查通过：${result.checkedFiles} 份 Markdown、${result.checkedTasks} 项任务、${result.checkedIssues} 项 Issue。`);
  else console.error(`治理检查失败：${result.errors.length} 项问题。`);
  process.exitCode = result.ok ? 0 : 1;
}

module.exports = {checkProjectGovernance, extractMarkdownLinks};
