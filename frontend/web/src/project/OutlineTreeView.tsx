// 为什么有这个文件：封装大纲树与章节协同编辑核心组件 OutlineTreeView。
// 它解决什么问题：
// 1. 按生成顺序展示目录；章节类型徽标（专项/通用/系统生成等）仍在无目录时的章节行上；
// 2. 章节顺序同级上移/下移调整与大纲树结构重排；
// 3. 严格落实合规红线门禁：星号条款(★)或废标条款对应章节绝对禁止标记为“不适用”（选项置灰禁用与 Tooltip 提示）；
// 4. 协同 useDataPermission，非主管分册处于分册级只读模式，拦截任何写操作与排序；
// 5. 增值理由弹窗编辑与编辑台章节选择跳转联动。

import React, { useMemo, useState, type CSSProperties } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  EditOutlined,
  FileDoneOutlined,
  LockOutlined,
  StarFilled,
  WarningFilled,
} from '@ant-design/icons';
import type { TechnicalHeading, Volume } from '../shared/types.ts';
import {
  canMarkNotApplicable,
  normalizeChapterNumbers,
  reorderNodes,
  validateChapterTypeChange,
  type ChapterOutlineNode,
  type ChapterType,
} from './outline-tree.ts';
import { ChapterTypeBadge } from './ChapterTypeBadge.tsx';
import { ValueAddedReasonModal } from './ValueAddedReasonModal.tsx';
import { useDataPermission } from '../shell/useDataPermission.ts';

const { Text } = Typography;

export type GeneratedDirectory = {
  title: string;
  chapterId: string;
  headings: TechnicalHeading[];
  missing?: string[];
  reviewTitles?: string[];
  chapterContent?: string;
  confirmed: boolean;
  canPrepare: boolean;
  canGenerate: boolean;
  busy?: boolean;
  onSave: (payload: {
    title: string;
    headings: Array<{
      level: number;
      title: string;
      requirement_id: string | null;
      task_id?: string | null;
      requirement_ids?: string[];
    }>;
    confirm: boolean;
  }) => Promise<void>;
  onGenerate: (section?: string) => Promise<void>;
  onOpen: () => void;
  onExport?: () => void;
  onCoverage?: () => void;
};

const LEVEL_OPTIONS = [
  { value: 1, label: '一级' },
  { value: 2, label: '二级' },
  { value: 3, label: '三级' },
  { value: 4, label: '四级' },
];

function withNumbers(items: TechnicalHeading[]): TechnicalHeading[] {
  const counters = [0, 0, 0, 0];
  return items.map(item => {
    const level = [1, 2, 3, 4].includes(item.level) ? item.level : 2;
    for (let ancestor = 0; ancestor < level - 1; ancestor += 1) {
      if (counters[ancestor] === 0) counters[ancestor] = 1;
    }
    counters[level - 1] += 1;
    for (let deeper = level; deeper < 4; deeper += 1) counters[deeper] = 0;
    const number = counters.slice(0, level).join('.');
    return { ...item, level, number };
  });
}

function DirectoryList({ directory }: { directory: GeneratedDirectory }) {
  const [titleDraft, setTitleDraft] = useState('');
  const [draft, setDraft] = useState<TechnicalHeading[] | null>(null);
  const [query, setQuery] = useState('');
  const headings = draft ?? directory.headings;
  const title = titleDraft || directory.title;
  const locked = directory.confirmed || !directory.canPrepare || !!directory.busy;
  const numbered = withNumbers(headings);
  const visible = numbered
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => !query.trim() || item.title.includes(query.trim()) || item.number.includes(query.trim()));

  function edit(next: TechnicalHeading[]) {
    setDraft(next);
    if (!titleDraft) setTitleDraft(directory.title);
  }

  async function save(confirm: boolean) {
    try {
      await directory.onSave({
        title: title.trim() || directory.title,
        headings: headings.map(item => ({
          level: [1, 2, 3, 4].includes(item.level) ? item.level : 2,
          title: item.title.trim(),
          requirement_id: item.requirement_id ?? null,
          task_id: item.task_id ?? null,
          requirement_ids: item.requirement_ids ?? (item.requirement_id ? [item.requirement_id] : []),
        })),
        confirm,
      });
      setDraft(null);
      setTitleDraft('');
    } catch {
      /* 拒绝时保留正在改的目录 */
    }
  }

  return (
    <div data-testid="generated-directory">
      <Space wrap style={{ marginBottom: 8 }}>
        <Button data-testid="save-technical-outline" disabled={locked} onClick={() => void save(false)}>保存目录</Button>
        <Button
          type={directory.confirmed ? 'default' : 'primary'}
          data-testid="confirm-technical-outline"
          disabled={locked && !directory.confirmed}
          onClick={() => void save(true)}
        >
          {directory.confirmed ? '目录已确认' : '确认目录'}
        </Button>
        {directory.confirmed && (
          <Button type="primary" data-testid="generate-technical-volume"
            disabled={!!directory.busy || !directory.canGenerate}
            onClick={() => void directory.onGenerate().catch(() => undefined)}>
            {directory.busy ? '生成中…' : '开始生成'}
          </Button>
        )}
        {directory.onExport && <Button data-testid="directory-export" onClick={directory.onExport}>导出</Button>}
        {directory.onCoverage && <Button type="link" data-testid="directory-coverage" onClick={directory.onCoverage}>覆盖视图</Button>}
        <Button type="link" onClick={directory.onOpen}>打开正文</Button>
      </Space>
      <Input
        allowClear
        aria-label="搜索目录"
        data-testid="directory-search"
        placeholder="搜索目录"
        value={query}
        onChange={event => setQuery(event.target.value)}
        style={{ marginBottom: 8 }}
      />
      <Input aria-label="章名" value={title} disabled={directory.confirmed} style={{ marginBottom: 8 }}
        onChange={event => { setTitleDraft(event.target.value); if (!draft) setDraft(directory.headings.map(item => ({ ...item }))); }} />
      {visible.map(({ item, index }) => {
        const status = sectionStatusLabel(directory, item);
        return (
        <div key={`${item.requirement_id || 'h'}-${index}`} data-testid="directory-heading" data-level={item.level}
          style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 4, paddingLeft: Math.max(0, (item.level - 1) * 12) }}>
          <span style={{ width: 64 }} data-testid="chapter-number">{item.number}</span>
          <Input aria-label="目录标题" value={item.title} disabled={directory.confirmed}
            onChange={event => edit(headings.map((row, rowIndex) => rowIndex === index ? { ...row, title: event.target.value } : row))} />
          <Select aria-label="标题级别" value={[1, 2, 3, 4].includes(item.level) ? item.level : 2} disabled={directory.confirmed} style={{ width: 88 }}
            options={LEVEL_OPTIONS}
            onChange={level => edit(headings.map((row, rowIndex) => rowIndex === index ? { ...row, level } : row))} />
          <Button type="text" aria-label="上移" disabled={directory.confirmed || index === 0}
            onClick={() => edit(headings.map((row, rowIndex) => rowIndex === index - 1 ? headings[index] : rowIndex === index ? headings[index - 1] : row))}>上移</Button>
          <Button type="text" aria-label="下移" disabled={directory.confirmed || index === headings.length - 1}
            onClick={() => edit(headings.map((row, rowIndex) => rowIndex === index ? headings[index + 1] : rowIndex === index + 1 ? headings[index] : row))}>下移</Button>
          <Button type="text" aria-label="去掉" disabled={directory.confirmed || headings.length === 1}
            onClick={() => edit(headings.filter((_, rowIndex) => rowIndex !== index))}>去掉</Button>
          {directory.confirmed && !!item.requirement_id && (
            <Button type="link" size="small" data-testid={`regenerate-${item.title}`}
              disabled={!!directory.busy || !directory.canGenerate}
              onClick={() => void directory.onGenerate(item.title).catch(() => undefined)}>重新生成</Button>
          )}
          {status && (
            <Tag color={status === '已生成' ? 'success' : status === '生成中' ? 'processing' : status === '未生成' ? 'default' : 'warning'} data-testid={`status-${item.title}`}>{status}</Tag>
          )}
        </div>
      );})}
      {(directory.missing ?? []).length > 0 && (
        <Alert type="warning" showIcon style={{ marginTop: 8 }} message="还有条款没有放进目录。" />
      )}
    </div>
  );
}

function sectionStatusLabel(directory: GeneratedDirectory, item: TechnicalHeading) {
  if (!item.requirement_id) return null;
  if (directory.busy) return '生成中';
  if ((directory.reviewTitles ?? []).includes(item.title)) return '需核对';
  const content = directory.chapterContent || '';
  const marker = `${item.number} ${item.title}`;
  const lines = content.split(/\r?\n/);
  const start = lines.findIndex(line => line.trim() === marker);
  if (start < 0) return content.trim() ? '未生成' : '未生成';
  const end = lines.findIndex((line, index) => index > start && /^\d+(?:\.\d+)*\s+\S/.test(line.trim()));
  const body = lines.slice(start + 1, end < 0 ? undefined : end).join('\n').trim();
  if (!body) return '未生成';
  if (body === '待补' || body.includes('待补')) return '待补';
  if (body.includes('需要核对')) return '需核对';
  return '已生成';
}

export interface OutlineTreeViewProps {
  nodes: ChapterOutlineNode[];
  activeVolume?: Volume | 'all';
  directory?: GeneratedDirectory | null;
  onNodesChange?: (nodes: ChapterOutlineNode[]) => void;
  onSelectChapter?: (chapter: ChapterOutlineNode) => void;
  onNavigateToEditor?: (chapterId: string) => void;
  selectedChapterId?: string | null;
  className?: string;
  style?: CSSProperties;
}

export function OutlineTreeView({
  nodes,
  activeVolume = 'technical',
  directory = null,
  onNodesChange,
  onSelectChapter,
  onNavigateToEditor,
  selectedChapterId,
  className = '',
  style,
}: OutlineTreeViewProps) {
  const [editingReasonChapter, setEditingReasonChapter] = useState<ChapterOutlineNode | null>(null);

  // 1. 接入数据权限判定：分册级与角色级只读管控
  const permission = useDataPermission({
    volume: activeVolume === 'all' ? undefined : (activeVolume as Volume),
  });
  const canEdit = permission.canEdit;

  // 2. 按传入顺序展示全部章节，不再按分册切开。已有生成目录时，目录章改由目录行承担。
  const orderedNodes = useMemo(() => normalizeChapterNumbers(nodes), [nodes]);
  const directoryShown = Boolean(directory && directory.headings.length > 0);
  const chapterNodes = directoryShown && directory
    ? orderedNodes.filter(node => node.id !== directory.chapterId)
    : orderedNodes;

  // 3. 排序操作处理器
  const handleReorder = (chapterId: string, direction: 'up' | 'down') => {
    if (!canEdit) return;
    const reordered = reorderNodes(orderedNodes, chapterId, direction);
    if (onNodesChange) onNodesChange(normalizeChapterNumbers(reordered));
  };

  // 4. 修改章节类型处理器
  const handleTypeChange = (node: ChapterOutlineNode, targetType: ChapterType) => {
    if (!canEdit) return;
    const check = validateChapterTypeChange(node, targetType);
    if (!check.valid) {
      return;
    }
    const updated = nodes.map(item => {
      if (item.id === node.id) {
        return { ...item, chapterType: targetType };
      }
      return item;
    });
    if (onNodesChange) {
      onNodesChange(updated);
    }
  };

  // 5. 保存增值理由
  const handleSaveReason = (chapterId: string, reason: string) => {
    const updated = nodes.map(item => {
      if (item.id === chapterId) {
        return { ...item, valueAddedReason: reason };
      }
      return item;
    });
    if (onNodesChange) {
      onNodesChange(updated);
    }
    setEditingReasonChapter(null);
  };

  return (
    <div
      className={`icg-outline-tree-view ${className}`}
      style={style}
      data-testid="outline-tree-view"
      data-volume={activeVolume}
      data-can-edit={canEdit ? 'true' : 'false'}
    >
      {!directoryShown && (
        <div className="icg-outline-toolbar" style={{ marginBottom: 16 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>共 {orderedNodes.length} 个章节</Text>
        </div>
      )}

      {/* 只读警告条（非主管分册或系统只读） */}
      {!canEdit && (
        <Alert
          type="warning"
          showIcon
          icon={<LockOutlined />}
          message="分册只读模式"
          description={permission.readOnlyReason || '当前处于非主管分册只读模式，仅供查阅，不可修改大纲顺序、章节类型或增值理由。'}
          style={{ marginBottom: 14 }}
          data-testid="readonly-notice-banner"
        />
      )}

      {directoryShown && directory && <DirectoryList directory={directory} />}
      {chapterNodes.length === 0 && !directoryShown ? (
        <Card>
          <Empty description="暂无章节" />
        </Card>
      ) : chapterNodes.length > 0 ? (
        <div className="icg-outline-nodes-list" style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: directoryShown ? 12 : 0 }}>
          {chapterNodes.map((node, index) => {
            const isFirst = index === 0;
            const isLast = index === chapterNodes.length - 1;
            const isSelected = selectedChapterId === node.id;
            const notApplicableCheck = canMarkNotApplicable(node);
            const isNotApplicableDisabled = !notApplicableCheck.allowed;

            return (
              <div
                key={node.id}
                className={`icg-outline-node-card ${isSelected ? 'is-selected' : ''}`}
                style={{
                  background: isSelected ? '#f0f5ff' : '#ffffff',
                  border: isSelected ? '1px solid #1e4db7' : '1px solid #e8ebf0',
                  borderRadius: 6,
                  padding: '12px 16px',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                }}
                data-testid="outline-node-item"
                data-chapter-id={node.id}
                data-chapter-type={node.chapterType}
                data-is-starred={node.isStarred ? 'true' : 'false'}
                data-is-blocker={node.isBlocker ? 'true' : 'false'}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                  {/* 左侧：章节序号、标题、类型与关键标签 */}
                  <div
                    style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', flex: 1, minWidth: 260 }}
                    onClick={() => onSelectChapter && onSelectChapter(node)}
                  >
                    <span
                      className="icg-node-number"
                      style={{
                        fontFamily: 'SFMono-Regular, Consolas, monospace',
                        fontWeight: 600,
                        color: '#1e4db7',
                        minWidth: 32,
                      }}
                      data-testid="chapter-number"
                    >
                      {node.chapterNumber || `${node.orderIndex}`}
                    </span>
                    <Text strong style={{ fontSize: 14, color: '#1d2129' }}>
                      {node.title}
                    </Text>

                    {/* 章节类型徽标 */}
                    <ChapterTypeBadge type={node.chapterType} />

                    {/* 星号条款标 (★) */}
                    {node.isStarred && (
                      <Tag color="error" icon={<StarFilled />} style={{ fontSize: 11 }} data-testid="starred-tag">
                        ★ 星号条款
                      </Tag>
                    )}

                    {/* 废标条款标 */}
                    {node.isBlocker && (
                      <Tag color="volcano" icon={<WarningFilled />} style={{ fontSize: 11 }} data-testid="blocker-tag">
                        废标条款
                      </Tag>
                    )}

                    {/* 关联条款数 */}
                    {node.clauseCount !== undefined && node.clauseCount > 0 && (
                      <Tag color="default" style={{ fontSize: 11 }}>
                        {node.clauseCount} 条款
                      </Tag>
                    )}

                    {/* 负责人 */}
                    {node.assigneeName && (
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        负责人: {node.assigneeName}
                      </Text>
                    )}
                  </div>

                  {/* 右侧：章节类型切换、排序、增值理由与编辑台跳转 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {/* 章节类型下拉选择（含核心门禁拦截：星号/废标条款禁止标“不适用”） */}
                    <Select
                      size="small"
                      value={node.chapterType}
                      disabled={!canEdit}
                      style={{ width: 112 }}
                      onChange={val => handleTypeChange(node, val)}
                      data-testid="chapter-type-select"
                      options={[
                        { label: '专项方案', value: 'specialized' },
                        { label: '通用方案', value: 'general' },
                        { label: '系统生成', value: 'system_generated' },
                        { label: '封面目录', value: 'cover_and_catalog' },
                        {
                          label: isNotApplicableDisabled ? (
                            <Tooltip title={notApplicableCheck.reason} placement="left">
                              <span style={{ color: '#bfbfbf' }}>不适用 (禁止)</span>
                            </Tooltip>
                          ) : (
                            '不适用'
                          ),
                          value: 'not_applicable',
                          disabled: isNotApplicableDisabled,
                        },
                      ]}
                    />

                    {/* 排序按钮：上移 / 下移 */}
                    <Space size={4}>
                      <Tooltip title={canEdit ? (isFirst ? '已在最顶端' : '同级上移') : '无编辑权限'}>
                        <Button
                          size="small"
                          icon={<ArrowUpOutlined />}
                          disabled={!canEdit || isFirst}
                          onClick={() => handleReorder(node.id, 'up')}
                          data-testid="reorder-up-btn"
                        />
                      </Tooltip>
                      <Tooltip title={canEdit ? (isLast ? '已在最底端' : '同级下移') : '无编辑权限'}>
                        <Button
                          size="small"
                          icon={<ArrowDownOutlined />}
                          disabled={!canEdit || isLast}
                          onClick={() => handleReorder(node.id, 'down')}
                          data-testid="reorder-down-btn"
                        />
                      </Tooltip>
                    </Space>

                    {/* 增值理由编辑按钮 */}
                    <Tooltip title={node.valueAddedReason ? '查看/修改增值理由' : '添加增值理由'}>
                      <Button
                        size="small"
                        type={node.valueAddedReason ? 'dashed' : 'default'}
                        icon={<FileDoneOutlined style={{ color: node.valueAddedReason ? '#52c41a' : undefined }} />}
                        onClick={() => setEditingReasonChapter(node)}
                        data-testid="edit-reason-btn"
                      >
                        {node.valueAddedReason ? '增值理由' : '添加理由'}
                      </Button>
                    </Tooltip>

                    {/* 编辑台跳转按钮 */}
                    {onNavigateToEditor && (
                      <Tooltip title="进入编辑台协同撰写">
                        <Button
                          size="small"
                          type="primary"
                          ghost
                          icon={<EditOutlined />}
                          onClick={() => onNavigateToEditor(node.id)}
                          data-testid="navigate-editor-btn"
                        >
                          编辑台
                        </Button>
                      </Tooltip>
                    )}
                  </div>
                </div>

                {/* 展开展示已填写的增值理由概要 */}
                {node.valueAddedReason && (
                  <div
                    className="icg-node-value-added-preview"
                    style={{
                      marginTop: 8,
                      padding: '6px 10px',
                      background: '#f9f0ff',
                      borderLeft: '3px solid #722ed1',
                      borderRadius: 2,
                      fontSize: 12,
                      color: '#4e5969',
                      lineHeight: 1.6,
                    }}
                    data-testid="value-added-preview"
                  >
                    <span style={{ fontWeight: 600, color: '#722ed1', marginRight: 6 }}>增值理由:</span>
                    {node.valueAddedReason}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : null}

      {/* 增值理由弹窗 */}
      <ValueAddedReasonModal
        open={Boolean(editingReasonChapter)}
        chapter={editingReasonChapter}
        readOnly={!canEdit}
        readOnlyReason={permission.readOnlyReason}
        onSave={handleSaveReason}
        onCancel={() => setEditingReasonChapter(null)}
      />
    </div>
  );
}
