// 为什么有这个文件：提取 App.tsx 登录屏界面，降低应用编排主文件行数。
// 它解决什么问题：解耦登录 UI 渲染与全局状态机，支持合成账号切换与登录提交。

import React from 'react';
import { Alert, Button, Card, Select } from 'antd';
import type { Account } from '../shared/types.ts';
import { roleName } from './context.tsx';

export interface LoginScreenProps {
  accounts: Account[];
  accountId: string;
  onAccountIdChange: (id: string) => void;
  onLogin: () => void;
  busy: boolean;
}

export function LoginScreen({
  accounts,
  accountId,
  onAccountIdChange,
  onLogin,
  busy,
}: LoginScreenProps) {
  return (
    <div className="login-screen">
      <section className="login-brand">
        <div className="brand-square">标</div>
        <h1>智能投标系统</h1>
        <p>让原文、证据和正文在同一处对齐</p>
        <div className="login-foot">
          ICG · 本地联调环境
          <br />
          合成资料用于验证流程
        </div>
      </section>
      <section className="login-main">
        <Card className="login-card" title="欢迎进入工作台">
          <Alert
            type="info"
            message="演示登录"
            description="选择合成账号体验。账号必须属于本公司并加入该项目才能读取资料；公司经理也不能进入未加入的项目。正式账号与密码登录尚未接入。"
            showIcon
          />
          <div className="form-label">体验账号</div>
          <Select
            aria-label="演示账号"
            style={{ width: '100%' }}
            value={accountId}
            onChange={onAccountIdChange}
            options={accounts.map(item => ({
              value: item.id,
              label: `${item.name} · ${roleName(item.role)} · ${item.company_id === 'alpha' ? '华东数智' : '远山信息'}`,
            }))}
          />
          <Button
            type="primary"
            block
            size="large"
            onClick={onLogin}
            loading={busy}
            disabled={!accounts.length}
            style={{ marginTop: 24 }}
          >
            进入工作台
          </Button>
        </Card>
      </section>
    </div>
  );
}
