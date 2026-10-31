// 为什么有这个文件：提取项目工作区「概览」页签（OverviewPage）。
// 它解决什么问题：解耦步骤流程、待办清单、分册进度与最近导出展示，精简 ProjectPages 巨石单体。

import React from 'react';
import { exportStatusMeta, getExportKindMeta } from './export-checks-core.ts';
import { Button, Card, Col, Collapse, Empty, List, Progress, Row, Steps, Tag } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';
import { formatTime, useProject, volumeName } from '../app/context.tsx';
import { useVolumesStatus, isVolumeFinalized } from './volume-api.ts';
import { projectVolumes, technicalOnly, volumeOptions } from './project-volumes.ts';
import { useProjectSettings } from './ProjectSettingsGroups.tsx';
import { mergeTodoItems } from './project-settings-core.ts';

export function ClockCircleSymbol() {
  return <span className="todo-circle">○</span>;
}

export function OverviewPage() {
  const { workspace, token, navigate } = useProject();
  const { volumes: volumesStatus } = useVolumesStatus(workspace.project.id, token, workspace.revision);
  const { settings } = useProjectSettings(workspace.project.id, token, workspace.revision);
  const steps = ['建立项目', '上传并解析', '确认与挂证据', '编制两册', '检查与导出'];
  const current = !workspace.files.length
    ? 0
    : !workspace.parse_confirmed
    ? 1
    : workspace.requirements.some(item => item.status !== 'rejected' && !item.response.trim())
    ? 2
    : workspace.chapters.some(item => !item.content.trim())
    ? 3
    : 4;

  const flowItems = [
    {
      title: '上传招标文件与补遗',
      detail: `${workspace.files.length} 个文件`,
      tab: 'tender',
      done: !!workspace.files.length,
    },
    {
      title: '逐条确认解析结果',
      detail: `${workspace.requirements.filter(item => item.status === 'pending').length} 条待确认，${workspace.conflicts.filter(item => item.status === 'pending').length} 个冲突`,
      tab: 'parse',
      done: workspace.parse_confirmed,
    },
    {
      title: '填回应要点并挂证据',
      detail: `${workspace.requirements.filter(item => item.status !== 'rejected' && !item.response.trim()).length} 条尚未响应`,
      tab: 'matrix',
      done:
        workspace.requirements.length > 0 &&
        workspace.requirements.filter(item => item.status !== 'rejected').every(item => item.response.trim()),
    },
    {
      title: '确认项目事实',
      detail: `${workspace.facts.filter(item => ['pending', 'needs_review'].includes(item.status)).length} 项待核对`,
      tab: 'facts',
      done: workspace.facts.every(item => !['pending', 'needs_review'].includes(item.status)),
    },
    {
      title: '编制技术与商务两册',
      detail: `${workspace.chapters.filter(item => item.content.trim()).length} / ${workspace.chapters.length} 章有已提交正文`,
      tab: 'editor',
      done: workspace.chapters.every(item => item.content.trim()),
    },
    {
      title: '运行检查并下载内部稿',
      detail: `${workspace.exports.filter(item => item.status === 'valid').length} 次有效输出`,
      tab: 'export',
      done: workspace.exports.some(item => item.status === 'valid'),
    },
  ];
  // 后台给出的待办（合作方缺协议、分册无负责人、内部截止临近、拟派人员占用等），每项可一键跳转
  const pendingItems = mergeTodoItems(flowItems, settings?.todos ?? []);
  const status = workspace.project_status;

  return (
    <>
      {status && <Card className="flow-card" size="small" data-testid="overview-status">项目状态：<Tag color={status.read_only ? 'default' : 'blue'}>{status.label}{status.result_label ? `（${status.result_label}）` : ''}</Tag>{status.read_only && <span className="muted">项目已取消，只读。</span>}</Card>}
      <Card className="flow-card">
        <Steps current={current} size="small" items={steps.map(title => ({ title }))} />
      </Card>
      <Row gutter={16}>
        <Col span={16}>
          <Card title="下一步该做什么">
            <List
              dataSource={pendingItems}
              renderItem={item => (
                <List.Item actions={[<Button type="link" onClick={() => navigate(item.tab)}>前往处理</Button>]}>
                  <List.Item.Meta
                    avatar={item.done ? <CheckCircleOutlined className="green" /> : <ClockCircleSymbol />}
                    title={<span className={item.done ? 'muted' : ''}>{item.title}</span>}
                    description={item.detail}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="分册进度" className="stack-card">
            {projectVolumes(workspace).map(volume => {
              const chapters = workspace.chapters.filter(item => item.volume === volume);
              return (
                <div key={volume} className="volume-progress">
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                    <b>{volumeName(volume)}</b>
                    {isVolumeFinalized(volumesStatus, volume) ? (
                      <Tag color="success" data-testid={`volume-${volume}-finalized-badge`}>已定稿</Tag>
                    ) : (
                      <Tag color="default" data-testid={`volume-${volume}-unfinalized-badge`}>编制中</Tag>
                    )}
                  </div>
                  <Progress
                    percent={
                      chapters.length
                        ? Math.round((chapters.filter(item => item.content.trim()).length / chapters.length) * 100)
                        : 0
                    }
                  />
                  <span className="muted">
                    已提交正文 {chapters.filter(item => item.content.trim()).length} / {chapters.length} 章
                  </span>
                </div>
              );
            })}
          </Card>
          <Card title="最近导出">
            {workspace.exports.length ? (
              workspace.exports
                .slice(-3)
                .reverse()
                .map(item => (
                  <p key={item.id}>
                    <Tag color={exportStatusMeta(item.status).color}>
                      {getExportKindMeta(item.kind).label} · {exportStatusMeta(item.status).label}
                    </Tag>
                    {item.batch_no ? `${item.batch_no} · ` : ''}
                    {formatTime(item.created_at)}
                  </p>
                ))
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有生成输出文件" />
            )}
          </Card>
        </Col>
      </Row>
      <Collapse
        className="page-notice"
        items={[
          {
            key: 'writing',
            label: '写作观察统计（项目）',
            children: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="统计尚未接通；不会以章节数量代替质量评价"
              />
            ),
          },
        ]}
      />
    </>
  );
}
