// 为什么有这个文件：账号密码登录页。
// 它解决什么问题：只提供正式账号密码登录；不预填、不内置任何账号口令，不提供令牌直登入口。

import React, { useState } from 'react';
import { Alert, Button, Card, Input } from 'antd';
import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { validateLoginForm, formatLoginErrorMessage } from './login-auth-core.ts';

export interface LoginScreenProps {
  onPasswordLogin: (username: string, password: string) => Promise<void> | void;
  busy?: boolean;
  errorMessage?: string | null;
}

export function LoginScreen({ onPasswordLogin, busy = false, errorMessage: externalError = null }: LoginScreenProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const displayError = localError || externalError;
  const isLoading = busy || submitting;

  const handlePasswordSubmit = async () => {
    setLocalError(null);
    const validation = validateLoginForm({ username, password });
    if (!validation.valid) {
      setLocalError(validation.message || '请填写完整的登录信息');
      return;
    }
    setSubmitting(true);
    try {
      await onPasswordLogin(username.trim(), password);
    } catch (err: unknown) {
      setLocalError(formatLoginErrorMessage(err));
    } finally {
      setSubmitting(false);
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
        <Card className="login-card" title="欢迎登录工作台">
          {displayError && (
            <Alert
              type="error"
              showIcon
              closable
              message={displayError}
              onClose={() => setLocalError(null)}
              style={{ marginBottom: 16 }}
              data-testid="login-error-alert"
            />
          )}

            <div className="login-form" style={{ paddingTop: 8 }}>
              <div style={{ marginBottom: 16 }}>
                <Input
                  prefix={<UserOutlined style={{ color: '#8c8c8c' }} />}
                  placeholder="请输入用户名 / 账号"
                  value={username}
                  onChange={e => {
                    setUsername(e.target.value);
                    if (localError) setLocalError(null);
                  }}
                  onPressEnter={handlePasswordSubmit}
                  size="large"
                  disabled={isLoading}
                  autoComplete="username"
                  data-testid="login-username-input"
                />
              </div>

              <div style={{ marginBottom: 20 }}>
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#8c8c8c' }} />}
                  placeholder="请输入登录密码"
                  value={password}
                  onChange={e => {
                    setPassword(e.target.value);
                    if (localError) setLocalError(null);
                  }}
                  onPressEnter={handlePasswordSubmit}
                  size="large"
                  disabled={isLoading}
                  autoComplete="current-password"
                  data-testid="login-password-input"
                />
              </div>

              <Button
                type="primary"
                block
                size="large"
                onClick={handlePasswordSubmit}
                loading={isLoading}
                style={{ height: 44, fontSize: 16, fontWeight: 500 }}
                data-testid="login-submit-button"
              >
                登 录
              </Button>

            </div>
        </Card>
      </section>
    </div>
  );
}
