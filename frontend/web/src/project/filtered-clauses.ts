// 为什么有这个文件：覆盖视图底部「已过滤条款查阅区」的纯展示逻辑。
// 它解决什么问题：把非技术/残句过滤原因统一成可读短标签，组件不做字符串判断。
export type FilteredClauseRow = {
  requirement_id: string;
  text: string;
  requirement_scope: 'non_technical' | 'fragment_filtered';
  non_tech_category?: string;
  fragment_reason?: string;
  source_page?: number | null;
  source_filename?: string | null;
};

const CATEGORY_LABEL: Record<string, string> = {
  qualification: '资格条件',
  pricing: '限价/报价',
  payment: '付款/费用',
  deposit: '保证金',
  format: '投标文件格式',
  procedure: '投标程序',
  business_or_packaging: '商务/合同条款',
};

const REASON_LABEL: Record<string, string> = {
  empty: '空内容',
  too_short: '过短',
  leading_broken_punct: '开头残缺',
  trailing_dangling_punct: '结尾悬空',
  trailing_incomplete_word: '结尾半词',
  unbalanced_brackets: '括号未闭合',
  ordinal_heading: '序号标题',
  section_heading: '章节标题',
  table_noise: '表格噪声',
  no_cjk_content: '无实质中文',
  short_no_action: '无实质动作',
  truncated_head: '开头被截断',
  truncated_tail: '结尾被截断',
  continuation_orphan: '续句碎片',
};

export function filteredClauseLabel(row: Pick<FilteredClauseRow, 'requirement_scope' | 'non_tech_category' | 'fragment_reason'>): string {
  if (row.requirement_scope === 'non_technical') return CATEGORY_LABEL[row.non_tech_category || ''] || '非技术条款';
  const reasons = String(row.fragment_reason || '').split('+').filter(Boolean).map(item => REASON_LABEL[item] || item);
  return reasons.length ? `残句：${reasons.join('、')}` : '残句';
}

export function filteredClauseRows(rows: unknown): FilteredClauseRow[] {
  if (!Array.isArray(rows)) return [];
  return rows.filter((row): row is FilteredClauseRow => {
    if (!row || typeof row !== 'object') return false;
    const item = row as Partial<FilteredClauseRow>;
    return typeof item.requirement_id === 'string' && typeof item.text === 'string'
      && (item.requirement_scope === 'non_technical' || item.requirement_scope === 'fragment_filtered');
  });
}
