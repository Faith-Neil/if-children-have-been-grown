// 为什么有这个文件：技术分册覆盖视图（五列），对齐 Requirement→ResponseTask 架构。
// 它解决什么问题：去掉归属分册/证据等两册噪音列；点行跳编辑台对应节。

import React, { useMemo, useState } from 'react';
import { Alert, Button, Card, Input, Table, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import type { CoverageRow } from '../shared/types.ts';

const RISK_LABEL: Record<string, string> = {
  critical: '废标风险',
  high: '高',
  medium: '中',
  low: '低',
};

const STATUS_LABEL: Record<string, string> = {
  not_started: '未生成',
  pending: '未生成',
  generated: '已生成',
  needs_confirm: '待确认',
  confirmed: '已确认',
  gap: '存在缺口',
  not_applicable: '不适用',
};

export function CoverageView() {
  const { workspace, navigate } = useProject();
  const [search, setSearch] = useState('');
  const rows = useMemo(() => {
    const source = (workspace.coverage_rows ?? []) as CoverageRow[];
    const q = search.trim();
    if (!q) return source;
    return source.filter(row =>
      row.text.includes(q)
      || (row.outline_title || '').includes(q)
      || (row.outline_number || '').includes(q),
    );
  }, [workspace.coverage_rows, search]);

  const validation = workspace.plan_validation;
  const stats = {
    total: rows.length,
    rejection: rows.filter(row => row.is_rejection_criterion).length,
    generated: rows.filter(row => ['generated', 'confirmed', 'needs_confirm'].includes(row.response_status)).length,
    gaps: rows.filter(row => row.response_status === 'gap' || row.generation_status === 'failed').length,
  };

  return (
    <div data-testid="coverage-view">
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
        <Card size="small"><span className="muted">要求 </span><strong>{stats.total}</strong></Card>
        <Card size="small"><span className="muted">废标相关 </span><strong>{stats.rejection}</strong></Card>
        <Card size="small"><span className="muted">已生成 </span><strong>{stats.generated}</strong></Card>
        <Card size="small"><span className="muted">缺口 </span><strong>{stats.gaps}</strong></Card>
      </div>
      <Alert
        type="info"
        showIcon
        className="page-notice"
        data-testid="coverage-view-notice"
        style={{ marginBottom: 8 }}
        message="覆盖视图（可选）"
        description="招标要求 → 响应任务 → 目标章节。不挡「开始生成」与导出。"
        action={<Button size="small" type="link" onClick={() => navigate('editor')}>回编辑台</Button>}
      />
      {validation && validation.passed === false && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
          data-testid="plan-validation-warning"
          message="生成计划校验未全部通过"
          description={(validation.issues || []).join('；')}
        />
      )}
      <Card size="small" styles={{ body: { padding: 0 } }}>
        <div style={{ padding: 8 }}>
          <Input
            allowClear
            placeholder="搜索要求 / 章节"
            value={search}
            onChange={event => setSearch(event.target.value)}
            style={{ width: 280 }}
            data-testid="coverage-search"
          />
        </div>
        <Table
          rowKey={row => `${row.task_id}-${row.requirement_id}`}
          size="small"
          pagination={{ pageSize: 12, size: 'small' }}
          dataSource={rows}
          onRow={row => ({
            style: { cursor: 'pointer' },
            onClick: () => navigate('editor'),
            'data-testid': `coverage-row-${row.requirement_id}`,
          })}
          columns={[
            {
              title: '招标要求',
              dataIndex: 'text',
              width: 360,
              render: (value: string, row) => (
                <>
                  <div>{value}</div>
                  {row.is_rejection_criterion && <Tag color="red">废标相关</Tag>}
                </>
              ),
            },
            {
              title: '风险',
              dataIndex: 'risk_level',
              width: 100,
              render: (value: string) => (
                <Tag color={value === 'critical' ? 'red' : value === 'high' ? 'orange' : 'default'}>
                  {RISK_LABEL[value] || value}
                </Tag>
              ),
            },
            {
              title: '原文出处',
              width: 140,
              render: (_, row) => (
                <span className="muted">
                  {row.source_filename || '招标文件'}
                  {row.source_page != null ? ` · p.${row.source_page}` : ''}
                </span>
              ),
            },
            {
              title: '目标章节',
              width: 180,
              render: (_, row) => (
                <Button type="link" size="small" onClick={event => { event.stopPropagation(); navigate('editor'); }}>
                  {[row.outline_number, row.outline_title].filter(Boolean).join(' ') || '未挂目录'}
                </Button>
              ),
            },
            {
              title: '响应状态',
              dataIndex: 'response_status',
              width: 110,
              render: (value: string) => STATUS_LABEL[value] || value,
            },
          ]}
        />
      </Card>
    </div>
  );
}
