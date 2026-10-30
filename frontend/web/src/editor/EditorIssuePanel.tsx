// 为什么有这个文件：编辑台右栏“问题”页签（APP-M2-T166 / PRD v1.8 §5.11.2）。
// 它解决什么问题：列出本章全部问题（检查、章节循环、编辑后复查），可按状态、处理路径、规则筛选，点一条定位到正文段落；
// 点正文段落上的问题标记时只看这一段的问题。

import { Alert, Button, Empty, Segmented, Select, Space, Spin, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { filterIssues, issueOptions, severityColor, type ChapterIssue, type ChapterIssueList, type IssueFilter } from './chapter-issues-core.ts';

export interface EditorIssuePanelProps {
  data: ChapterIssueList | null;
  loading: boolean;
  error: string | null;
  filter: IssueFilter;
  onFilterChange: (next: IssueFilter) => void;
  activeId: string | null;
  /** 编辑框光标所在段落：这一段的问题加框显示 */
  highlightKey?: string | null;
  onLocate: (issue: ChapterIssue) => void;
  onReload: () => void;
}

export function EditorIssuePanel({ data, loading, error, filter, onFilterChange, activeId, highlightKey, onLocate, onReload }: EditorIssuePanelProps) {
  const items = data?.items ?? [];
  const shown = filterIssues(items, filter);
  const options = issueOptions(items);
  return (
    <div className="editor-issue-panel" data-testid="editor-issue-panel">
      <div className="issue-filters">
        <Segmented size="small" value={filter.status} onChange={value => onFilterChange({ ...filter, status: value as IssueFilter['status'] })}
          options={[{ value: 'open', label: `待处理 ${data?.counts.open ?? 0}` }, { value: 'all', label: `全部 ${items.length}` }]} data-testid="issue-status-filter" />
        <Select size="small" value={filter.route} style={{ minWidth: 112 }} onChange={route => onFilterChange({ ...filter, route })} aria-label="处理路径"
          options={[{ value: 'all', label: '全部处理路径' }, ...options.routes]} data-testid="issue-route-filter" />
        <Select size="small" value={filter.rule} style={{ minWidth: 96 }} onChange={rule => onFilterChange({ ...filter, rule })} aria-label="规则"
          options={[{ value: 'all', label: '全部规则' }, ...options.rules]} data-testid="issue-rule-filter" />
        <Button size="small" type="text" icon={<ReloadOutlined />} onClick={onReload} aria-label="刷新问题" />
      </div>
      {filter.paragraphKey && <Tag closable color="blue" onClose={() => onFilterChange({ ...filter, paragraphKey: null })} data-testid="issue-paragraph-filter">只看所选段落</Tag>}
      {data?.check?.stale && <Alert className="page-notice" type="warning" showIcon message="检查结果已过期：正文或来源已变化，重新检查后再以此为准" data-testid="issue-check-stale" />}
      {error && <Alert className="page-notice" type="error" showIcon message={error} />}
      <Spin spinning={loading}>
        {shown.length ? (
          <ul className="issue-list" data-testid="issue-list">
            {shown.map(item => (
              <li key={item.id} className={`issue-item ${item.id === activeId || (!!highlightKey && item.paragraph_key === highlightKey) ? 'active' : ''} ${item.open ? '' : 'closed'}`} data-testid="issue-item"
                data-paragraph-key={item.paragraph_key ?? undefined} data-issue-origin={item.origin}>
                <div className="issue-item-head">
                  <Tag color={severityColor(item.severity)}>{item.rule_id || item.code}</Tag>
                  {item.origin !== 'check' && <Tag data-testid="issue-origin">{item.origin_label}</Tag>}
                  {!item.open && <Tag color="green">{item.status_label}</Tag>}
                  <span className="muted">{item.route_label}</span>
                </div>
                <div className="issue-message">{item.message}</div>
                {item.quote && <div className="issue-quote muted">{item.quote}</div>}
                {item.suggestion && item.open && <div className="issue-quote muted">建议：{item.suggestion}</div>}
                <Space size={4}>
                  {item.paragraph_key
                    ? <Button size="small" type="link" onClick={() => onLocate(item)} data-testid="issue-locate">定位</Button>
                    : <span className="muted" data-testid="issue-unlocated">{item.locate_note}</span>}
                  {item.stale && <span className="muted">检查已过期</span>}
                </Space>
              </li>
            ))}
          </ul>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={!data?.check && !data?.loop && !items.length ? '本章还没有检查或章节循环记录' : '没有符合条件的问题'} />
        )}
      </Spin>
    </div>
  );
}
