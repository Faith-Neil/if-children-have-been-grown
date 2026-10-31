// 为什么有这个文件：在服务承诺矩阵页顶部显示“需复核”传播（APP-M2-T122）和判定汇总（APP-M2-T119）。
// 它解决什么问题：模板、来源或取值变化后，负责人一眼看到哪些指标要重新核对、原因，以及哪些章节引用了它们并可直接跳到编辑台。

import { useCallback, useEffect, useState } from 'react';
import { Alert, Button, Space, Table, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useProject } from '../app/context.tsx';
import { editorChapterPath } from '../app/app-route.ts';
import type { SlaPropagation } from '../shared/types.ts';
import { fetchSlaPropagation, propagationHeadline, propagationSeverity, reasonColor } from './sla-propagation.ts';

export function SlaPropagationPanel() {
  const { workspace, token, navigate, report } = useProject();
  const [data, setData] = useState<SlaPropagation | null>(null);
  const [loading, setLoading] = useState(false);
  const projectId = workspace.project.id;
  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await fetchSlaPropagation(projectId, token)); } catch (error) { report(error); } finally { setLoading(false); }
  }, [projectId, token, report]);
  useEffect(() => { void load(); }, [load, workspace.revision]);
  const flagged = (data?.rows ?? []).filter(row => row.reasons.length);
  return (
    <div data-testid="sla-propagation" className="stack-card">
      <Alert
        type={propagationSeverity(data)}
        showIcon
        message={propagationHeadline(data)}
        description={data?.selected ? '以下原因来自后台判定；修改取值、来源或模板后须逐项重新确认，承诺函与引用章节随之失效。' : undefined}
        action={<Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={() => void load()}>刷新</Button>}
      />
      {data && flagged.length > 0 && (
        <Table
          size="small"
          rowKey="var_key"
          pagination={false}
          dataSource={flagged}
          columns={[
            { title: '指标', render: (_, row) => <b>{row.label}</b> },
            { title: '需处理的原因', render: (_, row) => <Space size={[4, 4]} wrap>{row.reasons.map(reason => <Tag key={reason.code} color={reasonColor(reason.code)} title={reason.label}>{reason.label}</Tag>)}</Space> },
            { title: '引用本指标的章节', render: (_, row) => row.chapters.length
              ? <Space size={[4, 4]} wrap>{row.chapters.map(chapter => <a key={chapter.chapter_id} onClick={() => navigate(editorChapterPath(projectId, chapter.chapter_id))}>{chapter.title}</a>)}</Space>
              : <span className="muted">暂无章节引用</span> },
          ]}
        />
      )}
      {data && data.chapters.some(chapter => chapter.issues.length) && (
        <Table
          size="small"
          rowKey="chapter_id"
          pagination={false}
          dataSource={data.chapters.filter(chapter => chapter.issues.length)}
          columns={[
            { title: '章节', render: (_, chapter) => <a onClick={() => navigate(editorChapterPath(projectId, chapter.chapter_id))}>{chapter.title}</a> },
            { title: '正文与服务承诺不一致', render: (_, chapter) => <ul>{chapter.issues.map(issue => <li key={`${issue.code}-${issue.message}`}>{issue.message}</li>)}</ul> },
          ]}
        />
      )}
    </div>
  );
}
