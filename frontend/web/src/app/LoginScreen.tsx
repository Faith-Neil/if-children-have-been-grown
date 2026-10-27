// 为什么有这个文件：生产环境正式账号密码登录屏界面，支持超级管理员与正式账号登录。
// 它解决什么问题：贯彻 Layout First 原则，移除冗余 demo 切换 Tab 与说明书文案，提供现代企业级账号密码卡片、即时校验、错误 Banner 与令牌直登扩展槽。

import React, { useState } from 'react';
import { Alert, Button, Card, Input } from 'antd';
import { LockOutlined, UserOutlined, KeyOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import type { Account } from '../shared/types.ts';
import {
  DEFAULT_SUPERADMIN_USER,
  DEFAULT_SUPERADMIN_PASSWORD,
  validateLoginForm,
  authenticateUser,
  formatLoginErrorMessage,
} from './login-auth-core.ts';

export interface LoginScreenProps {
  onPasswordLogin?: (username: string, password: string) => Promise<void> | void;
  onTokenLogin?: (token: string) => Promise<void> | void;
  busy?: boolean;
  errorMessage?: string | null;
  // 保持与现有 App.tsx 签名的向前兼容字段
  accounts?: Account[];
  accountId?: string;
  onAccountIdChange?: (id: string) => void;
  onLogin?: () => void;
}

export function LoginScreen({
  onPasswordLogin,
  onTokenLogin,
  busy = false,
  errorMessage: externalError = null,
  // 兼容参数
  accounts = [],
  accountId,
  onAccountIdChange,
  onLogin,
}: LoginScreenProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  // 令牌扩展槽显示模式（自动化测试/SSO场景）
  const [tokenMode, setTokenMode] = useState(false);
  const [customToken, setCustomToken] = useState('');

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
      if (onPasswordLogin) {
        await onPasswordLogin(username.trim(), password);
      } else if (onTokenLogin) {
        const token = await authenticateUser(username.trim(), password);
        await onTokenLogin(token);
      } else if (onLogin) {
        onLogin();
      }
    } catch (err: unknown) {
      setLocalError(formatLoginErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleTokenSubmit = async () => {
    setLocalError(null);
    if (!customToken.trim()) {
      setLocalError('请输入会话 Token 或授权密钥');
      return;
    }
    if (onTokenLogin) {
      setSubmitting(true);
      try {
        await onTokenLogin(customToken.trim());
      } catch (err: unknown) {
        setLocalError(formatLoginErrorMessage(err));
      } finally {
        setSubmitting(false);
      }
    }
  };

  const fillSuperAdmin = () => {
    setUsername(DEFAULT_SUPERADMIN_USER);
    setPassword(DEFAULT_SUPERADMIN_PASSWORD);
    setLocalError(null);
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

          {!tokenMode ? (
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

              <div
                style={{
                  marginTop: 16,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontSize: 13,
                }}
              >
                <a
                  onClick={fillSuperAdmin}
                  style={{ color: '#1677ff', cursor: 'pointer' }}
                  data-testid="login-superadmin-shortcut"
                >
                  填入超级管理员 (admin)
                </a>
                {onTokenLogin && (
                  <a
                    onClick={() => {
                      setTokenMode(true);
                      setLocalError(null);
                    }}
                    style={{ color: '#8c8c8c', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
                    data-testid="login-token-toggle"
                  >
                    <KeyOutlined /> 凭据令牌登录
                  </a>
                )}
              </div>
            </div>
          ) : (
            <div className="token-form" style={{ paddingTop: 8 }}>
              <div style={{ marginBottom: 20 }}>
                <Input
                  prefix={<KeyOutlined style={{ color: '#8c8c8c' }} />}
                  placeholder="输入会话 Token 或授权密钥"
                  value={customToken}
                  onChange={e => {
                    setCustomToken(e.target.value);
                    if (localError) setLocalError(null);
                  }}
                  onPressEnter={handleTokenSubmit}
                  size="large"
                  disabled={isLoading}
                  data-testid="login-token-input"
                />
              </div>

              <Button
                type="primary"
                block
                size="large"
                onClick={handleTokenSubmit}
                loading={isLoading}
                disabled={!customToken.trim()}
                style={{ height: 44, fontSize: 16, fontWeight: 500 }}
                data-testid="login-token-submit-button"
              >
                进入工作台
              </Button>

              <div style={{ marginTop: 16, textAlign: 'center' }}>
                <a
                  onClick={() => {
                    setTokenMode(false);
                    setLocalError(null);
                  }}
                  style={{ color: '#1677ff', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}
                  data-testid="login-password-toggle"
                >
                  <ArrowLeftOutlined /> 返回账号密码登录
                </a>
              </div>
            </div>
          )}
        </Card>
      </section>
    </div>
  );
}
