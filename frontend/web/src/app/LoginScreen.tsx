// 为什么有这个文件：提取 App.tsx 登录屏界面，降低应用编排主文件行数。
// 它解决什么问题：解耦登录 UI 渲染与全局状态机，支持合成账号与真实凭据登录，落实 Layout First 去说明化。

import React, { useState, useEffect } from 'react';
import { Button, Card, Input, Select, Tabs } from 'antd';
import type { Account } from '../shared/types.ts';
import { roleName } from './context.tsx';
import { isDemoMode } from '../shared/roles.ts';

export interface LoginScreenProps {
  accounts: Account[];
  accountId: string;
  onAccountIdChange: (id: string) => void;
  onLogin: () => void;
  busy: boolean;
  onTokenLogin?: (token: string) => void;
}

export function LoginScreen({
  accounts,
  accountId,
  onAccountIdChange,
  onLogin,
  busy,
  onTokenLogin,
}: LoginScreenProps) {
  const demoEnabled = isDemoMode() && accounts.length > 0;
  const [loginTab, setLoginTab] = useState<'demo' | 'credential'>(demoEnabled ? 'demo' : 'credential');
  const [customToken, setCustomToken] = useState('');

  useEffect(() => {
    if (demoEnabled) {
      setLoginTab('demo');
    }
  }, [demoEnabled]);

  const handleCredentialSubmit = () => {
    if (customToken.trim() && onTokenLogin) {
      onTokenLogin(customToken.trim());
    }
  };

  return (
    <div className="login-screen">
      <section className="login-brand">
        <div className="brand-square">标</div>
        <h1>智能投标系统</h1>
        <p>让原文、证据和正文在同一处对齐</p>
        <div className="login-foot">
          ICG · 生产级投标工作台
        </div>
      </section>
      <section className="login-main">
        <Card className="login-card" title="欢迎进入工作台">
          {demoEnabled ? (
            <Tabs
              activeKey={loginTab}
              onChange={key => setLoginTab(key as 'demo' | 'credential')}
              items={[
                {
                  key: 'demo',
                  label: '体验账号',
                  children: (
                    <div style={{ paddingTop: 8 }}>
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
                    </div>
                  ),
                },
                {
                  key: 'credential',
                  label: '账号凭据',
                  children: (
                    <div style={{ paddingTop: 8 }}>
                      <Input
                        placeholder="输入会话 Token"
                        value={customToken}
                        onChange={e => setCustomToken(e.target.value)}
                        onPressEnter={handleCredentialSubmit}
                        size="large"
                        style={{ width: '100%' }}
                      />
                      <Button
                        type="primary"
                        block
                        size="large"
                        onClick={handleCredentialSubmit}
                        loading={busy}
                        disabled={!customToken.trim()}
                        style={{ marginTop: 24 }}
                      >
                        凭据登录
                      </Button>
                    </div>
                  ),
                },
              ]}
            />
          ) : (
            <div style={{ paddingTop: 8 }}>
              <Input
                placeholder="输入会话 Token 或授权密钥"
                value={customToken}
                onChange={e => setCustomToken(e.target.value)}
                onPressEnter={handleCredentialSubmit}
                size="large"
                style={{ width: '100%' }}
              />
              <Button
                type="primary"
                block
                size="large"
                onClick={handleCredentialSubmit}
                loading={busy}
                disabled={!customToken.trim()}
                style={{ marginTop: 24 }}
              >
                进入工作台
              </Button>
            </div>
          )}
        </Card>
      </section>
    </div>
  );
}
