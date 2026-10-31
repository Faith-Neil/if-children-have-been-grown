// 为什么有这个文件：提取项目工作区「招标文件」页签（TenderPage）。
// 它解决什么问题：解耦招标文件上传、解析触发、原件下载与异常移除模态窗交互，降低 ProjectPages 行数。

import React, { useState } from 'react';
import { Alert, Button, Card, Drawer, Input, Modal, Select, Space, Table, Tag, Tooltip, Upload } from 'antd';
import { DownloadOutlined, FileTextOutlined, ReloadOutlined, UploadOutlined, WarningOutlined } from '@ant-design/icons';
import { MAX_UPLOAD_MB, download, rawUploadPath, request, uploadRaw, uploadTooLarge } from '../shared/api.ts';
import { projectCan } from './project-team.ts';
import { useProject } from '../app/context.tsx';
import { OriginalPreview } from './OriginalPreview.tsx';
import { AddendumDiffDrawer } from './AddendumDiffDrawer.tsx';
import { FILE_ROLE_OPTIONS, PARSE_SERVICE_OPTIONS, durationLabel, hasAddendumDiff, replacementOptions, retryBody, roleChangeAllowed, type ParseServiceChoice } from './parse-postprocess-core.ts';
import type { FileRole, Job, TenderFile } from '../shared/types.ts';
import { JobProgressWithSse } from '../status/JobProgress.tsx';
import { jobFromStatus, type BackendJobStatus } from '../status/job-progress-sse.ts';
import type { JobProgressData } from '../status/job-progress.ts';

/** 页面打开时仍在进行的解析任务（后台任务在任务列表里留有摘要）。 */
export function activeParseJob(jobs: Job[] | undefined): Job | undefined {
  return (jobs ?? []).filter(job => job.type === 'parse' && ['queued', 'running'].includes(job.status))
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))[0];
}

export function TenderPage() {
  const { workspace, token, busy, mutate, reload, report, navigate } = useProject();
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [removeFile, setRemoveFile] = useState<TenderFile | null>(null);
  const [removeReason, setRemoveReason] = useState('');
  const [uploadRole, setUploadRole] = useState<FileRole>('tender');
  const [diffFile, setDiffFile] = useState('');
  const [supersede, setSupersede] = useState<TenderFile | null>(null);
  const [replacementId, setReplacementId] = useState('');
  const [supersedeReason, setSupersedeReason] = useState('');
  const [retryFile, setRetryFile] = useState<TenderFile | null>(null);
  const [retryService, setRetryService] = useState<ParseServiceChoice>('ragflow');
  // 解析在后台执行（APP-M2-T020）：进度经事件流实时显示，断线时自动改为轮询
  const [parseJob, setParseJob] = useState<{ id: string; initial: JobProgressData } | null>(() => {
    const active = activeParseJob(workspace.jobs);
    return active ? { id: active.id, initial: jobFromStatus(active) } : null;
  });
  const [parseJobDone, setParseJobDone] = useState(false);

  async function removeUpload() {
    if (!removeFile || !removeReason.trim()) {
      report(new Error('请说明移除原因，方便后续核对。'));
      return;
    }
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/files/${removeFile.id}`, 'DELETE', {
        reason: removeReason.trim(),
      });
      setRemoveFile(null);
      setRemoveReason('');
    } catch {
      /* 保留理由和选中文件，后台拒绝时显示实际原因 */
    }
  }

  async function upload(file: File) {
    const tooLarge = uploadTooLarge(file);
    if (tooLarge) {
      report(new Error(tooLarge));
      return false;
    }
    setUploading(true);
    try {
      // 二进制直传：大扫描件不先转 base64
      await uploadRaw(rawUploadPath(`/api/v1/projects/${workspace.project.id}/files/raw`, { filename: file.name, file_role: uploadRole }),
        token, file, workspace.revision);
    } catch (error) {
      report(error);
    } finally {
      await reload().catch(report);
      setUploading(false);
    }
    return false;
  }

  async function changeRole(file: TenderFile, role: FileRole) {
    if (!roleChangeAllowed(file, role)) { report(new Error('已解析的文件不能在补遗/澄清与其他类型之间切换。')); return; }
    try { await mutate(`/api/v1/projects/${workspace.project.id}/files/${file.id}/role`, 'POST', { file_role: role }); } catch { /* 后台拒绝原因已显示 */ }
  }

  async function submitSupersede() {
    if (!supersede || !replacementId || !supersedeReason.trim()) { report(new Error('请选择新版文件并写明理由。')); return; }
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/files/${supersede.id}/supersede`, 'POST',
        { replacement_file_id: replacementId, reason: supersedeReason.trim() });
      setSupersede(null); setReplacementId(''); setSupersedeReason('');
    } catch { /* 保留输入 */ }
  }

  async function parse(body: Record<string, unknown> = {}) {
    try {
      const job = await mutate(`/api/v1/projects/${workspace.project.id}/parse/jobs`, 'POST', body) as BackendJobStatus;
      setParseJobDone(false); setParseJob({ id: job.id, initial: jobFromStatus(job) });
    } catch {
      /* 保留当前文件列表供重试 */
    }
  }

  async function parseFinished(job: JobProgressData) {
    await reload().catch(report);
    if (job.status === 'completed') { setParseJob(null); navigate('parse'); }
  }

  async function cancelParse(jobId: string) {
    try { await request(`/api/v1/jobs/${encodeURIComponent(jobId)}/cancel`, token, 'POST'); } catch (error) { report(error); }
  }

  async function retryParse(jobId: string) {
    try {
      const job = await request<BackendJobStatus>(`/api/v1/jobs/${encodeURIComponent(jobId)}/retry`, token, 'POST');
      setParseJob({ id: `${job.id}`, initial: jobFromStatus(job) });
    } catch (error) { report(error); }
  }

  function sample() {
    const text =
      '合成招标文件：星河数据库维保服务项目\n招标编号：DEMO-2026-001\n投标截止时间：2026-12-31T17:00:00+08:00\n服务期限：12个月\n采购人：星河科技（虚构）\n★技术要求：提供数据库日常巡检，每月提交巡检报告。\n技术要求：重大故障响应不超过30分钟，处理方案由双方核对。\n商务要求：投标人应提供有效企业资质证明。\n商务要求：提供同类项目业绩证明，所有资料仅使用合成测试数据。\n';
    const url = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = '合成招标示例.txt';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <h2>招标文件</h2>
          <p>上传原件后，提取条款与项目事实。结果需人工逐项核对。</p>
        </div>
        <Space>
          <Button onClick={sample} icon={<DownloadOutlined />}>
            下载合成示例
          </Button>
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            loading={busy}
            disabled={!workspace.files.length || !projectCan(workspace, 'prepare_sources') || uploading
              || (!!parseJob && !['completed', 'failed', 'cancelled'].includes(parseJob.initial.status) && !parseJobDone)}
            onClick={() => void parse()}
          >
            解析招标文件
          </Button>
        </Space>
      </div>
      {parseJob && (
        <Card size="small" className="page-notice" data-testid="parse-job-card">
          <JobProgressWithSse key={parseJob.id + parseJob.initial.status} jobId={parseJob.id} token={token} initialJob={parseJob.initial}
            showSteps={false} onTerminal={job => { setParseJobDone(true); void parseFinished(job); }}
            onCancel={projectCan(workspace, 'prepare_sources') ? id => void cancelParse(id) : undefined}
            onRetry={projectCan(workspace, 'prepare_sources') ? id => { setParseJobDone(false); void retryParse(id); } : undefined} />
        </Card>
      )}
      <Alert
        type="info"
        showIcon
        className="page-notice"
        message="招标文件先在本地提取文字；扫描件、.doc、Excel 与图片交给公司自建 RAGFlow 识别版面与文字"
        description="页码方式与能力限制随原文显示，解析完成也需要人确认。经 RAGFlow 识别的文件标“RAGFlow 解析中”，解析任务在后台自动取回结果，可离开本页；识别结果请对照原件核对；未连接 RAGFlow 时这些格式会如实提示失败。"
      />
      <Card>
        <Space style={{ marginBottom: 12 }}>
          <span>本次上传的文件类型</span>
          <Select<FileRole> value={uploadRole} options={FILE_ROLE_OPTIONS} onChange={setUploadRole} style={{ width: 160 }}
            aria-label="上传文件类型" data-testid="upload-role-select" disabled={busy || uploading || !projectCan(workspace, 'prepare_sources')} />
        </Space>
        <Upload.Dragger
          accept=".txt,.md,.docx,.doc,.pdf,.xls,.xlsx,.png,.jpg,.jpeg"
          beforeUpload={file => upload(file)}
          showUploadList={false}
          disabled={busy || uploading || !projectCan(workspace, 'prepare_sources')}
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">拖入招标文件、补遗或附件，或点击选择</p>
          <p className="ant-upload-hint">UTF-8 文本、Word（.docx/.doc）、PDF（含扫描件）、Excel、图片 · 每份不超过 {MAX_UPLOAD_MB}MB</p>
        </Upload.Dragger>
        <Table
          className="file-table"
          size="small"
          rowKey="id"
          dataSource={workspace.files}
          pagination={false}
          columns={[
            {
              title: '文件名称',
              dataIndex: 'filename',
              render: (value: string) => (
                <Space>
                  <FileTextOutlined />
                  {value}
                </Space>
              ),
            },
            {
              title: '类型',
              dataIndex: 'file_role',
              render: (value: FileRole | undefined, item: TenderFile) => (
                <Select<FileRole> size="small" style={{ width: 120 }} value={value ?? 'tender'} options={FILE_ROLE_OPTIONS}
                  aria-label="文件类型" data-testid="file-role-select"
                  disabled={busy || !projectCan(workspace, 'prepare_sources') || !!item.superseded_by}
                  onChange={role => void changeRole(item, role)} />
              ),
            },
            {
              title: '版本 / 上传人',
              render: (_, item: TenderFile) => (
                <span data-testid="file-version">
                  v{item.version_no ?? 1}{item.superseded_by ? <Tag style={{ marginLeft: 4 }}>已被替代</Tag> : null}
                  <br /><span className="muted">{item.uploaded_by_name || '—'}{item.uploaded_at ? ` · ${item.uploaded_at.slice(0, 16).replace('T', ' ')}` : ''}</span>
                </span>
              ),
            },
            {
              title: '解析服务 / 耗时',
              render: (_, item: TenderFile) => (
                <span data-testid="file-parse-service">
                  {item.parse_service_label || '—'}{item.reused ? <Tag color="cyan" style={{ marginLeft: 4 }}>复用</Tag> : null}
                  <br /><span className="muted">{durationLabel(item.parse_duration_ms)}</span>
                </span>
              ),
            },
            {
              title: '大小',
              dataIndex: 'size',
              render: (value: number) => `${Math.round((value / 1024) * 10) / 10} KB`,
            },
            {
              title: '状态',
              dataIndex: 'status',
              render: (value: string) => (
                <Tag color={value === 'parsed' ? 'green' : value === 'failed' ? 'red' : value === 'parsing_remote' ? 'processing' : 'blue'}>
                  {value === 'parsed' ? '已解析' : value === 'failed' ? '解析失败' : value === 'parsing_remote' ? 'RAGFlow 解析中' : '已上传'}
                </Tag>
              ),
            },
            {
              title: '原文与说明',
              render: (_, item) => (
                <Space>
                  {item.status === 'parsed' && <a onClick={() => setSelectedFile(item.id)}>查看原文</a>}
                  <Button
                    type="link"
                    size="small"
                    onClick={() => download(item.download_url, token, item.filename).catch(report)}
                  >
                    下载原件
                  </Button>
                  {item.warnings?.length > 0 && (
                    <Tooltip title={item.warnings.join('；')}>
                      <WarningOutlined className="orange" />
                    </Tooltip>
                  )}
                  {hasAddendumDiff(item) && <a data-testid="addendum-diff-link" onClick={() => setDiffFile(item.id)}>补遗差异</a>}
                  {replacementOptions(item, workspace.files).length > 0 && projectCan(workspace, 'prepare_sources') && (
                    <Button type="link" size="small" data-testid="supersede-button" disabled={busy}
                      onClick={() => { setSupersede(item); setReplacementId(''); setSupersedeReason(''); }}>设为被替代</Button>
                  )}
                  {['parsed', 'failed'].includes(item.status) && projectCan(workspace, 'prepare_sources') && (
                    <Button type="link" size="small" data-testid="retry-service-button" disabled={busy || uploading}
                      onClick={() => { setRetryFile(item); setRetryService(item.parse_service === 'ragflow-deepdoc' ? 'local' : 'ragflow'); }}>换服务重试</Button>
                  )}
                  {['uploaded', 'failed', 'parsing_remote'].includes(item.status) && (
                    <Button
                      type="link"
                      danger
                      size="small"
                      disabled={busy || uploading || !projectCan(workspace, 'prepare_sources')}
                      onClick={() => {
                        setRemoveFile(item);
                        setRemoveReason('');
                      }}
                    >
                      移除上传
                    </Button>
                  )}
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        title="移除失败或未解析的上传"
        open={!!removeFile}
        onCancel={() => setRemoveFile(null)}
        onOk={removeUpload}
        okText="按上述原因移除"
        cancelText="保留文件"
        confirmLoading={busy}
        okButtonProps={{
          danger: true,
          disabled: !removeReason.trim() || !projectCan(workspace, 'prepare_sources'),
        }}
      >
        <Alert
          showIcon
          type="warning"
          message={`准备移除：${removeFile?.filename ?? ''}`}
          description="只移除当前项目中的这一份上传。已有解析条款的文件不能在这里移除，避免来源断开；如需保留，请先下载原件。移除会要求重新确认解析结果。"
        />
        <Input.TextArea
          style={{ marginTop: 16 }}
          aria-label="移除上传的原因"
          value={removeReason}
          onChange={event => setRemoveReason(event.target.value)}
          maxLength={2000}
          placeholder="例如：误传了扫描件，将改用可解析的文字版"
        />
      </Modal>
      <Modal title="设为被替代（版本链）" open={!!supersede} onCancel={() => setSupersede(null)} onOk={() => void submitSupersede()}
        okText="确认替代" cancelText="取消" confirmLoading={busy} okButtonProps={{ disabled: !replacementId || !supersedeReason.trim() }}>
        <Alert showIcon type="info" message={`旧版：${supersede?.filename ?? ''}`}
          description="本文件的条目标“所在文件已被替代”（不删除）；人工改过的回到待确认；未处理的疑似遗漏随之排除。" />
        <Select style={{ width: '100%', marginTop: 12 }} placeholder="选择同类型、在其后上传的新版文件" value={replacementId || undefined}
          onChange={setReplacementId} data-testid="supersede-target"
          options={(supersede ? replacementOptions(supersede, workspace.files) : []).map(f => ({ value: f.id, label: `${f.filename}（v${f.version_no ?? 1}）` }))} />
        <Input.TextArea style={{ marginTop: 12 }} aria-label="替代理由" value={supersedeReason} maxLength={2000}
          onChange={event => setSupersedeReason(event.target.value)} placeholder="理由（必填），例如重新发布的正式版" />
      </Modal>
      <Modal title="换一个解析服务重试" open={!!retryFile} onCancel={() => setRetryFile(null)} okText="重新解析" cancelText="取消"
        onOk={() => { if (retryFile) { void parse(retryBody(retryService, retryFile.id)); setRetryFile(null); } }}>
        <p>文件：{retryFile?.filename}（当前：{retryFile?.parse_service_label || '尚未解析'}）</p>
        <Select<ParseServiceChoice> style={{ width: '100%' }} value={retryService} options={[...PARSE_SERVICE_OPTIONS]} onChange={setRetryService}
          aria-label="解析服务" data-testid="retry-service-select" />
      </Modal>
      <AddendumDiffDrawer fileId={diffFile} onClose={() => setDiffFile('')} />
      <Drawer
        title="实际招标原文"
        width={760}
        open={!!selectedFile}
        onClose={() => setSelectedFile('')}
      >
        <OriginalPreview source={selectedFile ? { file_id: selectedFile, page: 1, quote: '' } : null} />
      </Drawer>
    </>
  );
}
