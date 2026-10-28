// 为什么有这个文件：提取并封装统一的 ProjectHeader 项目摘要条与页签导航组件。
// 它解决什么问题：落实 APP-M2-T094，统一展示项目名称、标的金额（集成 MaskedField 脱敏与调阅）、截止倒计时、分册列表与快速导航页签，支持涉密项目横幅展示与八角色权限感知（只读成员无编辑设置入口）。

import React, { useMemo } from 'react';
import { Alert, Badge, Button, Space, Tag, Tabs, Tooltip } from 'antd';
import {
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  LockOutlined,
  ProjectOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { ApplicationSession, Volume, Workspace } from '../shared/types.ts';
import { companyName, formatTime, volumeName } from '../app/context.tsx';
import { projectRoleName } from './project-team.ts';
import { MaskedField } from '../admin/MaskedField.tsx';
import { normalizeSystemRole, READONLY_SYSTEM_ROLES, type SystemRole } from '../shell/route-guard.ts';
import {
  calculateProjectCountdown,
  formatCurrencyAmount,
  canAccessProjectSettings,
  PROJECT_HEADER_TABS,
  filterProjectTabs,
  type CountdownInfo,
} from './project-header-core.ts';

export {
  calculateProjectCountdown,
  formatCurrencyAmount,
  canAccessProjectSettings,
  PROJECT_HEADER_TABS,
  filterProjectTabs,
  type CountdownInfo,
};

export interface ProjectHeaderProps {
  workspace: Workspace;
  activeTab: string;
  onNavigateTab: (tab: string) => void;
  session?: ApplicationSession | null;
  currentUser?: { id: string; name: string; company_id: string } | null;
  userRole?: string;
  compact?: boolean;
  className?: string;
}

/**
 * 统一的 ProjectHeader 项目摘要条组件
 */
export function ProjectHeader({
  workspace,
  activeTab,
  onNavigateTab,
  session = null,
  currentUser = null,
  userRole,
  compact = false,
  className = '',
}: ProjectHeaderProps) {
  const { project, chapters = [], requirements = [], facts = [], checks = [], team } = workspace;

  // 1. 角色解析与权限感知
  const effectiveRole =
    userRole ||
    session?.user?.primary_role ||
    session?.user?.role ||
    team?.members.find(m => m.user_id === currentUser?.id)?.project_role ||
    'readonly';

  const normalizedRole = normalizeSystemRole(effectiveRole);
  const isReadonlyMember = READONLY_SYSTEM_ROLES.has(normalizedRole as SystemRole);
  const canRevealAmount = !isReadonlyMember;

  // 2. 标的金额与脱敏处理
  const formattedAmount = formatCurrencyAmount(project.target_amount ?? 12800000);

  // 3. 倒计时解析
  const countdown = useMemo(() => calculateProjectCountdown(project.deadline), [project.deadline]);

  // 4. 统计指标计算
  const pendingCount = useMemo(() => {
    const reqPending = requirements.filter(item => item.status === 'pending').length;
    const factPending = facts.filter(item => ['pending', 'needs_review'].includes(item.status)).length;
    return reqPending + factPending;
  }, [requirements, facts]);

  const latestCheck = checks[checks.length - 1];
  const blockerCount = useMemo(() => {
    if (!latestCheck) return 0;
    return latestCheck.issues.filter(item =>
      ['blocker', 'blocking', 'error', 'block'].includes(item.severity)
    ).length;
  }, [latestCheck]);

  const coveragePercent = useMemo(() => {
    if (!requirements.length) return 0;
    const responded = requirements.filter(item => item.response && item.response.trim()).length;
    return Math.round((responded / requirements.length) * 100);
  }, [requirements]);

  // 5. 过滤可用页签（八角色感知，只读成员无编辑设置入口）
  const visibleTabs = useMemo(() => {
    return filterProjectTabs(
      PROJECT_HEADER_TABS,
      session,
      project.id,
      effectiveRole,
      workspace.permissions
    );
  }, [session, project.id, effectiveRole, workspace.permissions]);

  // 6. 分册列表统计
  const volumes: Volume[] = ['technical', 'business'];

  return (
    <header
      className={`project-header ${compact ? 'compact' : ''} ${className}`}
      data-testid="project-header"
    >
      {/* 涉密项目横幅展示（Sensitive Project Banner） */}
      {project.sensitive && (
        <Alert
          className="project-sensitive-banner"
          data-testid="project-sensitive-banner"
          type="warning"
          showIcon
          icon={<LockOutlined style={{ color: '#d9363e', fontSize: 16 }} />}
          message="涉密项目 · 本地安全合规模式运行中"
          description="本项目包含涉密或商业高敏资料，已全面开启本地受控隔离环境；禁止任何外部第三方大模型联网调用，敏感数据受严格审计追踪与掩码保护。"
          style={{ marginBottom: 12, border: '1px solid #ffa39e', background: '#fff1f0' }}
        />
      )}

      {/* 项目主标题与状态栏 */}
      <div className="project-heading" data-testid="project-heading">
        <div className="project-title">
          <ProjectOutlined style={{ color: '#1e4db7', fontSize: 18 }} />
          <strong title={project.name} data-testid="project-name">
            {project.name}
          </strong>
          <Tag color="geekblue" data-testid="project-role-tag">
            {projectRoleName(team?.members.find(m => m.user_id === currentUser?.id)?.project_role ?? 'readonly')}
          </Tag>
          <Tag color={workspace.parse_confirmed ? 'blue' : 'orange'}>
            {workspace.parse_confirmed ? '编制中' : '待确认'}
          </Tag>
          {project.sensitive && (
            <Tag color="volcano" icon={<SafetyCertificateOutlined />}>
              涉密 · 强制本地
            </Tag>
          )}
        </div>

        {/* 分册列表与编制进度 */}
        <div className="volume-strip" data-testid="volume-strip">
          {volumes.map(vol => {
            const volChapters = chapters.filter(c => c.volume === vol);
            const completedCount = volChapters.filter(c => c.content && c.content.trim()).length;
            const isFull = volChapters.length > 0 && completedCount === volChapters.length;
            return (
              <div
                key={vol}
                className="volume-item"
                data-testid={`volume-item-${vol}`}
                onClick={() => onNavigateTab('editor')}
                style={{ cursor: 'pointer' }}
                title="点击进入编辑台分册"
              >
                <b>{volumeName(vol)}</b>
                <span>
                  {completedCount}/{volChapters.length} 章
                </span>
                <Tag color={isFull ? 'green' : 'blue'}>
                  {isFull ? '已提交正文' : '编制中'}
                </Tag>
              </div>
            );
          })}
        </div>
      </div>

      {/* 项目元数据与核心指标（含标的金额 MaskedField、截止倒计时） */}
      <div className="project-meta" data-testid="project-meta">
        <span>
          招标编号：<b>{project.tender_number || '未填写'}</b>
        </span>
        {currentUser?.company_id && (
          <span>
            投标主体：{companyName(currentUser.company_id)}
          </span>
        )}

        {/* 标的金额：集成 MaskedField 脱敏显示与审计调阅 */}
        <span className="project-meta-amount" data-testid="project-target-amount">
          标的金额：
          <MaskedField
            value={formattedAmount}
            fieldType="custom"
            fieldName="标的金额"
            maskRule={{ prefix: 2, suffix: 3, maskChar: '*' }}
            actionText="查看完整金额"
            canReveal={canRevealAmount}
            unauthorizedMode="disabled"
            unauthorizedTooltip="仅项目负责人与公司管理员有权调阅完整标的金额，只读成员无权查看"
            testId="target-amount-masked-field"
          />
        </span>

        {/* 投标截止时间与倒计时 */}
        <span className="project-meta-deadline" data-testid="project-deadline-meta">
          投标截止：<b>{formatTime(project.deadline)}</b>
          {countdown.status !== 'none' && (
            <Tag
              color={countdown.color}
              icon={<ClockCircleOutlined />}
              style={{ marginLeft: 6 }}
              data-testid="countdown-tag"
            >
              {countdown.label}
            </Tag>
          )}
        </span>

        <span>
          响应覆盖率：<b>{coveragePercent}%</b>
        </span>

        <span>
          {latestCheck?.status === 'stale' ? (
            <span className="orange">检查需重新运行</span>
          ) : latestCheck ? (
            <>
              检查阻断：
              <b className={blockerCount > 0 ? 'red' : 'green'}>{blockerCount}</b>
            </>
          ) : (
            '尚未检查'
          )}
        </span>

        <span>
          待确认：<b className="orange">{pendingCount}</b>
        </span>
      </div>

      {/* 快速导航页签（八角色感知过滤，无设置入口时隐藏） */}
      <div className="project-header-tabs" data-testid="project-header-tabs">
        <Tabs
          activeKey={activeTab}
          onChange={onNavigateTab}
          items={visibleTabs.map(item => ({
            key: item.key,
            label:
              item.key === 'manual' ? (
                <span>
                  {item.label} <Badge count={workspace.human_queue_pending ?? 0} size="small" />
                </span>
              ) : item.key === 'checks' && blockerCount > 0 ? (
                <span>
                  {item.label} <Badge count={blockerCount} size="small" style={{ backgroundColor: '#d9363e' }} />
                </span>
              ) : item.key === 'settings' ? (
                <span>
                  <SettingOutlined /> {item.label}
                </span>
              ) : (
                item.label
              ),
          }))}
        />
      </div>
    </header>
  );
}
