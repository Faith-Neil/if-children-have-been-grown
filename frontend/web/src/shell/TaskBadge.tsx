// 为什么有这个文件：封装顶栏任务中心入口按钮与状态角标。
// 它解决什么问题：
// 1. 统一展示当前公司运行中 + 排队中的异步任务总数；
// 2. 提供无障碍属性（aria-label）与悬停提示（Tooltip）；
// 3. 点击即可唤起全局任务中心抽屉。

import React from 'react';
import { Badge, Button, Tooltip } from 'antd';
import { CheckSquareOutlined } from '@ant-design/icons';
import { calculateActiveTaskCount, type RawTaskInput, type TaskItem } from './task-center.ts';

export interface TaskBadgeProps {
  tasks: RawTaskInput[];
  companyId?: string;
  onClick: () => void;
  ariaLabel?: string;
  className?: string;
}

export function TaskBadge({
  tasks,
  companyId,
  onClick,
  ariaLabel = '查看后台任务中心',
  className = '',
}: TaskBadgeProps) {
  const activeCount = calculateActiveTaskCount(tasks, companyId);
  const tooltipTitle =
    activeCount > 0 ? `任务中心（${activeCount} 项任务进行中）` : '任务中心';

  return (
    <Tooltip title={tooltipTitle}>
      <Button
        type="text"
        icon={
          <Badge
            count={activeCount}
            size="small"
            overflowCount={99}
            offset={[2, -2]}
            data-testid="header-task-badge-count"
          >
            <CheckSquareOutlined style={{ fontSize: 16 }} />
          </Badge>
        }
        aria-label={ariaLabel}
        onClick={onClick}
        className={`task-badge-btn ${className}`.trim()}
        data-testid="header-task-badge-btn"
        data-active-count={activeCount}
      />
    </Tooltip>
  );
}
