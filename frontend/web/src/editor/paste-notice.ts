// 为什么有这个文件：提交正文后对“粘贴识别”结果的提示（PRD v1.8 §5.11.7；APP-M2-T188）。
// 它解决什么问题：把后台识别为“对话助手撰写（粘贴）”的段落和这些段落的复查问题写成一句提示，提醒编写人按模型所写的内容核对。

export type PastedParagraph = {
  paragraph_index: number; match_ratio: number; source_label: string; text: string;
  issues?: { rule_id: string; severity: string; message: string }[];
};

export function pasteNotice(pasted: PastedParagraph[] | null | undefined): string {
  if (!pasted?.length) return '';
  const issues = pasted.flatMap(p => p.issues ?? []);
  const where = pasted.map(p => `第 ${p.paragraph_index + 1} 段（重合 ${Math.round(p.match_ratio * 100)}%）`).join('、');
  return ` ${where}与对话助手输出高度重合，来源已记为“对话助手撰写（粘贴）”，请按模型所写内容核对数值和事实${
    issues.length ? `；复查发现 ${issues.length} 个问题：${issues.slice(0, 3).map(i => i.message).join('；')}` : ''}。`;
}
