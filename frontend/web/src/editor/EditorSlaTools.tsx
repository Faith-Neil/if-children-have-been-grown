// 为什么有这个文件：提取编辑台项目事实与服务承诺变量插入工具条（EditorSlaTools）。
// 它解决什么问题：解耦事实选择器、SLA变量选择器及矩阵变量换算标记渲染，降低 EditorPage 行数。

import React from 'react';
import { Button, Select } from 'antd';
import { displaySlaValue } from '../admin/sla-form.ts';
import type { Workspace } from '../shared/types.ts';

export interface EditorSlaToolsProps {
  workspace: Workspace;
  factId: string;
  setFactId: (id: string) => void;
  slaKey: string;
  setSlaKey: (key: string) => void;
  held: boolean;
  combinedBusy: boolean;
  onInsertFact: () => void;
  onInsertVariable: () => void;
}

export function EditorSlaTools({
  workspace,
  factId,
  setFactId,
  slaKey,
  setSlaKey,
  held,
  combinedBusy,
  onInsertFact,
  onInsertVariable,
}: EditorSlaToolsProps) {
  const factOptions = workspace.facts
    .filter(fact => fact.source_type !== 'sla')
    .map(fact => ({
      value: fact.id,
      label: `${fact.key} · ${fact.value}`,
      disabled: fact.status !== 'confirmed',
    }));

  const slaOptions = (workspace.sla?.rows || []).map(row => ({
    value: row.var_key,
    label: `${row.label} · ${displaySlaValue(row.project_value, row.project_unit)}`,
    disabled: row.fact_status !== 'confirmed' || row.source_stale || workspace.sla?.template_stale,
  }));

  const activeFact = workspace.facts.find(fact => fact.id === factId);
  const activeSlaRow = workspace.sla?.rows.find(row => row.var_key === slaKey);

  return (
    <>
      <div className="sla-token-tools">
        <Select
          aria-label="选择已确认项目事实"
          placeholder="选择已确认的项目事实"
          value={factId || undefined}
          onChange={setFactId}
          options={factOptions}
        />
        <Button
          size="small"
          disabled={!held || combinedBusy || !factId || activeFact?.status !== 'confirmed'}
          onClick={onInsertFact}
        >
          插入事实变量
        </Button>
        <small className="muted">事实变量读取已确认值；文字改动仍须提交</small>
      </div>

      {workspace.sla && (
        <div className="sla-token-tools">
          <Select
            aria-label="选择已确认服务承诺变量"
            placeholder="选择已确认的服务变量"
            value={slaKey || undefined}
            onChange={setSlaKey}
            options={slaOptions}
          />
          <Button
            size="small"
            disabled={
              !held ||
              combinedBusy ||
              !slaKey ||
              workspace.sla.template_stale ||
              activeSlaRow?.fact_status !== 'confirmed'
            }
            onClick={onInsertVariable}
          >
            插入服务变量
          </Button>
          <small className="muted">导出使用矩阵当前值；变量按模板单位显示</small>
        </div>
      )}
    </>
  );
}
