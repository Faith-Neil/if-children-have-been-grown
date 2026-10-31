// 为什么有这个文件：首次登录或密码被重置后的强制改密页（APP-M2-T260 / PRD v1.8 §5.12.1 操作）。
// 它解决什么问题：改密前不进入系统；新密码输入两次，页面显示当前适用的规则并就近提示缺少哪一项；服务端仍会再核一次。

import React, { useState } from 'react';
import { Alert, Button, Card, Input } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { ApiError } from '../shared/api.ts';
import { changeOwnPassword, type PasswordPolicy } from './login-auth-core.ts';
import { checkPasswordChange, DEFAULT_POLICY, passwordProblems, policyText } from './password-change-core.ts';

export interface PasswordChangeScreenProps {
  token: string;
  username: string;
  policy: PasswordPolicy | null;
  productName?: string;
  onChanged: () => Promise<void> | void;
  onCancel: () => void;
}

export function PasswordChangeScreen({ token, username, policy, productName = '智能投标系统', onChanged, onCancel }: PasswordChangeScreenProps) {
  const rules = policy ?? DEFAULT_POLICY;
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [problems, setProblems] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const live = newPassword ? passwordProblems(newPassword, rules) : [];

  async function submit() {
    setError(null);
    const check = checkPasswordChange({ oldPassword, newPassword, confirmPassword }, rules);
    if (!check.ok) { setProblems(check.problems); return; }
    setProblems([]);
    setSubmitting(true);
    try {
      await changeOwnPassword(token, oldPassword, newPassword);
      await onChanged();
    } catch (err) {
      const listed = err instanceof ApiError ? err.details?.problems : undefined;
      if (Array.isArray(listed)) setProblems(listed.map(String));
      else setError(err instanceof Error ? err.message : '修改密码失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  }

  const shown = problems.length ? problems : live;
  return (
    <div className="login-screen">
      <section className="login-brand">
        <div className="brand-square">标</div>
        <h1>{productName}</h1>
      </section>
      <section className="login-main">
        <Card className="login-card" title="设置新密码" data-testid="password-change-card">
          <Alert type="info" showIcon message={`${username} 首次登录或密码已被重置，修改密码后进入系统`}
            description={policyText(rules)} style={{ marginBottom: 16 }} data-testid="password-policy-text" />
          {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} data-testid="password-change-error" />}
          <div style={{ display: 'grid', gap: 12 }}>
            <Input.Password prefix={<LockOutlined />} placeholder="当前密码" value={oldPassword} size="large"
              autoComplete="current-password" onChange={e => setOldPassword(e.target.value)} disabled={submitting}
              data-testid="password-old-input" />
            <Input.Password prefix={<LockOutlined />} placeholder="新密码" value={newPassword} size="large"
              autoComplete="new-password" onChange={e => { setNewPassword(e.target.value); setProblems([]); }} disabled={submitting}
              status={shown.length && newPassword ? 'warning' : undefined} data-testid="password-new-input" />
            {shown.length > 0 && (
              <ul className="password-problems" data-testid="password-problems" style={{ margin: 0, paddingLeft: 20, color: '#d46b08' }}>
                {shown.map(item => <li key={item}>{item}</li>)}
              </ul>
            )}
            <Input.Password prefix={<LockOutlined />} placeholder="再次输入新密码" value={confirmPassword} size="large"
              autoComplete="new-password" onChange={e => setConfirmPassword(e.target.value)} onPressEnter={submit}
              disabled={submitting} data-testid="password-confirm-input" />
            <Button type="primary" block size="large" loading={submitting} onClick={submit} data-testid="password-change-submit">
              修改密码并进入
            </Button>
            <Button type="link" onClick={onCancel} disabled={submitting} data-testid="password-change-cancel">退出登录</Button>
          </div>
        </Card>
      </section>
    </div>
  );
}
