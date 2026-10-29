// 为什么有这个文件：顶栏铃铛（PRD v1.8 §5.12.2；APP-M2-T029、T030）。
// 它解决什么问题：徽标显示本人未读数（超过 99 显示 99+，每分钟刷新）；点开下拉显示最近 7 条，点击跳到对象并标已读，
// 可逐条标已读或全部标已读；“查看全部”进入站内提醒列表页。
import React, { useEffect, useState } from 'react';
import { App as AntApp, Badge, Button, Empty, List, Popover, Space, Tag } from 'antd';
import { BellOutlined } from '@ant-design/icons';
import { request } from '../shared/api.ts';
import { formatTime } from '../app/context';
import { DROPDOWN_SIZE, NOT_AVAILABLE, POLL_MS, badgeText, listPath, mergedNote, notificationPaths, safeTarget,
  type NotificationList, type OpenResult } from './notifications-core.ts';

export function NotificationBell({ token, onNavigate }: { token: string | null; onNavigate: (path: string) => void }) {
  const { message } = AntApp.useApp();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [list, setList] = useState<NotificationList | null>(null);

  async function refreshCount() {
    if (!token) return;
    try { setUnread((await request<{ unread: number }>(notificationPaths.unread, token)).unread); } catch { /* 下次轮询再试 */ }
  }
  async function refreshList() {
    if (!token) return;
    const value = await request<NotificationList>(listPath({ status: 'all' }, DROPDOWN_SIZE), token);
    setList(value); setUnread(value.unread);
  }

  useEffect(() => {
    void refreshCount();
    const timer = window.setInterval(() => { void refreshCount(); }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [token]);
  useEffect(() => { if (open) refreshList().catch(() => undefined); }, [open]);

  async function openItem(id: string) {
    if (!token) return;
    const result = await request<OpenResult>(notificationPaths.open(id), token, 'POST');
    await refreshList().catch(() => undefined);
    const target = safeTarget(result);
    if (target) { setOpen(false); onNavigate(target); } else message.warning(result.message || NOT_AVAILABLE);
  }

  const content = (
    <div className="notice-dropdown" data-testid="notification-dropdown">
      <List
        size="small"
        dataSource={list?.items ?? []}
        locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有提醒" /> }}
        renderItem={item => (
          <List.Item className={item.read ? 'read' : 'unread'} data-testid="notification-item"
            actions={item.read ? [] : [<a key="read" onClick={async () => { await request(notificationPaths.read(item.id), token, 'POST', { read: true }); await refreshList(); }}>标为已读</a>]}>
            <a onClick={() => void openItem(item.id)} className="notice-link">
              <Space size={4}><Tag>{item.type_label}</Tag>{!item.read && <Badge status="processing" />}<b>{item.title}</b></Space>
              <div className="muted">{item.body}{mergedNote(item)}</div>
              <div className="muted">{formatTime(item.updated_at)}</div>
            </a>
          </List.Item>
        )}
      />
      <div className="notice-dropdown-foot">
        <Button size="small" type="link" disabled={!unread} data-testid="notification-read-all"
          onClick={async () => { await request(notificationPaths.readAll, token, 'POST'); await refreshList(); }}>全部标为已读</Button>
        <Button size="small" type="link" data-testid="notification-view-all" onClick={() => { setOpen(false); onNavigate('/notifications'); }}>查看全部</Button>
      </div>
    </div>
  );

  return (
    <Popover trigger="click" placement="bottomRight" open={open} onOpenChange={setOpen} content={content} title="站内提醒">
      <Badge count={badgeText(unread)} size="small" offset={[-4, 4]} data-testid="notification-badge">
        <Button type="text" icon={<BellOutlined />} aria-label={unread ? `站内提醒，${badgeText(unread)} 条未读` : '站内提醒'} data-testid="notification-bell" />
      </Badge>
    </Popover>
  );
}
