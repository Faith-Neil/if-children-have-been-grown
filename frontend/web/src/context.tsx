// 为什么有这个文件：共享当前项目和经过权限校验的操作入口。
// 它解决什么问题：每个项目页签更新后读取同一后台状态，避免各页假数据。
import { createContext, useContext } from 'react';
import type { Account, Evidence, SlaTemplate, Workspace } from './types';

export type ProjectContextValue = {
  workspace: Workspace; token: string; user: Account; busy: boolean; library: Evidence[]; slaTemplates: SlaTemplate[];
  mutate: (path: string, method: string, body?: unknown) => Promise<unknown>;
  reload: () => Promise<Workspace | undefined>;
  report: (error: unknown) => void;
  navigate: (tab: string) => void;
};
export const ProjectContext = createContext<ProjectContextValue | null>(null);
export function useProject() { const value = useContext(ProjectContext); if (!value) throw new Error('项目未加载'); return value; }
export const volumeName = (value: string) => value === 'technical' ? '技术分册' : value === 'business' ? '商务分册' : '全部分册';
export const roleName = (value: string) => value === 'manager' ? '公司经理账号' : value === 'viewer' ? '公司只读账号' : '公司编写账号';
export const companyName = (value: string) => value === 'alpha' ? '华东数智科技有限公司（合成）' : '远山信息技术有限公司（合成）';
export const formatTime = (value?: string | null) => value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false }) : '未设置';
export const categoryName = (value: string) => ({ mandatory: '必需条款', qualification: '资格要求', technical: '技术服务', commercial: '商务要求', business: '商务要求', sla: 'SLA 要求', star: '星号条款', disqualification: '废标条款', score: '评分要点', other: '其他要求', scoring: '评分要点' }[value] ?? value);

export const paginationName = (value: string) => ({ explicit_form_feed: '按文本换页符定位', explicit_docx_breaks_only: '按Word明确分页符定位', pdf_page_index: '按PDF实际页码定位' }[value] ?? '页码尚未确定');
