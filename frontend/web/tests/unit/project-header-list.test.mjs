// 为什么有这个文件：验证 ProjectHeader 摘要条与项目列表页的倒计时计算、页签与权限过滤、状态与分册筛选、标的金额脱敏等核心业务逻辑。
// 它解决什么问题：落实 APP-M2-T094 与 APP-M2-T095，确保八角色权限感知、只读成员无编辑设置入口、涉密项目标记与多维筛选规则精准执行。

import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  calculateProjectCountdown,
  formatCurrencyAmount,
  canAccessProjectSettings,
  filterProjectTabs,
  PROJECT_HEADER_TABS,
} from '../../src/project/project-header-core.ts';
import {
  deriveProjectStatus,
  deriveVolumeStatus,
  filterProjectList,
} from '../../src/project/project-list-core.ts';
import { maskSensitiveValue } from '../../src/admin/sensitive-mask.ts';

/* ========================================================================= */
/* 1. ProjectHeader: 截止倒计时算法 (calculateProjectCountdown)             */
/* ========================================================================= */

test('ProjectHeader: 倒计时计算与临期、过期判定', () => {
  const baseTime = new Date('2026-10-22T12:00:00Z').getTime();

  // 1. 距离截止还有 5 天（非紧急状态）
  const fiveDaysLater = new Date('2026-10-27T15:30:00Z').toISOString();
  const resNormal = calculateProjectCountdown(fiveDaysLater, baseTime);
  assert.equal(resNormal.status, 'normal');
  assert.equal(resNormal.isUrgent, false);
  assert.equal(resNormal.isExpired, false);
  assert.equal(resNormal.days, 5);
  assert.equal(resNormal.hours, 3);
  assert.equal(resNormal.color, 'blue');
  assert.match(resNormal.label, /剩余 5 天 3 小时/);

  // 2. 距离截止小于 3 天（紧急临期状态）
  const twoDaysLater = new Date('2026-10-24T18:00:00Z').toISOString();
  const resUrgent = calculateProjectCountdown(twoDaysLater, baseTime);
  assert.equal(resUrgent.status, 'urgent');
  assert.equal(resUrgent.isUrgent, true);
  assert.equal(resUrgent.isExpired, false);
  assert.equal(resUrgent.days, 2);
  assert.equal(resUrgent.color, 'orange');
  assert.match(resUrgent.label, /剩余 2 天 6 小时/);

  // 3. 距离截止不足 1 天
  const fewHoursLater = new Date('2026-10-22T16:45:00Z').toISOString();
  const resHours = calculateProjectCountdown(fewHoursLater, baseTime);
  assert.equal(resHours.status, 'urgent');
  assert.equal(resHours.isUrgent, true);
  assert.equal(resHours.days, 0);
  assert.equal(resHours.hours, 4);
  assert.equal(resHours.minutes, 45);
  assert.match(resHours.label, /剩余 4 小时 45 分钟/);

  // 4. 已截止（超时）
  const pastTime = new Date('2026-10-20T10:00:00Z').toISOString();
  const resExpired = calculateProjectCountdown(pastTime, baseTime);
  assert.equal(resExpired.status, 'expired');
  assert.equal(resExpired.isUrgent, true);
  assert.equal(resExpired.isExpired, true);
  assert.equal(resExpired.color, 'red');
  assert.equal(resExpired.label, '已截止');

  // 5. 空值或非法日期边界安全
  const resEmpty = calculateProjectCountdown(null, baseTime);
  assert.equal(resEmpty.status, 'none');
  assert.equal(resEmpty.label, '未设定截止时间');

  const resInvalid = calculateProjectCountdown('not-a-date', baseTime);
  assert.equal(resInvalid.status, 'none');
  assert.equal(resInvalid.label, '截止时间格式无效');
});

/* ========================================================================= */
/* 2. 标的金额格式化与脱敏处理 (formatCurrencyAmount & MaskedField)          */
/* ========================================================================= */

test('ProjectHeader: 标的金额货币格式化与脱敏掩码规则', () => {
  // 1. 金额千分位格式化
  assert.equal(formatCurrencyAmount(12800000), '¥ 12,800,000.00');
  assert.equal(formatCurrencyAmount(500000.5), '¥ 500,000.50');
  assert.equal(formatCurrencyAmount('8600000'), '¥ 8,600,000.00');
  assert.equal(formatCurrencyAmount(null), '未填写');
  assert.equal(formatCurrencyAmount(''), '未填写');

  // 2. 脱敏掩码处理（前留2位 ¥ ，后留3位 .00，中间掩码）
  const formatted = formatCurrencyAmount(12800000); // "¥ 12,800,000.00"
  const masked = maskSensitiveValue(formatted, 'custom', { prefix: 2, suffix: 3, maskChar: '*' });
  assert.equal(masked.startsWith('¥ '), true);
  assert.equal(masked.endsWith('.00'), true);
  assert.equal(masked.includes('*'), true);
  assert.notEqual(masked, formatted);
});

/* ========================================================================= */
/* 3. 八角色权限感知与设置页签过滤 (canAccessProjectSettings & filterProjectTabs) */
/* ========================================================================= */

test('ProjectHeader: 八角色权限感知与只读成员设置入口拦截', () => {
  // 1. 允许访问项目设置的高权限角色
  assert.equal(canAccessProjectSettings('project_lead'), true);
  assert.equal(canAccessProjectSettings('lead'), true);
  assert.equal(canAccessProjectSettings('manager'), true);
  assert.equal(canAccessProjectSettings('company_admin'), true);

  // 2. 严厉拦截只读角色、审核角色与一般成员访问设置入口
  assert.equal(canAccessProjectSettings('viewer'), false);
  assert.equal(canAccessProjectSettings('readonly'), false);
  assert.equal(canAccessProjectSettings('auditor'), false);
  assert.equal(canAccessProjectSettings('group_admin'), false);
  assert.equal(canAccessProjectSettings(null), false);

  // 3. 显式自定义权限优先
  assert.equal(canAccessProjectSettings('viewer', { manage_project: true }), true);
  assert.equal(canAccessProjectSettings('project_lead', { manage_project: false }), false);

  // 4. filterProjectTabs 页签过滤：只读角色自动剔除 settings 页签
  const tabs = [...PROJECT_HEADER_TABS];
  const readonlyTabs = filterProjectTabs(tabs, null, 'p1', 'viewer');
  assert.equal(readonlyTabs.some(t => t.key === 'settings'), false);
  assert.equal(readonlyTabs.some(t => t.key === 'overview'), true);
  assert.equal(readonlyTabs.some(t => t.key === 'editor'), true);

  const leadTabs = filterProjectTabs(tabs, null, 'p1', 'project_lead');
  assert.equal(leadTabs.some(t => t.key === 'settings'), true);
});

/* ========================================================================= */
/* 4. 项目状态与分册推导算法 (deriveProjectStatus & deriveVolumeStatus)      */
/* ========================================================================= */

test('ProjectListPage: 项目状态与分册状态推导', () => {
  // 1. 显式 status 优先
  assert.equal(deriveProjectStatus({ id: '1', name: 'A', company_id: 'alpha', status: 'completed' }), 'completed');
  assert.equal(deriveProjectStatus({ id: '2', name: 'B', company_id: 'alpha', status: 'writing' }), 'writing');

  // 2. 根据分册状态推导
  assert.equal(
    deriveProjectStatus({
      id: '3',
      name: 'C',
      company_id: 'alpha',
      volumes_status: { technical: 'completed', business: 'completed' },
    }),
    'completed'
  );

  assert.equal(
    deriveProjectStatus({
      id: '4',
      name: 'D',
      company_id: 'alpha',
      volumes_status: { technical: 'submitted', business: 'writing' },
    }),
    'reviewing'
  );

  assert.equal(
    deriveProjectStatus({
      id: '5',
      name: 'E',
      company_id: 'alpha',
      revision: 2,
    }),
    'writing'
  );

  assert.equal(
    deriveProjectStatus({
      id: '6',
      name: 'F',
      company_id: 'alpha',
      revision: 1,
    }),
    'preparing'
  );

  // 3. 分册状态综合对象
  const v1 = deriveVolumeStatus({
    id: '7',
    name: 'G',
    company_id: 'alpha',
    volumes_status: { technical: 'completed', business: 'completed' },
  });
  assert.equal(v1.isBothDone, true);
  assert.equal(v1.technical, 'completed');
  assert.equal(v1.business, 'completed');

  const v2 = deriveVolumeStatus({
    id: '8',
    name: 'H',
    company_id: 'alpha',
    volumes_status: { technical: 'pending', business: 'completed' },
  });
  assert.equal(v2.isBothDone, false);
  assert.equal(v2.technical, 'pending');
});

/* ========================================================================= */
/* 5. 项目列表多维筛选算法 (filterProjectList)                              */
/* ========================================================================= */

test('ProjectListPage: 状态、涉密属性、分册状态与关键词多维筛选', () => {
  const sampleProjects = [
    {
      id: 'p-01',
      name: '国家电网调度平台升级改造项目',
      tender_number: 'SGCC-2026-001',
      company_id: 'alpha',
      status: 'writing',
      sensitive: true,
      volumes_status: { technical: 'writing', business: 'writing' },
    },
    {
      id: 'p-02',
      name: '某涉密军工数据中心系统采购',
      tender_number: 'MIL-SECRET-902',
      company_id: 'alpha',
      status: 'reviewing',
      sensitive: true,
      volumes_status: { technical: 'completed', business: 'writing' },
    },
    {
      id: 'p-03',
      name: '市智慧交通综合分析系统',
      tender_number: 'TRAFFIC-2026-X',
      company_id: 'alpha',
      status: 'completed',
      sensitive: false,
      volumes_status: { technical: 'completed', business: 'completed' },
    },
    {
      id: 'p-04',
      name: '普通企业OA协同平台招标',
      tender_number: 'OA-2026-888',
      company_id: 'alpha',
      status: 'preparing',
      sensitive: false,
      volumes_status: { technical: 'pending', business: 'pending' },
    },
  ];

  // 1. 关键词筛选（名称匹配与编号匹配）
  const searchName = filterProjectList(sampleProjects, { keyword: '电网' });
  assert.equal(searchName.length, 1);
  assert.equal(searchName[0].id, 'p-01');

  const searchTender = filterProjectList(sampleProjects, { keyword: 'MIL-SECRET' });
  assert.equal(searchTender.length, 1);
  assert.equal(searchTender[0].id, 'p-02');

  // 2. 涉密属性筛选
  const sensitiveOnly = filterProjectList(sampleProjects, { sensitive: 'sensitive' });
  assert.equal(sensitiveOnly.length, 2);
  assert.equal(sensitiveOnly.every(p => p.sensitive === true), true);

  const normalOnly = filterProjectList(sampleProjects, { sensitive: 'normal' });
  assert.equal(normalOnly.length, 2);
  assert.equal(normalOnly.every(p => !p.sensitive), true);

  // 3. 状态筛选
  const writingOnly = filterProjectList(sampleProjects, { status: 'writing' });
  assert.equal(writingOnly.length, 1);
  assert.equal(writingOnly[0].id, 'p-01');

  const completedOnly = filterProjectList(sampleProjects, { status: 'completed' });
  assert.equal(completedOnly.length, 1);
  assert.equal(completedOnly[0].id, 'p-03');

  // 4. 分册状态筛选
  const bothDone = filterProjectList(sampleProjects, { volumeStatus: 'both_done' });
  assert.equal(bothDone.length, 1);
  assert.equal(bothDone[0].id, 'p-03');

  const techPending = filterProjectList(sampleProjects, { volumeStatus: 'technical_pending' });
  // p-01(writing!=completed), p-04(pending!=completed)
  assert.equal(techPending.length, 2);

  // 5. 组合筛选：涉密 + 审核中
  const combo = filterProjectList(sampleProjects, { sensitive: 'sensitive', status: 'reviewing' });
  assert.equal(combo.length, 1);
  assert.equal(combo[0].id, 'p-02');
});
