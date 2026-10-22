// 为什么有这个文件：定义大纲树与章节类型的核心逻辑、红线门禁判定、树排序算法与增值理由校验。
// 它解决什么问题：
// 1. 严格落实 PRD v1.8 §5.7.2 / §5.7.8 验收红线：星号条款(★)或废标条款对应的章节绝对禁止标记为“不适用”；
// 2. 提供同级章节上移/下移排序与多层级编号自动归一化算法；
// 3. 规范专项方案、通用方案、系统生成、封面目录与不适用 5 类章节类型元信息；
// 4. 纯逻辑脱离 DOM 实现，确保全面单元测试覆盖。

import type { Volume } from '../shared/types.ts';

/**
 * PRD v1.8 §5.7.2 规定的 5 类核心章节类型
 */
export type ChapterType =
  | 'specialized'       // 专项方案（针对特定技术/实施重点）
  | 'general'           // 通用方案（标准/常规能力）
  | 'system_generated'  // 系统生成（评分索引表、响应矩阵等）
  | 'cover_and_catalog' // 封面与目录
  | 'not_applicable';   // 不适用（免于响应）

/**
 * 章节大纲节点模型
 */
export interface ChapterOutlineNode {
  id: string;
  key?: string;
  title: string;
  chapterNumber?: string;
  volume: Volume | string;
  chapterType: ChapterType;
  orderIndex: number;
  parentId?: string | null;
  valueAddedReason?: string;
  isStarred?: boolean;      // 是否包含星号条款 ★
  isBlocker?: boolean;      // 是否包含废标条款
  clauseCount?: number;     // 关联条款数量
  requirementCount?: number;
  assigneeId?: string | null;
  assigneeName?: string | null;
  assignee_name?: string | null;
  isLeaf?: boolean;
  children?: ChapterOutlineNode[];
}

/**
 * 章节类型元信息定义
 */
export interface ChapterTypeMeta {
  type: ChapterType;
  label: string;
  color: string;
  description: string;
  isAiRelevant?: boolean;
}

export const CHAPTER_TYPES_CONFIG: Record<ChapterType, ChapterTypeMeta> = {
  specialized: {
    type: 'specialized',
    label: '专项方案',
    color: '#1e4db7', // 业务主蓝
    description: '针对招标关键需求的专项应对方案与深度设计',
    isAiRelevant: true,
  },
  general: {
    type: 'general',
    label: '通用方案',
    color: '#13c2c2', // 青色
    description: '公司标准与通用技术/服务保障方案',
  },
  system_generated: {
    type: 'system_generated',
    label: '系统生成',
    color: '#722ed1', // 专属 AI 紫色
    description: '由系统根据抽取事实、响应矩阵及评分规则自动汇总生成',
    isAiRelevant: true,
  },
  cover_and_catalog: {
    type: 'cover_and_catalog',
    label: '封面目录',
    color: '#8c8c8c', // 中性灰
    description: '标书封面、目录及格式化章节',
  },
  not_applicable: {
    type: 'not_applicable',
    label: '不适用',
    color: '#d46b08', // 橙棕色
    description: '经研判免于响应或本项目不适用的章节',
  },
};

/**
 * 获取章节类型的元信息
 */
export function getChapterTypeMeta(type: ChapterType): ChapterTypeMeta {
  return CHAPTER_TYPES_CONFIG[type] || {
    type,
    label: type,
    color: '#1e4db7',
    description: '标准章节',
  };
}

/**
 * 【核心门禁红线】判定章节是否允许标记为“不适用”
 * 规则：若关联了星号条款(★)或废标条款，绝对禁止标记为“不适用”！
 */
export function canMarkNotApplicable(node: {
  isStarred?: boolean;
  isBlocker?: boolean;
  title?: string;
}): { allowed: boolean; reason?: string } {
  if (node.isStarred) {
    return {
      allowed: false,
      reason: '该章节对应星号(★)关键条款，合规门禁严格禁止标记为“不适用”！',
    };
  }
  if (node.isBlocker) {
    return {
      allowed: false,
      reason: '该章节对应废标关键条款，合规门禁严格禁止标记为“不适用”！',
    };
  }
  return {
    allowed: true,
  };
}

/**
 * 校验章节类型变更合法性
 */
export function validateChapterTypeChange(
  node: { isStarred?: boolean; isBlocker?: boolean },
  targetType: ChapterType
): { valid: boolean; error?: string } {
  if (targetType === 'not_applicable') {
    const check = canMarkNotApplicable(node);
    if (!check.allowed) {
      return {
        valid: false,
        error: check.reason,
      };
    }
  }
  return { valid: true };
}

/**
 * 同级节点顺序调整（上移/下移）
 */
export function reorderNodes(
  nodes: ChapterOutlineNode[],
  targetId: string,
  direction: 'up' | 'down'
): ChapterOutlineNode[] {
  const index = nodes.findIndex(n => n.id === targetId);
  if (index === -1) return nodes;

  if (direction === 'up' && index === 0) return nodes; // 已在最前
  if (direction === 'down' && index === nodes.length - 1) return nodes; // 已在最后

  const nextNodes = [...nodes];
  const swapIndex = direction === 'up' ? index - 1 : index + 1;
  const temp = nextNodes[index];
  nextNodes[index] = nextNodes[swapIndex];
  nextNodes[swapIndex] = temp;

  // 重新指派连续的 orderIndex
  return nextNodes.map((item, idx) => ({
    ...item,
    orderIndex: idx + 1,
  }));
}

/**
 * 递归重新归一化章节编号（如 1, 1.1, 1.2, 2, 2.1 等）
 */
export function normalizeChapterNumbers(
  nodes: ChapterOutlineNode[],
  prefix = ''
): ChapterOutlineNode[] {
  return nodes.map((node, index) => {
    const currentNumber = prefix ? `${prefix}.${index + 1}` : `${index + 1}`;
    const updatedNode: ChapterOutlineNode = {
      ...node,
      orderIndex: index + 1,
      chapterNumber: currentNumber,
    };
    if (updatedNode.children && updatedNode.children.length > 0) {
      updatedNode.children = normalizeChapterNumbers(updatedNode.children, currentNumber);
    }
    return updatedNode;
  });
}

/**
 * 增值理由快速预置选项模板
 */
export const VALUE_ADDED_PRESETS = [
  '响应招标文件核心需求，提供超出标准指标 20% 的性能与容量保障承诺。',
  '针对本项目关键工期要求，组建 7x24h 本地专属运维保障团队与 15 分钟响应机制。',
  '提供行业领先的双活灾备架构与数据全生命周期零泄露安全加密防护方案。',
  '赠送项目投产后首年免费定期巡检、安全合规审计与应急保障演练服务。',
  '根据评分办法加分项要求，配套提供成熟的国家级示范工程标杆案例与复用成果。',
];

/**
 * 增值理由校验函数
 */
export function validateValueAddedReason(
  reason?: string,
  chapterType?: ChapterType
): { valid: boolean; error?: string } {
  if (!reason || reason.trim() === '') {
    if (chapterType === 'specialized') {
      return {
        valid: true, // 允许为空但建议填写
      };
    }
    return { valid: true };
  }

  const trimmed = reason.trim();
  if (trimmed.length > 500) {
    return {
      valid: false,
      error: '增值理由最多支持 500 个字符，当前字数超出上限。',
    };
  }

  return { valid: true };
}

/**
 * 将工作区章节列表与条款映射为完整的大纲树节点数组
 */
export function mapChaptersToOutlineNodes(
  chapters: Array<{
    id: string;
    title: string;
    volume: Volume | string;
    assignee_id?: string | null;
    assignee_name?: string | null;
    requirement_ids?: string[];
    chapter_type?: ChapterType;
    value_added_reason?: string;
  }>,
  requirements: Array<{
    id: string;
    chapter_id?: string | null;
    starred?: boolean;
    is_starred?: boolean;
    blocker?: boolean;
    is_blocker?: boolean;
    severity?: string;
  }> = []
): ChapterOutlineNode[] {
  return chapters.map((chapter, index) => {
    // 找出与当前章节关联的所有要求条款
    const matchedReqs = requirements.filter(
      r => r.chapter_id === chapter.id || (chapter.requirement_ids && chapter.requirement_ids.includes(r.id))
    );

    const isStarred = matchedReqs.some(r => r.starred || r.is_starred);
    const isBlocker = matchedReqs.some(r => r.blocker || r.is_blocker || r.severity === 'blocker');

    // 推导章节类型
    let derivedType: ChapterType = chapter.chapter_type || 'general';
    if (!chapter.chapter_type) {
      const lowerTitle = chapter.title.toLowerCase();
      if (lowerTitle.includes('评分') || lowerTitle.includes('矩阵') || lowerTitle.includes('索引')) {
        derivedType = 'system_generated';
      } else if (lowerTitle.includes('封面') || lowerTitle.includes('目录')) {
        derivedType = 'cover_and_catalog';
      } else if (isStarred || isBlocker || lowerTitle.includes('专项') || lowerTitle.includes('关键') || lowerTitle.includes('重点')) {
        derivedType = 'specialized';
      }
    }

    return {
      id: chapter.id,
      key: chapter.id,
      title: chapter.title,
      volume: chapter.volume,
      chapterType: derivedType,
      orderIndex: index + 1,
      chapterNumber: String(index + 1),
      isStarred,
      isBlocker,
      clauseCount: matchedReqs.length,
      requirementCount: matchedReqs.length,
      assigneeId: chapter.assignee_id,
      assigneeName: chapter.assignee_name,
      assignee_name: chapter.assignee_name,
      valueAddedReason: chapter.value_added_reason,
      isLeaf: true,
    };
  });
}

