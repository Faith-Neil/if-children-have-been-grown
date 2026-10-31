// 为什么有这个文件：企业设置“导出交付”页签里的公司 Word 模板（PRD v1.8 §5.6.2；权限矩阵只有公司管理员可改；APP-M2-T086）。
// 它解决什么问题：公司管理员上传或替换 .docx 模板，页面列出模板里读到并会用于导出的样式、以及沿用平台默认的项；
// 其他成员只能查看和下载模板原件。换模板只影响之后的导出。

import { useEffect, useState } from 'react';
import { App as AntApp, Button, Card, Empty, List, Popconfirm, Space, Tag, Typography, Upload } from 'antd';
import { DeleteOutlined, DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import { download, request, uploadRaw, userFacingMessage } from '../shared/api.ts';
import { templateUploadProblem, wordTemplatePaths, type WordTemplate } from './word-template-core.ts';

const { Text } = Typography;

type Props = { companyId: string; token: string | null; canEdit: boolean };

export function WordTemplateCard({ companyId, token, canEdit }: Props) {
  const { message } = AntApp.useApp();
  const [template, setTemplate] = useState<WordTemplate | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    request<{ template: WordTemplate | null }>(wordTemplatePaths.info(companyId), token)
      .then(result => { if (alive) setTemplate(result.template); })
      .catch(error => { if (alive) message.error(userFacingMessage(error)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [companyId, token]);  // eslint-disable-line react-hooks/exhaustive-deps

  async function upload(file: File) {
    const problem = templateUploadProblem(file);
    if (problem) { message.error(problem); return; }
    setLoading(true);
    try {
      const result = await uploadRaw<{ template: WordTemplate }>(wordTemplatePaths.upload(companyId, file.name), token, file, undefined, 'PUT');
      setTemplate(result.template);
      message.success('Word 模板已更新，之后的导出按新模板生成。');
    } catch (error) {
      message.error(userFacingMessage(error));
    } finally {
      setLoading(false);
    }
  }

  async function remove() {
    setLoading(true);
    try {
      await request(wordTemplatePaths.info(companyId), token, 'DELETE');
      setTemplate(null);
    } catch (error) {
      message.error(userFacingMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card size="small" title="公司 Word 模板" loading={loading} data-testid="word-template-card"
      extra={canEdit && (
        <Upload accept=".docx" showUploadList={false} beforeUpload={file => { void upload(file); return false; }}>
          <Button size="small" icon={<UploadOutlined />} data-testid="word-template-upload">{template ? '替换模板' : '上传模板'}</Button>
        </Upload>
      )}>
      {!template ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未上传，导出使用平台默认模板" />
      ) : (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Text strong>{template.filename}</Text>
            <Button type="link" size="small" icon={<DownloadOutlined />} disabled={!token}
              onClick={() => token && download(wordTemplatePaths.file(companyId), token, template.filename).catch(error => message.error(userFacingMessage(error)))}>
              下载
            </Button>
            {canEdit && (
              <Popconfirm title="删除后导出改用平台默认模板，已导出的文件不受影响。" okText="删除" cancelText="取消" onConfirm={remove}>
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>
            )}
          </Space>
          <List size="small" header="导出会用到的样式" dataSource={template.applied} data-testid="word-template-applied"
            renderItem={line => <List.Item>{line}</List.Item>} />
          {template.defaults.length > 0 && (
            <div>
              <Text type="secondary">模板里没有、沿用平台默认：</Text>
              {template.defaults.map(item => <Tag key={item}>{item}</Tag>)}
            </div>
          )}
        </Space>
      )}
    </Card>
  );
}
