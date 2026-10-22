// 为什么有这个文件：封装统一的元数据驱动表格组件（MetadataTable）。
// 它解决什么问题：从字段元数据自动推导 Ant Design Table 的列配置与渲染器，
// 实现行/列合并、1280px 视口无横向滚动优先分配、深度集成状态组件（StatusViews）与业务小组件（BusinessTags），
// 并落地合规批量操作限制（星号/废标/资格禁止批量确认）与风险行高亮。

import React, { useMemo, useState, type CSSProperties, type ReactNode } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Drawer,
  Dropdown,
  Empty,
  Input,
  Popconfirm,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  type TablePaginationConfig,
  type TableProps,
} from 'antd';
import {
  CloseOutlined,
  ColumnHeightOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  MoreOutlined,
  ReloadOutlined,
  SearchOutlined,
  WarningOutlined,
} from '@ant-design/icons';

import {
  calculateColumnWidthBudget,
  calculateRowSpans,
  canBatchConfirm,
  formatDateTimeMonospace,
  isRiskRow,
  isUrgentRow,
  resolveTableMeta,
  STANDARD_TABLE_AVAILABLE_WIDTH,
  type ColumnBudgetResult,
  type FieldDataType,
  type FieldMeta,
  type TableMeta,
} from './metadata-table';

import { ErrorView, SkeletonView, EmptyState } from './StatusViews';
import { LevelTag, AiTag, DirectTag, Cite, SourceBar } from './BusinessTags';

const { Text, Paragraph } = Typography;

/* ========================================================================= */
/* 1. 组件属性定义                                                           */
/* ========================================================================= */

export interface MetadataTableProps<T = any> {
  /** 表格元数据模式（Schema 对象或预设 SchemaId 字符串） */
  schema: TableMeta<T> | string;
  /** 数据源 */
  dataSource: T[];
  /** 唯一行键（默认 "id"） */
  rowKey?: string | ((record: T) => string);
  /** 加载中状态 */
  loading?: boolean;
  /** 错误信息对象（如有则降级渲染 ErrorView 并提供 traceId 复制） */
  error?: any;
  /** 错误重试回调 */
  onRetry?: () => void;
  /** 刷新回调 */
  onRefresh?: () => void;
  /** 表格尺寸：默认取 schema.defaultSize 或 middle；矩阵/合规/资料列表推荐 small */
  size?: 'small' | 'middle' | 'large';
  /** 可用宽度（px），默认 1040（1280px 标准视口下的安全表格宽度） */
  availableWidth?: number;
  /** 是否强制启用横向滚动条（覆盖无横滚优先策略） */
  forceScrollX?: boolean;
  /** 选中的行键集合 */
  selectedRowKeys?: React.Key[];
  /** 行选中改变回调 */
  onSelectChange?: (selectedRowKeys: React.Key[], selectedRows: T[]) => void;
  /** 自定义批量操作栏渲染函数 */
  batchActions?: (selectedRows: T[], canConfirm: boolean) => ReactNode;
  /** 批量确认回调函数 */
  onBatchConfirm?: (selectedRows: T[]) => void | Promise<void>;
  /** 是否显示内置搜索工具栏 */
  searchable?: boolean;
  /** 搜索过滤函数（默认按名称、标题或编号匹配） */
  searchFilter?: (record: T, query: string) => boolean;
  /** 外部受控搜索词 */
  searchValue?: string;
  /** 搜索词变化回调 */
  onSearchChange?: (value: string) => void;
  /** 工具栏额外扩展内容 */
  toolbarExtra?: ReactNode;
  /** 分页配置（默认 pageSize: 10，showTotal: 共 N 条） */
  pagination?: TablePaginationConfig | false;
  /** 行点击回调 */
  onRowClick?: (record: T) => void;
  /** 定位引用证据回调 */
  onLocateEvidence?: (record: T, citeMeta?: any) => void;
  /** 自定义风险行判断 */
  riskRowPredicate?: (record: T) => boolean;
  /** 自定义急迫行判断 */
  urgentRowPredicate?: (record: T) => boolean;
  /** 自定义类名与样式 */
  className?: string;
  style?: CSSProperties;
  /** 抽屉详情查看标题 */
  detailDrawerTitle?: string;
}

/* ========================================================================= */
/* 2. MetadataTable 组件实现                                                 */
/* ========================================================================= */

export function MetadataTable<T extends Record<string, any> = any>({
  schema,
  dataSource,
  rowKey = 'id',
  loading = false,
  error,
  onRetry,
  onRefresh,
  size,
  availableWidth = STANDARD_TABLE_AVAILABLE_WIDTH,
  forceScrollX = false,
  selectedRowKeys,
  onSelectChange,
  batchActions,
  onBatchConfirm,
  searchable = true,
  searchFilter,
  searchValue: controlledSearchValue,
  onSearchChange,
  toolbarExtra,
  pagination = { pageSize: 10 },
  onRowClick,
  onLocateEvidence,
  riskRowPredicate,
  urgentRowPredicate,
  className = '',
  style,
  detailDrawerTitle = '条款与内容详情',
}: MetadataTableProps<T>) {
  // 解析元数据模式
  const tableMeta = useMemo(() => resolveTableMeta(schema), [schema]);

  // 内部搜索状态
  const [internalSearch, setInternalSearch] = useState('');
  const searchKeyword = controlledSearchValue !== undefined ? controlledSearchValue : internalSearch;
  const handleSearch = (val: string) => {
    if (onSearchChange) onSearchChange(val);
    else setInternalSearch(val);
  };

  // 内部尺寸状态（支持工具栏密度切换）
  const [currentSize, setCurrentSize] = useState<'small' | 'middle' | 'large'>(
    size || tableMeta.defaultSize || 'middle'
  );

  // 抽屉详情弹窗状态
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeDetail, setActiveDetail] = useState<{
    field: FieldMeta<T>;
    record: T;
    value: any;
  } | null>(null);

  const openDetailDrawer = (field: FieldMeta<T>, record: T, value: any) => {
    setActiveDetail({ field, record, value });
    setDrawerOpen(true);
  };

  const closeDetailDrawer = () => {
    setDrawerOpen(false);
    setActiveDetail(null);
  };

  // 过滤数据源（根据搜索词）
  const filteredData = useMemo(() => {
    if (!searchKeyword.trim()) return dataSource || [];
    const query = searchKeyword.trim().toLowerCase();
    return (dataSource || []).filter(item => {
      if (searchFilter) return searchFilter(item, query);
      // 默认模糊匹配：检查所有字段
      return Object.values(item).some(val => {
        if (val === null || val === undefined) return false;
        return String(val).toLowerCase().includes(query);
      });
    });
  }, [dataSource, searchKeyword, searchFilter]);

  // 布局与无横滚宽度预算计算
  const budget: ColumnBudgetResult = useMemo(() => {
    return calculateColumnWidthBudget(tableMeta.fields, availableWidth);
  }, [tableMeta.fields, availableWidth]);

  // 计算行合并 rowSpan（根据 groupField 或各字段的 groupMerge）
  const rowSpanMaps = useMemo(() => {
    const maps: Record<string, number[]> = {};
    for (const field of tableMeta.fields) {
      if (field.groupMerge || tableMeta.groupField === field.key) {
        maps[field.key] = calculateRowSpans(filteredData, (item: any) => item[field.key]);
      }
    }
    return maps;
  }, [tableMeta.fields, tableMeta.groupField, filteredData]);

  // 选中的记录数组
  const selectedRecords = useMemo(() => {
    if (!selectedRowKeys || !selectedRowKeys.length) return [];
    const keySet = new Set(selectedRowKeys);
    return (dataSource || []).filter(item => {
      const key = typeof rowKey === 'function' ? rowKey(item) : item[rowKey];
      return keySet.has(key);
    });
  }, [selectedRowKeys, dataSource, rowKey]);

  // 批量操作合规门禁检查
  const batchValidation = useMemo(() => {
    return canBatchConfirm(selectedRecords);
  }, [selectedRecords]);

  /* ----------------------------------------------------------------------- */
  /* 列渲染器推导引擎                                                        */
  /* ----------------------------------------------------------------------- */
  const columns = useMemo(() => {
    const fieldMap = new Map(tableMeta.fields.map(f => [f.key, f]));

    return budget.columns.map(allocatedCol => {
      const field = fieldMap.get(allocatedCol.key)!;
      const isMergeTarget = !!rowSpanMaps[field.key];

      // 表头：支持双行标签（规范 9.2 规则 2：中文名 + 等宽小字系统键）
      const headerTitle = (
        <div className="icg-two-line-header" data-testid={`col-header-${field.key}`}>
          <div className="icg-header-primary">
            {field.starred && <span className="icg-starred-indicator">★ </span>}
            <span>{field.label}</span>
          </div>
          {field.secondaryLabel && (
            <div className="icg-header-secondary">{field.secondaryLabel}</div>
          )}
        </div>
      );

      return {
        key: field.key,
        dataIndex: field.key,
        title: headerTitle,
        width: allocatedCol.allocatedWidth,
        align: field.align || (field.dataType === 'number' ? 'right' : 'left'),
        ellipsis: allocatedCol.ellipsis,
        fixed: forceScrollX ? field.fixed : allocatedCol.fixed,
        onCell: (_record: T, rowIndex?: number) => {
          if (isMergeTarget && rowIndex !== undefined) {
            const span = rowSpanMaps[field.key]?.[rowIndex] ?? 1;
            return { rowSpan: span };
          }
          return {};
        },
        render: (textValue: any, record: T, rowIndex: number) => {
          // 1. 自定义渲染优先
          if (field.render) {
            return field.render(textValue, record, rowIndex);
          }

          // 2. 根据 dataType 分流渲染
          switch (field.dataType) {
            case 'level': {
              const levelVal = textValue || record.level || record.rule_level || record.category;
              return <LevelTag level={levelVal} />;
            }

            case 'ai': {
              const variantVal = textValue || record.ai_variant || 'suggestion';
              return <AiTag variant={variantVal} />;
            }

            case 'direct': {
              const labelVal = textValue || record.direct_label || '系统直出';
              return <DirectTag label={labelVal} />;
            }

            case 'cite': {
              const citeType = record.cite_type || (textValue ? 'evidence' : 'none');
              const citeTitle = record.cite_title || textValue;
              const citeSnippet = record.cite_snippet || record.quote;
              const page = record.page || record.cite_page;
              return (
                <Cite
                  type={citeType}
                  metadata={{
                    title: citeTitle,
                    quote: citeSnippet,
                    page: page,
                  }}
                  onClick={onLocateEvidence ? () => onLocateEvidence(record) : undefined}
                />
              );
            }

            case 'source': {
              const sourceVal = record.source || textValue;
              const fp = record.input_fingerprint || record.fingerprint;
              const stale = record.source_stale || record.stale;
              return (
                <SourceBar
                  kind={sourceVal || 'tender_doc'}
                  fingerprint={fp}
                  status={stale ? 'stale' : 'confirmed'}
                  layout="bottom"
                />
              );
            }

            case 'status': {
              const st = String(textValue || '').toLowerCase();
              let color = 'default';
              let label = textValue || '—';
              if (st === 'confirmed' || st === '已确认' || st === 'passed') {
                color = 'green';
                label = '已确认';
              } else if (st === 'pending' || st === '待确认' || st === 'reviewing') {
                color = 'orange';
                label = '待确认';
              } else if (st === 'rejected' || st === '已排除' || st === 'failed') {
                color = 'red';
                label = '已排除';
              }
              return <Tag color={color}>{label}</Tag>;
            }

            case 'datetime': {
              return (
                <span className="icg-monospace-time">
                  {formatDateTimeMonospace(textValue)}
                </span>
              );
            }

            case 'date': {
              return (
                <span className="icg-monospace-time">
                  {textValue ? String(textValue).split('T')[0] : '—'}
                </span>
              );
            }

            case 'number': {
              if (textValue === null || textValue === undefined || textValue === '') {
                return '—';
              }
              const num = Number(textValue);
              return isNaN(num) ? String(textValue) : num.toLocaleString();
            }

            case 'longtext': {
              if (!textValue) return <span className="muted">—</span>;
              const strVal = String(textValue);
              return (
                <div className="icg-longtext-cell" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className="icg-cell-ellipsis" title={strVal} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                    {strVal}
                  </span>
                  {allocatedCol.viewInDrawer && (
                    <Button
                      type="link"
                      size="small"
                      className="icg-detail-trigger"
                      icon={<EyeOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        openDetailDrawer(field, record, strVal);
                      }}
                      title="在侧栏抽屉中查看完整内容"
                    >
                      查看
                    </Button>
                  )}
                </div>
              );
            }

            case 'actions': {
              // 默认操作列占位
              return (
                <Space size="small">
                  <Button type="link" size="small" onClick={() => onRowClick && onRowClick(record)}>
                    详情
                  </Button>
                </Space>
              );
            }

            default:
              return textValue ?? <span className="muted">—</span>;
          }
        },
      };
    });
  }, [
    tableMeta.fields,
    budget.columns,
    rowSpanMaps,
    forceScrollX,
    onLocateEvidence,
    onRowClick,
  ]);

  /* ----------------------------------------------------------------------- */
  /* 异常与骨架屏分支                                                        */
  /* ----------------------------------------------------------------------- */

  // 1. 错误态降级分支（集成 ErrorView，展示 traceId 一键复制）
  if (error) {
    return (
      <div className={`icg-metadata-table-error ${className}`} style={style}>
        <ErrorView
          error={error}
          onRetry={onRetry || onRefresh}
          message={`${tableMeta.name} 加载失败`}
        />
      </div>
    );
  }

  // 2. 初次加载骨架屏（集成 SkeletonView 表格 5 行）
  if (loading && (!dataSource || dataSource.length === 0)) {
    return (
      <div className={`icg-metadata-table-loading ${className}`} style={style}>
        <SkeletonView
          variant="table"
          rows={5}
          active
          tip={`正在加载 ${tableMeta.name} 数据...`}
        />
      </div>
    );
  }

  /* ----------------------------------------------------------------------- */
  /* 行选择配置（支持批量操作门禁）                                          */
  /* ----------------------------------------------------------------------- */
  const rowSelection = onSelectChange
    ? {
        selectedRowKeys: selectedRowKeys || [],
        onChange: (keys: React.Key[], rows: T[]) => onSelectChange(keys, rows),
      }
    : undefined;

  /* ----------------------------------------------------------------------- */
  /* 风险行高亮与急迫置顶样式（规范 9.1 规则 4）                             */
  /* ----------------------------------------------------------------------- */
  const getRowClassName = (record: T) => {
    const classes: string[] = ['icg-table-row'];
    const risk = isRiskRow(record, riskRowPredicate || tableMeta.riskRowPredicate);
    if (risk) classes.push('row-danger'); // 浅红底 #FFF5F5

    const urgent = isUrgentRow(record, 3, urgentRowPredicate || tableMeta.urgentRowPredicate);
    if (urgent) classes.push('row-urgent');

    return classes.join(' ');
  };

  /* ----------------------------------------------------------------------- */
  /* 密度切换菜单                                                            */
  /* ----------------------------------------------------------------------- */
  const densityMenuItems = [
    { key: 'small', label: '紧凑 (Small)' },
    { key: 'middle', label: '默认 (Middle)' },
    { key: 'large', label: '宽松 (Large)' },
  ];

  return (
    <div
      className={`icg-metadata-table-wrapper ${className}`}
      style={style}
      data-testid="metadata-table-container"
    >
      {/* 1. 表格顶部工具栏 */}
      <div className="icg-table-toolbar">
        <div className="icg-toolbar-left">
          <span className="icg-table-title">
            <strong>{tableMeta.name}</strong>
            <span className="icg-table-count">（共 {filteredData.length} 项）</span>
          </span>
          {searchable && (
            <Input
              prefix={<SearchOutlined style={{ color: '#8c8c8c' }} />}
              placeholder={`搜索 ${tableMeta.name} 内容 / 编号...`}
              value={searchKeyword}
              onChange={e => handleSearch(e.target.value)}
              allowClear
              style={{ width: 260 }}
              aria-label="表格内容检索"
              data-testid="metadata-table-search"
            />
          )}
        </div>

        <div className="icg-toolbar-right">
          {toolbarExtra}

          {onRefresh && (
            <Tooltip title="刷新数据">
              <Button
                icon={<ReloadOutlined />}
                loading={loading}
                onClick={onRefresh}
                aria-label="刷新数据"
              />
            </Tooltip>
          )}

          <Dropdown
            menu={{
              items: densityMenuItems,
              selectedKeys: [currentSize],
              onClick: ({ key }) => setCurrentSize(key as any),
            }}
          >
            <Tooltip title="表格密度">
              <Button icon={<ColumnHeightOutlined />} aria-label="调整表格密度" />
            </Tooltip>
          </Dropdown>
        </div>
      </div>

      {/* 2. 批量操作浮动栏（支持规范 9.1 规则 6 合规门禁） */}
      {selectedRecords.length > 0 && (
        <div className="icg-batch-bar" data-testid="metadata-batch-bar">
          <div className="icg-batch-info">
            <span className="icg-batch-count">
              已选中 <strong>{selectedRecords.length}</strong> 项
            </span>
            {!batchValidation.allowed && (
              <span className="icg-batch-warning">
                <WarningOutlined style={{ color: '#d9363e', marginRight: 4 }} />
                含 {batchValidation.nonBatchableCount} 项星号/废标/资格条款，依据合规规范（§5.2.2）禁止批量确认，须逐项核对。
              </span>
            )}
          </div>

          <div className="icg-batch-actions">
            {batchActions ? (
              batchActions(selectedRecords, batchValidation.allowed)
            ) : (
              <Space>
                {onBatchConfirm && (
                  <Tooltip
                    title={
                      !batchValidation.allowed
                        ? '选中的条目中包含不可批量确认的关键条款（星号/废标/资格），请剔除后重试。'
                        : undefined
                    }
                  >
                    <Popconfirm
                      title="批量确认提醒"
                      description={`确定批量确认选中的 ${selectedRecords.length} 项记录吗？`}
                      disabled={!batchValidation.allowed}
                      onConfirm={() => onBatchConfirm(selectedRecords)}
                      okText="确认"
                      cancelText="取消"
                    >
                      <Button
                        type="primary"
                        size="small"
                        disabled={!batchValidation.allowed}
                        data-testid="batch-confirm-button"
                      >
                        批量确认
                      </Button>
                    </Popconfirm>
                  </Tooltip>
                )}
                {onSelectChange && (
                  <Button
                    size="small"
                    onClick={() => onSelectChange([], [])}
                  >
                    清空选择
                  </Button>
                )}
              </Space>
            )}
          </div>
        </div>
      )}

      {/* 3. 主表格组件（优先无横滚排版） */}
      <Table
        rowKey={rowKey}
        columns={columns}
        dataSource={filteredData}
        loading={loading}
        size={currentSize}
        pagination={
          pagination === false
            ? false
            : {
                pageSize: 10,
                showTotal: total => `共 ${total} 条记录`,
                showSizeChanger: true,
                ...pagination,
              }
        }
        rowSelection={rowSelection}
        rowClassName={getRowClassName}
        onRow={record => ({
          onClick: () => onRowClick && onRowClick(record),
        })}
        // 无横向滚动优先原则：当 budget.fitsWithoutScroll 为真且未强行开启时，scroll.x 为 undefined
        scroll={
          forceScrollX || !budget.fitsWithoutScroll
            ? { x: budget.scrollX || 'max-content' }
            : undefined
        }
        locale={{
          emptyText: (
            <EmptyState
              mode={searchKeyword ? 'search' : 'empty'}
              title={searchKeyword ? '未找到匹配记录' : '暂无数据'}
              description={
                searchKeyword
                  ? `未找到与 “${searchKeyword}” 相关的条目，请调整搜索词或重置筛选。`
                  : tableMeta.description || '当前列表暂无数据记录'
              }
            />
          ),
        }}
      />

      {/* 4. 长文本侧边抽屉详情查看（保障 1280px 下无需横向滚动即可完整查阅文本） */}
      <Drawer
        title={detailDrawerTitle}
        open={drawerOpen}
        onClose={closeDetailDrawer}
        width={560}
        data-testid="metadata-table-detail-drawer"
        extra={
          <Button icon={<CloseOutlined />} type="text" onClick={closeDetailDrawer} />
        }
      >
        {activeDetail && (
          <div className="icg-table-detail-content">
            <div className="icg-detail-header" style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#1d2129' }}>
                {activeDetail.field.label}
              </div>
              {activeDetail.field.secondaryLabel && (
                <div style={{ fontSize: 12, color: '#8c8c8c', fontFamily: 'monospace' }}>
                  {activeDetail.field.secondaryLabel}
                </div>
              )}
            </div>

            <Card size="small" style={{ background: '#f7f8fa', marginBottom: 16 }}>
              <Paragraph
                style={{
                  fontSize: 14,
                  lineHeight: 1.8,
                  whiteSpace: 'pre-wrap',
                  marginBottom: 0,
                  color: '#1d2129',
                }}
              >
                {String(activeDetail.value)}
              </Paragraph>
            </Card>

            {/* 条款级别 */}
            {(activeDetail.record.level || activeDetail.record.category) && (
              <div style={{ marginBottom: 12 }}>
                <span className="muted" style={{ marginRight: 8, fontSize: 12 }}>
                  条款级别：
                </span>
                <LevelTag
                  level={activeDetail.record.level || activeDetail.record.category}
                />
              </div>
            )}

            {/* 引用证据卡片 */}
            {activeDetail.record.cite_type && (
              <div style={{ marginBottom: 12 }}>
                <span className="muted" style={{ marginRight: 8, fontSize: 12 }}>
                  关联证据：
                </span>
                <Cite
                  type={activeDetail.record.cite_type}
                  metadata={{
                    title: activeDetail.record.cite_title,
                    quote: activeDetail.record.cite_snippet,
                    page: activeDetail.record.page,
                  }}
                  onClick={
                    onLocateEvidence
                      ? () => onLocateEvidence(activeDetail.record)
                      : undefined
                  }
                />
              </div>
            )}

            {/* 来源溯源 */}
            {activeDetail.record.input_fingerprint && (
              <div style={{ marginTop: 16 }}>
                <span className="muted" style={{ display: 'block', marginBottom: 6, fontSize: 12 }}>
                  来源指纹溯源：
                </span>
                <SourceBar
                  kind={activeDetail.record.source || 'tender_doc'}
                  fingerprint={activeDetail.record.input_fingerprint}
                  status={activeDetail.record.source_stale ? 'stale' : 'confirmed'}
                  layout="bottom"
                />
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
}

// 别名导出（兼容 ProTableWrapper 命名）
export const ProTableWrapper = MetadataTable;
export default MetadataTable;
