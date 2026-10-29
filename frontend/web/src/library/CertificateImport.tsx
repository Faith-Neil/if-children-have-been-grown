// 为什么有这个文件：资料库里“从证书附件识别”：上传证书扫描件 → 知识库证书流程解析抽取 → 生成待核验资料。
// 它解决什么问题：资料管理员不必逐字录入证书名称、编号、发证机构、有效期；抽取结果只是草稿，
// 状态固定为“待核验”，必须对照原件确认后才可引用（PRD 原则 1）。

import React, { useState } from 'react';
import { Alert, Button, Modal, Progress, Space, Typography, Upload } from 'antd';
import { ScanOutlined } from '@ant-design/icons';
import { rawUploadPath, request, uploadRaw, uploadTooLarge } from '../shared/api.ts';
import { KB_UPLOAD_ACCEPT, kbApi } from './kb-admin-core.ts';

type Phase = 'idle' | 'uploading' | 'parsing' | 'drafting' | 'done' | 'failed';
const POLL_MS = 4000;
const POLL_LIMIT = 90; // 约 6 分钟；RAGFlow 排队较长时提示稍后在知识库管理里继续

export interface CertificateImportProps {
  token: string | null;
  disabled?: boolean;
  onDrafted?: () => void;
  wait?: (ms: number) => Promise<void>;
}

export function CertificateImport({ token, disabled, onDrafted, wait = ms => new Promise(r => setTimeout(r, ms)) }: CertificateImportProps) {
  const [open, setOpen] = useState(false);
  const [phase, setPhase] = useState<Phase>('idle');
  const [message, setMessage] = useState('');
  const [polls, setPolls] = useState(0);

  async function run(file: File) {
    setPhase('uploading'); setMessage(''); setPolls(0);
    try {
      const tooLarge = uploadTooLarge(file);
      if (tooLarge) throw new Error(tooLarge);
      const uploaded = await uploadRaw<{ document_id: string; status: string }>(
        rawUploadPath(`${kbApi.documents('certificate').split('?')[0]}/raw`, { filename: file.name, content_type: file.type }), token, file);
      setPhase('parsing');
      let status = uploaded.status;
      for (let i = 0; status !== 'synced' && i < POLL_LIMIT; i++) {
        if (status === 'failed') break;
        await wait(POLL_MS);
        setPolls(i + 1);
        const docs = await request<{ items: { document_id: string; status: string; message: string }[] }>(kbApi.documents('certificate'), token);
        const row = docs.items.find(d => d.document_id === uploaded.document_id);
        status = row?.status === 'unsynced' ? 'parsing' : (row?.status ?? status);
        if (row?.status === 'failed') { setMessage(row.message || '识别失败'); break; }
      }
      if (status !== 'synced') {
        setPhase('failed');
        setMessage(prev => prev || '识别仍在排队，请稍后到“知识库 › 知识库管理 › 数据集与文档 › 资质证书附件”里点“生成资料草稿”。');
        return false;
      }
      setPhase('drafting');
      const draft = await request<{ library_item: { name: string } }>(kbApi.certificateDraft(uploaded.document_id), token, 'POST', {});
      setPhase('done');
      setMessage(`已生成待核验资料“${draft.library_item.name}”。请对照原件核对名称、编号、有效期后确认。`);
      onDrafted?.();
    } catch (error) {
      setPhase('failed');
      setMessage(error instanceof Error ? error.message : '上传或识别失败');
    }
    return false;
  }

  const busy = phase === 'uploading' || phase === 'parsing' || phase === 'drafting';
  const percent = { idle: 0, uploading: 15, parsing: Math.min(85, 25 + polls * 3), drafting: 92, done: 100, failed: 100 }[phase];

  return (
    <>
      <Button icon={<ScanOutlined />} disabled={disabled} onClick={() => { setOpen(true); setPhase('idle'); setMessage(''); }} data-testid="certificate-import-button">
        从证书附件识别
      </Button>
      <Modal open={open} title="从证书附件识别资料" footer={null} maskClosable={!busy} closable={!busy} onCancel={() => setOpen(false)}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Paragraph type="secondary">
            上传证书、资质或合同的扫描件/照片（PDF、JPG、PNG），系统识别名称、编号、发证机构、持有人和有效期，生成一条“待核验”资料。识别结果可能有误，必须对照原件确认。
          </Typography.Paragraph>
          <Upload accept={KB_UPLOAD_ACCEPT.certificate} showUploadList={false} beforeUpload={file => run(file)} disabled={busy}>
            <Button type="primary" loading={busy} disabled={busy}>选择文件</Button>
          </Upload>
          {phase !== 'idle' && <Progress percent={percent} status={phase === 'failed' ? 'exception' : phase === 'done' ? 'success' : 'active'} />}
          {busy && <Typography.Text>{{ uploading: '正在上传…', parsing: '正在识别（OCR 与字段抽取）…', drafting: '正在生成资料草稿…' }[phase as 'uploading']}</Typography.Text>}
          {message && <Alert type={phase === 'done' ? 'success' : 'warning'} showIcon message={message} />}
        </Space>
      </Modal>
    </>
  );
}

export default CertificateImport;
