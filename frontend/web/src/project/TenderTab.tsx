// 为什么有这个文件：提取项目工作区「招标文件」页签（TenderPage）。
// 它解决什么问题：解耦招标文件上传、解析触发、原件下载与异常移除模态窗交互，降低 ProjectPages 行数。

import React, { useState } from 'react';
import { Alert, Button, Card, Drawer, Input, Modal, Space, Table, Tag, Tooltip, Upload } from 'antd';
import { DownloadOutlined, FileTextOutlined, ReloadOutlined, UploadOutlined, WarningOutlined } from '@ant-design/icons';
import { download, encodeFile } from '../shared/api.ts';
import { projectCan } from './project-team.ts';
import { useProject } from '../app/context.tsx';
import { OriginalPreview } from './OriginalPreview.tsx';
import type { TenderFile } from '../shared/types.ts';

export function TenderPage() {
  const { workspace, token, busy, mutate, report, navigate } = useProject();
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [removeFile, setRemoveFile] = useState<TenderFile | null>(null);
  const [removeReason, setRemoveReason] = useState('');

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
    if (file.size > 5 * 1024 * 1024) {
      report(new Error('当前联调版本支持 5MB 以内文件，请拆分后上传。'));
      return false;
    }
    setUploading(true);
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/files`, 'POST', {
        filename: file.name,
        content_base64: await encodeFile(file),
      });
    } catch {
      /* 统一入口已显示具体错误 */
    } finally {
      setUploading(false);
    }
    return false;
  }

  async function parse() {
    try {
      await mutate(`/api/v1/projects/${workspace.project.id}/parse`, 'POST', {});
      navigate('parse');
    } catch {
      /* 保留当前文件列表供重试 */
    }
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
            disabled={!workspace.files.length || !projectCan(workspace, 'prepare_sources') || uploading}
            onClick={parse}
          >
            解析招标文件
          </Button>
        </Space>
      </div>
      <Alert
        type="info"
        showIcon
        className="page-notice"
        message="招标文件先在本地提取文字；扫描件、.doc、Excel 与图片交给公司自建 RAGFlow 识别版面与文字"
        description="页码方式与能力限制随原文显示，解析完成也需要人确认。经 RAGFlow 识别的文件会标“RAGFlow 解析中”，稍后再次点击“开始解析”取回结果，识别结果请对照原件核对；未连接 RAGFlow 时这些格式会如实提示失败。"
      />
      <Card>
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
          <p className="ant-upload-hint">UTF-8 文本、Word（.docx/.doc）、PDF（含扫描件）、Excel、图片 · 每份不超过 5MB</p>
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
