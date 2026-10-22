// 为什么有这个文件：封装大纲树与章节协同编辑核心组件 OutlineTreeView。
// 它解决什么问题：
// 1. 分册（技术/商务）章节树层级与编号展示、章节类型徽标（专项/通用/系统生成等）展示；
// 2. 章节顺序同级上移/下移调整与大纲树结构重排；
// 3. 严格落实合规红线门禁：星号条款(★)或废标条款对应章节绝对禁止标记为“不适用”（选项置灰禁用与 Tooltip 提示）；
// 4. 协同 useDataPermission，非主管分册处于分册级只读模式，拦截任何写操作与排序；
// 5. 增值理由弹窗编辑与编辑台章节选择跳转联动。

import React, { useMemo, useState, type CSSProperties } from 'react';
import {
  Alert,
  Button,
  Card,
  Dropdown,
  Empty,
  MenuProps,
  Radio,
  Select,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  CheckCircleOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  FileDoneOutlined,
  InfoCircleOutlined,
  LockOutlined,
  StarFilled,
  WarningFilled,
} from '@ant-design/icons';
import type { Volume } from '../shared/types.ts';
import {
  canMarkNotApplicable,
  CHAPTER_TYPES_CONFIG,
  normalizeChapterNumbers,
  reorderNodes,
  validateChapterTypeChange,
  type ChapterOutlineNode,
  type ChapterType,
} from './outline-tree.ts';
import { ChapterTypeBadge } from './ChapterTypeBadge.tsx';
import { ValueAddedReasonModal } from './ValueAddedReasonModal.tsx';
import { useDataPermission } from '../shell/useDataPermission.ts';

const { Text, Paragraph } = Typography;

export interface OutlineTreeViewProps {
  nodes: ChapterOutlineNode[];
  activeVolume?: Volume | 'all';
  onVolumeChange?: (volume: Volume | 'all') => void;
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
  onVolumeChange,
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

  // 2. 过滤当前选定分册的章节
  const filteredNodes = useMemo(() => {
    let result = nodes;
    if (activeVolume && activeVolume !== 'all') {
      result = nodes.filter(n => n.volume === activeVolume);
    }
    return normalizeChapterNumbers(result);
  }, [nodes, activeVolume]);

  // 3. 排序操作处理器
  const handleReorder = (chapterId: string, direction: 'up' | 'down') => {
    if (!canEdit) return;
    const reordered = reorderNodes(filteredNodes, chapterId, direction);
    const normalized = normalizeChapterNumbers(reordered);
    if (onNodesChange) {
      // 合并非当前分册的节点保持不变
      const otherNodes = nodes.filter(n => activeVolume !== 'all' && n.volume !== activeVolume);
      onNodesChange([...otherNodes, ...normalized]);
    }
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
      {/* 顶栏控制：分册切换与操作指引 */}
      <div className="icg-outline-toolbar" style={{ marginBottom: 16 }}>
        <Space style={{ justifyContent: 'space-between', width: '100%', flexWrap: 'wrap' }}>
          <Space>
            <span style={{ fontSize: 13, fontWeight: 500, color: '#4e5969' }}>分册视图：</span>
            <Radio.Group
              value={activeVolume}
              onChange={e => onVolumeChange && onVolumeChange(e.target.value)}
              buttonStyle="solid"
              size="small"
              data-testid="volume-switch-group"
            >
              <Radio.Button value="technical" data-testid="volume-technical-btn">技术分册</Radio.Button>
              <Radio.Button value="business" data-testid="volume-business-btn">商务分册</Radio.Button>
              <Radio.Button value="all" data-testid="volume-all-btn">全部分册</Radio.Button>
            </Radio.Group>
          </Space>

          <Space size={12}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              共 {filteredNodes.length} 个章节
            </Text>
          </Space>
        </Space>
      </div>

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

      {/* 大纲节点列表 */}
      {filteredNodes.length === 0 ? (
        <Card>
          <Empty description="当前分册下暂无章节大纲数据" />
        </Card>
      ) : (
        <div className="icg-outline-nodes-list" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {filteredNodes.map((node, index) => {
            const isFirst = index === 0;
            const isLast = index === filteredNodes.length - 1;
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
      )}

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
