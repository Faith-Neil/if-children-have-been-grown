// 为什么有这个文件：封装大纲树与章节协同编辑核心组件 OutlineTreeView。
// 它解决什么问题：
// 1. 按生成顺序展示目录；章节类型徽标（专项/通用/系统生成等）仍在无目录时的章节行上；
// 2. 目录用拖放调整顺序和 1～4 级，双击改名称；
// 3. 严格落实合规红线门禁：星号条款(★)或废标条款对应章节绝对禁止标记为“不适用”（选项置灰禁用与 Tooltip 提示）；
// 4. 协同 useDataPermission，非主管分册处于分册级只读模式，拦截任何写操作与排序；
// 5. 增值理由弹窗编辑与编辑台章节选择跳转联动。

import React, { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  CaretDownOutlined,
  CaretRightOutlined,
  DownOutlined,
  EditOutlined,
  FileDoneOutlined,
  LockOutlined,
  MinusOutlined,
  PlusOutlined,
  StarFilled,
  UpOutlined,
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
import { blockEnd, moveOutline } from './directory-order.ts';

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

function outlineText(number: string, title: string) {
  return number.includes('.') ? `${number} ${title}` : `${number}. ${title}`;
}

function titleFromOutline(value: string, number: string) {
  const text = value.trim();
  const dotted = number.includes('.') ? `${number} ` : `${number}.`;
  if (text.startsWith(dotted)) return text.slice(dotted.length).trim();
  if (text.startsWith(`${number} `) || text.startsWith(`${number}.`)) return text.slice(number.length).replace(/^[\s.]+/, '');
  return text;
}

function headingHidden(items: TechnicalHeading[], index: number, folded: Set<number>) {
  let depth = items[index].level;
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    if (items[cursor].level < depth) {
      if (folded.has(cursor)) return true;
      depth = items[cursor].level;
    }
  }
  return false;
}

function DirectoryList({ directory }: { directory: GeneratedDirectory }) {
  const [draft, setDraft] = useState<TechnicalHeading[] | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [selected, setSelected] = useState(0);
  const [folded, setFolded] = useState<Set<number>>(new Set());
  const [dropAt, setDropAt] = useState<number | null>(null);
  const dragFrom = useRef<{ index: number; x: number; level: number } | null>(null);
  const savedKey = useRef('');
  const headings = draft ?? directory.headings;
  const blocked = !directory.canPrepare || !!directory.busy;
  const numbered = withNumbers(headings);
  const current = numbered[Math.min(selected, Math.max(0, numbered.length - 1))];

  useEffect(() => {
    const key = directory.headings.map(item => `${item.level}\t${item.title}`).join('\n');
    if (savedKey.current && key === savedKey.current) {
      savedKey.current = '';
      setDraft(null);
    }
  }, [directory.headings]);

  function payload(next: TechnicalHeading[]) {
    return next.map(item => ({
      level: [1, 2, 3, 4].includes(item.level) ? item.level : 2,
      title: item.title.trim(),
      requirement_id: item.requirement_id ?? null,
      task_id: item.task_id ?? null,
      requirement_ids: item.requirement_ids ?? (item.requirement_id ? [item.requirement_id] : []),
    }));
  }

  async function persist(next: TechnicalHeading[]) {
    const stamp = (items: TechnicalHeading[]) => items.map(item => `${item.level}\t${item.title}`).join('\n');
    if (stamp(next) === stamp(headings)) return;
    setDraft(next);
    const key = next.map(item => `${item.level}\t${item.title.trim()}`).join('\n');
    savedKey.current = key;
    try {
      await directory.onSave({ title: directory.title, headings: payload(next), confirm: directory.confirmed });
    } catch {
      savedKey.current = '';
    }
  }

  function onDragStart(index: number, event: React.DragEvent) {
    dragFrom.current = { index, x: event.clientX, level: headings[index].level };
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', String(index));
  }

  function onDragOver(index: number, event: React.DragEvent) {
    if (!dragFrom.current) return;
    event.preventDefault();
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    setDropAt(event.clientY > rect.top + rect.height / 2 ? index + 1 : index);
  }

  function onDrop(event: React.DragEvent) {
    event.preventDefault();
    const origin = dragFrom.current;
    dragFrom.current = null;
    const target = dropAt;
    setDropAt(null);
    if (!origin || target === null || blocked) return;
    const shift = Math.round((event.clientX - origin.x) / 24);
    const next = moveOutline(headings, origin.index, target, origin.level + shift);
    const movedTo = target > origin.index ? target - (blockEnd(headings, origin.index) - origin.index) : target;
    setSelected(Math.max(0, Math.min(next.length - 1, movedTo)));
    void persist(next);
  }

  function finishEdit(index: number, value: string) {
    setEditing(null);
    const title = titleFromOutline(value, numbered[index]?.number ?? '');
    if (!title || title === headings[index]?.title) return;
    void persist(headings.map((row, rowIndex) => rowIndex === index ? { ...row, title } : row));
  }

  function changeLevel(delta: number) {
    if (!current || blocked) return;
    const index = numbered.indexOf(current);
    void persist(moveOutline(headings, index, index, current.level + delta));
  }

  function addHeading() {
    if (!current || blocked) return;
    const index = numbered.indexOf(current);
    const at = blockEnd(headings, index);
    const next = headings.map(item => ({ ...item }));
    next.splice(at, 0, { level: current.level, number: '', title: '未命名', requirement_id: null, task_id: null, requirement_ids: [] });
    setSelected(at);
    setEditing(at);
    void persist(next);
  }

  function removeHeading() {
    if (!current || blocked || headings.length <= 1) return;
    const index = numbered.indexOf(current);
    const next = headings.filter((_, rowIndex) => rowIndex !== index);
    setSelected(Math.max(0, index - 1));
    void persist(next);
  }

  return (
    <div className="wps-outline" data-testid="generated-directory" onDragEnd={() => { dragFrom.current = null; setDropAt(null); }}>
      <div className="wps-outline-tools">
        <button type="button" aria-label="降级" disabled={blocked || !current} onClick={() => changeLevel(1)}><DownOutlined /></button>
        <button type="button" aria-label="升级" disabled={blocked || !current} onClick={() => changeLevel(-1)}><UpOutlined /></button>
        <button type="button" aria-label="增加" disabled={blocked || !current} onClick={addHeading}><PlusOutlined /></button>
        <button type="button" aria-label="删除" disabled={blocked || !current || headings.length <= 1} onClick={removeHeading}><MinusOutlined /></button>
      </div>
      {numbered.map((item, index) => {
        if (headingHidden(numbered, index, folded)) return null;
        const shownLevel = [1, 2, 3, 4].includes(item.level) ? item.level : 2;
        const children = index + 1 < numbered.length && numbered[index + 1].level > item.level;
        const label = outlineText(item.number, item.title);
        return (
          <div
            key={`${item.requirement_id || 'h'}-${index}`}
            className={`wps-outline-row${selected === index ? ' is-selected' : ''}${dropAt === index ? ' is-over-before' : ''}${dropAt === numbered.length && index === numbered.length - 1 ? ' is-over-after' : ''}`}
            data-testid="directory-heading"
            data-level={shownLevel}
            draggable={!blocked && editing !== index}
            style={{ paddingLeft: (shownLevel - 1) * 16 }}
            onClick={() => setSelected(index)}
            onDragStart={event => onDragStart(index, event)}
            onDragOver={event => onDragOver(index, event)}
            onDrop={onDrop}
          >
            <button
              type="button"
              className="wps-outline-twist"
              aria-label={children ? (folded.has(index) ? '展开' : '折叠') : undefined}
              aria-hidden={children ? undefined : true}
              tabIndex={children ? 0 : -1}
              onClick={event => {
                event.stopPropagation();
                if (!children) return;
                setFolded(currentFolded => {
                  const next = new Set(currentFolded);
                  if (next.has(index)) next.delete(index);
                  else next.add(index);
                  return next;
                });
              }}
            >
              {children ? (folded.has(index) ? <CaretRightOutlined /> : <CaretDownOutlined />) : null}
            </button>
            {editing === index ? (
              <input
                autoFocus
                className="wps-outline-editor"
                aria-label="目录标题"
                defaultValue={label}
                onClick={event => event.stopPropagation()}
                onBlur={event => finishEdit(index, event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter') event.currentTarget.blur();
                  if (event.key === 'Escape') setEditing(null);
                }}
              />
            ) : (
              <span className="wps-outline-label" data-testid="chapter-number" onDoubleClick={event => { event.stopPropagation(); if (!blocked) setEditing(index); }}>{label}</span>
            )}
          </div>
        );
      })}
    </div>
  );
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
      {!canEdit && !directoryShown && (
        <Alert
          type="warning"
          showIcon
          icon={<LockOutlined />}
          message="方案只读模式"
          description={permission.readOnlyReason || '当前处于非主管方案只读模式，仅供查阅，不可修改大纲顺序、章节类型或增值理由。'}
          style={{ marginBottom: 14 }}
          data-testid="readonly-notice-banner"
        />
      )}

      {directoryShown && directory && <DirectoryList directory={directory} />}
      {chapterNodes.length === 0 && !directoryShown ? (
        <Card>
          <Empty description="暂无章节" />
        </Card>
      ) : chapterNodes.length > 0 && !directoryShown ? (
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
