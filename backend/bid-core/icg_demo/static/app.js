/* 为什么有这个文件：把演示页面上的操作连接到真实后端接口。
   它解决什么问题：让权限、保存、版本、检查和下载反馈来自后台。 */
'use strict';
const $ = id => document.getElementById(id);
const state = {token:null,user:null,accounts:[],chapter:null,lease:null,sequence:0,editBaseRevision:null,savedDraft:null,draftConflict:false,draftResolution:null,check:null,suggestion:null,busy:false,epoch:0};
const actions = ['create-project','acquire','takeover','release','save-draft','commit','suggest','apply-suggestion','check','export','refresh','use-latest','restore-draft'];
function say(text,type=''){ $('message').textContent=text; $('message').className=type; }
function hasLease(){return Boolean(state.lease?.lease_token && state.chapter && state.lease.chapter_id===state.chapter.id && state.lease.owner_id===state.user?.id && Date.parse(state.lease.expires_at)>Date.now() && state.user.role!=='viewer');}
function editable(){return hasLease()&&!state.draftConflict;}
function dirty(){return Boolean(state.chapter && $('content').value !== state.chapter.content);}
function ensureEditable(){
  if(!hasLease())throw new Error('本页面没有有效编辑权，请先取得编辑权。');
  if(state.draftConflict)throw new Error('原草稿基于旧版本，请先核对最新正文并明确选择处理方式。');
  if(state.editBaseRevision!==state.chapter.revision)throw new Error('编辑基线已变化，请重新核对已提交正文。');
}
function renderSavedDraft(){
  $('saved-draft-panel').hidden=!state.savedDraft;
  if(!state.savedDraft)return;
  $('saved-draft-content').value=state.savedDraft.content;
  const origin='原草稿基于版本 '+state.savedDraft.base_revision+'，当前已提交版本为 '+state.chapter.revision+'。';
  $('saved-draft-status').textContent=origin+(state.draftConflict?' 存在版本冲突，尚未恢复；请先核对上方最新正文。':state.draftResolution==='restored'?' 已明确恢复并按当前版本重建草稿；原文本仍保留供复制。':state.draftResolution==='latest'?' 已选择继续使用已提交正文；原草稿仍保留供复制。':' 草稿尚未放入编辑框，恢复前请先核对正文。');
}
function render(){
  const has=Boolean(state.chapter),write=editable(),busy=state.busy;
  actions.forEach(id=>$(id).disabled=busy||!has);
  $('create-project').disabled=busy||!state.token||state.user?.role==='viewer';
  ['save-draft','commit'].forEach(id=>$(id).disabled=busy||!write);
  $('release').disabled=busy||!hasLease();
  $('acquire').disabled=busy||!has||hasLease()||state.user?.role==='viewer';
  $('takeover').disabled=busy||!has||hasLease()||state.user?.role!=='manager';
  $('use-latest').disabled=busy||!state.savedDraft||!$('review-latest').checked||dirty();
  $('restore-draft').disabled=busy||!state.savedDraft||!$('review-latest').checked||!hasLease()||dirty();
  $('review-latest').disabled=busy||dirty();
  $('apply-suggestion').disabled=busy||!write||!state.suggestion||state.suggestion.base_revision!==state.chapter.revision;
  $('export').disabled=busy||!has||dirty()||!state.check?.passed;
  $('check').disabled=busy||!has||dirty();
  $('suggest').disabled=busy||!has||state.user?.role==='viewer';
  $('content').readOnly=!write||busy;
  ['account','login','project','chapter'].forEach(id=>$(id).disabled=busy||(['project','chapter'].includes(id)&&!state.token));
  const activeLock=state.chapter?.lock&&Date.parse(state.chapter.lock.expires_at)>Date.now();
  $('lock-state').textContent=hasLease()?(state.draftConflict?'你持有编辑权，先核对旧草稿':'你正在编辑'):activeLock?(state.chapter.lock.owner_id===state.user?.id?'此账号的其他登录会话持有编辑权，本页面只读':'其他人持有编辑权'):has?'可申请编辑权':'尚未选择章节';
  $('lock-state').className='pill'+(hasLease()?' active':'');
  $('content-state').textContent=has?(state.draftConflict?'当前显示已提交版本；旧草稿冲突尚未处理':dirty()?'编辑框有未提交修改':'当前显示已提交版本'):'尚无正文';
  renderSavedDraft();
}
async function api(path,method='GET',data){
  const epoch=state.epoch;
  const headers={};if(state.token)headers.Authorization='Bearer '+state.token;
  if(data!==undefined)headers['Content-Type']='application/json';
  const response=await fetch(path,{method,headers,body:data===undefined?undefined:JSON.stringify(data)});
  const body=await response.json();
  if(epoch!==state.epoch)throw new Error('工作区已切换，请重新操作。');
  if(!response.ok){const error=new Error(body.error?.message||'请求未完成，请重试。');error.code=body.error?.code;error.status=response.status;throw error;}
  return body;
}
async function act(callback){
  if(state.busy)return;state.busy=true;render();
  try{await callback();}catch(error){if([409,423].includes(error.status))state.check=null;if(/LEASE|LOCK/i.test(error.code||''))state.lease=null;say(error.message,'error');}
  finally{state.busy=false;render();}
}
function resetChapter(){state.epoch++;state.chapter=null;state.lease=null;state.check=null;state.suggestion=null;state.sequence=0;state.editBaseRevision=null;state.savedDraft=null;state.draftConflict=false;state.draftResolution=null;$('review-latest').checked=false;$('saved-draft-panel').hidden=true;$('saved-draft-content').value='';$('content').value='';$('suggestion').textContent='尚无建议';$('check-result').textContent='尚未检查';}
function options(select,items,label){select.replaceChildren(...items.map(item=>{const option=document.createElement('option');option.value=item.id;option.textContent=label(item);return option;}));}
function showChapterHeading(){
  $('chapter-title').textContent=state.chapter.title;
  $('chapter-meta').textContent=(state.chapter.volume==='technical'?'技术册':'商务册')+' · 已提交版本 '+state.chapter.revision;
}
async function loadChapter(){
  resetChapter();if(!$('chapter').value){render();return;}
  state.chapter=await api('/api/chapters/'+encodeURIComponent($('chapter').value));
  showChapterHeading();
  // 初始总展示已提交正文，不把旧草稿暗中套到新的正式版本上。
  $('content').value=state.chapter.content;state.editBaseRevision=state.chapter.revision;
  state.savedDraft=state.chapter.draft?{...state.chapter.draft}:null;
  state.draftConflict=Boolean(state.savedDraft&&state.savedDraft.base_revision!==state.chapter.revision);
  state.sequence=state.savedDraft?.base_revision===state.chapter.revision?state.savedDraft.sequence:0;
  await history();render();
}
async function loadChapters(){
  if(!$('project').value){resetChapter();render();return;}
  const result=await api('/api/projects/'+encodeURIComponent($('project').value)+'/chapters');
  options($('chapter'),result.chapters,item=>(item.volume==='technical'?'技术册':'商务册')+' · '+item.title);
  await loadChapter();
}
async function loadProjects(selected){const result=await api('/api/projects');options($('project'),result.projects,item=>item.name);if(selected)$('project').value=selected;await loadChapters();}
function chapterPath(suffix=''){return '/api/chapters/'+encodeURIComponent(state.chapter.id)+suffix;}
function list(id,items,label){const entries=items.length?items:[null];$(id).replaceChildren(...entries.map(item=>{const li=document.createElement('li');li.textContent=item?label(item):'尚无记录';return li;}));}
const eventNames={'lock.acquire':'取得编辑权','lock.renew':'续期编辑权','lock.release':'释放编辑权','lock.takeover':'接管编辑权','draft.save':'保存草稿','version.commit':'提交版本','suggestion.generate':'生成演示建议','check.run':'检查正文','export.create':'生成Word','export.download':'下载Word','project.create':'创建项目'};
function actorName(id){return state.accounts.find(account=>account.id===id)?.name||(id==='demo-seed'?'初始示例':'演示账号');}
async function history(){
  const versions=await api(chapterPath('/versions'));const audit=await api(chapterPath('/audit'));
  list('versions',versions.versions.slice(-10).reverse(),item=>'版本 '+item.revision+' · '+actorName(item.actor_id)+' · '+(item.content||'').slice(0,70));
  list('audit',audit.events.slice(-10).reverse(),item=>(eventNames[item.action]||'后台操作')+' · '+actorName(item.actor_id)+(item.details?.reason?' · '+item.details.reason:''));
}
$('login').onclick=()=>act(async()=>{
  resetChapter();state.token=null;state.user=null;
  const result=await api('/api/demo/login','POST',{account_id:$('account').value});state.token=result.access_token;state.user=result.user;
  $('identity').textContent=state.user.name+' · '+(state.user.role==='viewer'?'只读账号':state.user.role==='manager'?'项目负责人':'编辑人员');
  await loadProjects();say('已进入工作区，只显示当前公司的项目。','success');
});
$('project').onchange=()=>act(loadChapters);$('chapter').onchange=()=>act(loadChapter);
$('create-project').onclick=()=>act(async()=>{const name=$('project-name').value.trim();if(!name)throw new Error('请填写项目名称。');const project=await api('/api/projects','POST',{name});await loadProjects(project.id);$('project-name').value='';say('项目已创建，技术和商务章节已准备好。','success');});
async function acquire(takeover){const lease=await api(chapterPath('/lock'),'POST',{takeover_reason:takeover?$('takeover-reason').value.trim():null});state.lease={...lease,chapter_id:state.chapter.id};state.chapter.lock={owner_id:lease.owner_id,expires_at:lease.expires_at};say(state.draftConflict?'已取得编辑权；原草稿与当前版本不同，请先核对并选择处理方式。':'已取得编辑权，可以修改正文。','success');await history();}
$('acquire').onclick=()=>act(()=>acquire(false));$('takeover').onclick=()=>act(async()=>{if(!$('takeover-reason').value.trim())throw new Error('请填写接管理由。');await acquire(true);});
$('release').onclick=()=>act(async()=>{if(!hasLease())throw new Error('本页面没有可释放的编辑权。');await api(chapterPath('/lock/release'),'POST',{lease_token:state.lease.lease_token});state.lease=null;state.chapter.lock=null;say('已释放编辑权。','success');await history();});
$('content').oninput=()=>{state.check=null;$('review-latest').checked=false;$('check-result').textContent='编辑框已修改，提交后重新检查。';render();};
$('review-latest').onchange=render;
async function verifiedLatestForDraft(){
  if(!state.savedDraft||!$('review-latest').checked)throw new Error('请先查看最新已提交正文，并勾选核对确认。');
  if(dirty())throw new Error('编辑框有未提交修改，请先保存或提交，避免恢复时覆盖它。');
  const latest=await api(chapterPath());
  if(latest.revision!==state.chapter.revision||latest.content!==state.chapter.content){
    state.chapter=latest;state.editBaseRevision=latest.revision;$('content').value=latest.content;
    state.sequence=latest.draft?.base_revision===latest.revision?latest.draft.sequence:0;
    state.draftConflict=true;state.draftResolution=null;state.check=null;state.suggestion=null;
    $('review-latest').checked=false;showChapterHeading();
    throw new Error('已提交正文再次更新，现已展示新版本。请重新查看并核对，再选择草稿处理方式。');
  }
  state.chapter.lock=latest.lock;
  return latest;
}
$('use-latest').onclick=()=>act(async()=>{await verifiedLatestForDraft();state.draftConflict=false;state.draftResolution='latest';$('review-latest').checked=false;say('已明确选择继续使用当前已提交正文，原草稿保留在下方供复制。','success');});
$('restore-draft').onclick=()=>act(async()=>{
  if(!hasLease())throw new Error('恢复前请先取得本页面的编辑权。');
  const latest=await verifiedLatestForDraft();
  const sequence=(latest.draft?.base_revision===latest.revision?latest.draft.sequence:0)+1;
  // 用户已经核对并明确恢复，且后台保存成功后，才建立新的草稿基线和编辑内容。
  const rebuilt=await api(chapterPath('/draft'),'PUT',{lease_token:state.lease.lease_token,base_revision:latest.revision,sequence,content:state.savedDraft.content});
  state.chapter.draft=rebuilt;state.sequence=rebuilt.sequence;state.editBaseRevision=rebuilt.base_revision;
  $('content').value=rebuilt.content;state.draftConflict=false;state.draftResolution='restored';state.check=null;state.suggestion=null;
  $('review-latest').checked=false;$('check-result').textContent='已明确恢复草稿；核对后提交新版本，再重新检查。';
  say('原草稿已按当前版本重新保存，尚未提交正式正文。请继续核对后再提交。','success');await history();
});
$('save-draft').onclick=()=>act(async()=>{ensureEditable();const sequence=state.sequence+1;await api(chapterPath('/draft'),'PUT',{lease_token:state.lease.lease_token,base_revision:state.editBaseRevision,sequence,content:$('content').value});state.sequence=sequence;say('草稿已保存在后台，尚未提交为正式版本。','success');await history();});
$('commit').onclick=()=>act(async()=>{
  ensureEditable();
  const result=await api(chapterPath('/versions'),'POST',{lease_token:state.lease.lease_token,base_revision:state.editBaseRevision,content:$('content').value,idempotency_key:crypto.randomUUID()});
  state.chapter.revision=result.revision;state.chapter.content=result.content;state.editBaseRevision=result.revision;state.chapter.draft=null;state.check=null;state.suggestion=null;state.sequence=0;
  $('chapter-meta').textContent=(state.chapter.volume==='technical'?'技术册':'商务册')+' · 已提交版本 '+result.revision;$('check-result').textContent='新版本尚未检查。';say('新版本已提交，正文和操作记录已更新。','success');await history();
});
$('suggest').onclick=()=>act(async()=>{state.suggestion=await api(chapterPath('/suggestions'),'POST',{instruction:$('instruction').value});$('suggestion').textContent=state.suggestion.content;say('演示建议已返回，正文尚未改变。','success');});
$('apply-suggestion').onclick=()=>act(async()=>{ensureEditable();if(state.suggestion.base_revision!==state.chapter.revision)throw new Error('正文版本已变化，请重新生成建议。');$('content').value=state.suggestion.content;state.check=null;$('review-latest').checked=false;$('check-result').textContent='采用后仍需提交新版本并检查。';say('建议已放入编辑框，请核对后提交。','success');});
$('check').onclick=()=>act(async()=>{state.check=await api(chapterPath('/checks'),'POST',{});$('check-result').textContent=state.check.passed?'已提交版本通过基础检查。':state.check.issues.map(item=>item.message).join('；');say(state.check.passed?'基础检查通过，可以下载此版本Word。':'检查未通过，请处理后重新提交。',state.check.passed?'success':'error');await history();});
$('export').onclick=()=>act(async()=>{
  if(dirty()||!state.check?.passed)throw new Error('请先提交正文并完成检查。');
  const result=await api(chapterPath('/exports'),'POST',{check_id:state.check.id});
  const response=await fetch(result.download_url,{headers:{Authorization:'Bearer '+state.token}});
  if(!response.ok){const problem=await response.json();throw new Error(problem.error?.message||'文件下载未完成。');}
  const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download=result.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);say('Word文件已生成并开始下载。','success');await history();
});
$('refresh').onclick=()=>act(async()=>{await history();say('已刷新后台记录。','success');});
setInterval(async()=>{if(!state.lease||state.busy)return;const chapter=state.chapter.id,lease=state.lease.lease_token;try{const renewed=await api(chapterPath('/lock/renew'),'POST',{lease_token:lease});if(state.chapter?.id===chapter&&state.lease?.lease_token===lease)state.lease={...renewed,chapter_id:chapter};}catch(error){if(state.chapter?.id===chapter&&state.lease?.lease_token===lease){state.lease=null;say('编辑权已失效，请重新取得。','error');render();}}},30000);
(async()=>{render();try{const accounts=await api('/api/demo/accounts');state.accounts=accounts.accounts;options($('account'),accounts.accounts,item=>item.name);$('connection').textContent='后台已连接';}catch(error){$('connection').textContent='后台连接失败';say(error.message,'error');}})();
