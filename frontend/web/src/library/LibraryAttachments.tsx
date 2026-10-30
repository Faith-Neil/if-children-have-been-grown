// 为什么有这个文件：资料详情里的附件扫描件（PRD v1.8 §5.4.7、§5.9.1 规则 7、R38、R42；APP-M2-T059、T198）。
// 它解决什么问题：上传证书、授权书、业绩证明的扫描件（加密保存），设置导出时插入的页码范围、是否敏感（加水印）、
// 是否带公司名称或标志（暗标分册不插）与功能点标签；下载原件记审计，数据都来自后台，没有示例数据。

import { useEffect, useState } from 'react';
import { App as AntApp, Button, InputNumber, Popconfirm, Select, Space, Switch, Table, Tag, Tooltip, Upload } from 'antd';
import { DeleteOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import { download, MAX_UPLOAD_BYTES, request, uploadRaw, userFacingMessage } from '../shared/api.ts';
import { formatTime } from '../app/context.tsx';
import {
  ATTACHMENT_ACCEPT, attachmentPaths, normalizeTags, pageRangeLabel, pageRangeProblem, sizeLabel, uploadProblem,
  type LibraryAttachment,
} from './attachments-core.ts';

type Props = { itemId: string; token: string | null; canEdit: boolean };

export function LibraryAttachments({ itemId, token, canEdit }: Props) {
  const { message } = AntApp.useApp();
  const [items, setItems] = useState<LibraryAttachment[]>([]);
  const [loading, setLoading] = useState(false);
  const [ranges, setRanges] = useState<Record<string, [number | null, number | null]>>({});

  async function load() {
    setLoading(true);
    try {
      const result = await request<{ items: LibraryAttachment[] }>(attachmentPaths.list(itemId), token);
      setItems(result.items);
      setRanges({});
    } catch (error) {
      message.error(userFacingMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [itemId]);  // eslint-disable-line react-hooks/exhaustive-deps

  async function upload(file: File) {
    const problem = uploadProblem(file, MAX_UPLOAD_BYTES);
    if (problem) { message.error(problem); return; }
    setLoading(true);
    try {
      const result = await uploadRaw<{ attachment: LibraryAttachment; duplicate: boolean }>(attachmentPaths.upload(itemId, file.name), token, file);
      message.success(result.duplicate ? '这份资料已有相同内容的附件，未重复保存。' : '附件已加密保存。');
      await load();
    } catch (error) {
      message.error(userFacingMessage(error));
      setLoading(false);
    }
  }

  async function patch(item: LibraryAttachment, body: Partial<LibraryAttachment>) {
    try {
      const result = await request<{ attachment: LibraryAttachment }>(attachmentPaths.item(item.id), token, 'PATCH', body, item.revision);
      setItems(current => current.map(row => row.id === item.id ? result.attachment : row));
      setRanges(current => { const next = { ...current }; delete next[item.id]; return next; });
    } catch (error) {
      message.error(userFacingMessage(error));
      void load();
    }
  }

  async function remove(item: LibraryAttachment) {
    try {
      await request(attachmentPaths.item(item.id), token, 'DELETE');
      setItems(current => current.filter(row => row.id !== item.id));
    } catch (error) {
      message.error(userFacingMessage(error));
    }
  }

  function saveRange(item: LibraryAttachment) {
    const [from, to] = ranges[item.id] ?? [item.page_from, item.page_to];
    const problem = pageRangeProblem(from, to, item.page_count);
    if (problem) { message.error(problem); return; }
    if (from === item.page_from && to === item.page_to) return;
    void patch(item, { page_from: from as number, page_to: to as number });
  }

  return (
    <div className="attachment-slot-section" data-testid="attachment-slot-section">
      <Space style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <strong>附件扫描件</strong>
        {canEdit && (
          <Upload accept={ATTACHMENT_ACCEPT} showUploadList={false} beforeUpload={file => { void upload(file); return false; }}>
            <Button size="small" icon={<UploadOutlined />} loading={loading} data-testid="attachment-upload-btn">上传扫描件</Button>
          </Upload>
        )}
      </Space>
      <Table<LibraryAttachment>
        size="small"
        rowKey="id"
        loading={loading}
        pagination={false}
        dataSource={items}
        locale={{ emptyText: '还没有扫描件' }}
        data-testid="attachment-table"
        columns={[
          {
            title: '文件', key: 'file',
            render: (_: unknown, item) => (
              <Space direction="vertical" size={0}>
                <span>{item.filename}</span>
                <span style={{ fontSize: 12, color: '#8c8c8c' }}>{sizeLabel(item.size_bytes)} · {formatTime(item.uploaded_at)}</span>
              </Space>
            ),
          },
          {
            title: '导出插入页', key: 'pages', width: 190,
            render: (_: unknown, item) => item.page_count === 1 || !canEdit ? pageRangeLabel(item) : (
              <Space size={4}>
                <InputNumber size="small" min={1} max={item.page_count} style={{ width: 56 }} aria-label="起始页"
                  value={(ranges[item.id] ?? [item.page_from, item.page_to])[0]}
                  onChange={value => setRanges(current => ({ ...current, [item.id]: [value, (current[item.id] ?? [item.page_from, item.page_to])[1]] }))}
                  onBlur={() => saveRange(item)} />
                ～
                <InputNumber size="small" min={1} max={item.page_count} style={{ width: 56 }} aria-label="结束页"
                  value={(ranges[item.id] ?? [item.page_from, item.page_to])[1]}
                  onChange={value => setRanges(current => ({ ...current, [item.id]: [(current[item.id] ?? [item.page_from, item.page_to])[0], value] }))}
                  onBlur={() => saveRange(item)} />
                <span style={{ fontSize: 12 }}>/ {item.page_count}</span>
              </Space>
            ),
          },
          {
            title: <Tooltip title="敏感附件导出时加水印">敏感</Tooltip>, key: 'sensitive', width: 64,
            render: (_: unknown, item) => (
              <Switch size="small" checked={item.is_sensitive} disabled={!canEdit} aria-label="敏感附件"
                onChange={value => void patch(item, { is_sensitive: value })} />
            ),
          },
          {
            title: <Tooltip title="附件上有公司名称或标志；暗标分册不插入">带公司标识</Tooltip>, key: 'identity', width: 92,
            render: (_: unknown, item) => (
              <Switch size="small" checked={item.shows_identity} disabled={!canEdit} aria-label="带公司标识"
                onChange={value => void patch(item, { shows_identity: value })} />
            ),
          },
          {
            title: '功能点标签', key: 'tags', width: 200,
            render: (_: unknown, item) => canEdit ? (
              <Select mode="tags" size="small" style={{ width: '100%' }} value={item.feature_tags} tokenSeparators={[',', '，', '、']}
                aria-label="功能点标签" placeholder="截图证明的功能点"
                onChange={(values: string[]) => void patch(item, { feature_tags: normalizeTags(values) })} />
            ) : item.feature_tags.map(tag => <Tag key={tag}>{tag}</Tag>),
          },
          {
            title: '操作', key: 'actions', width: 120,
            render: (_: unknown, item) => (
              <Space size={4}>
                <Button type="link" size="small" icon={<DownloadOutlined />} disabled={!token}
                  onClick={() => token && download(attachmentPaths.file(item.id), token, item.filename).catch(error => message.error(userFacingMessage(error)))}>
                  下载
                </Button>
                {canEdit && (
                  <Popconfirm title="删除这份扫描件？已导出的文件不受影响。" okText="删除" cancelText="取消" onConfirm={() => remove(item)}>
                    <Button type="link" size="small" danger icon={<DeleteOutlined />} aria-label="删除附件" />
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />
    </div>
  );
}
