// 为什么有这个文件：技术目录模型编排失败时的专用告警与「重新生成目录」入口。
// 它解决什么问题：
// 1. 规则兜底目录不再伪装成可用模型目录——失败原因以错误级告警驻留显示，不用瞬时气泡；
// 2. 重跑走后端既有 rebuild-model 契约，HTTP 200 也可能仍是失败态，按响应如实反馈；
// 3. 重跑成功后回调编辑台刷新章节与指纹，失败时错误提示保留到下一次尝试。

import React, { useEffect, useRef, useState } from 'react';
import { Alert, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useProject } from '../app/context.tsx';
import { request, userFacingMessage } from '../shared/api.ts';
import {
  canRebuildOutlineModel,
  outlineFailureState,
  runOutlineRebuild,
} from './outline-rebuild-core.ts';

export function OutlineRebuildNotice({ onRebuilt, disabled }: { onRebuilt?: () => void; disabled?: boolean }) {
  const { workspace, token, user, busy, reload, report } = useProject();
  const [running, setRunning] = useState(false);
  const [lastError, setLastError] = useState('');
  // 重跑跨多次渲染才结束：回调必须取最新一版渲染闭包，里面的 dirty/章节状态才是当前值。
  const callbackRef = useRef(onRebuilt);
  useEffect(() => { callbackRef.current = onRebuilt; }, [onRebuilt]);

  const failure = outlineFailureState(workspace);
  if (!failure.failed) return null;

  const allowed = canRebuildOutlineModel(user, workspace.project.company_id);

  async function rebuild() {
    if (running) return;
    setRunning(true);
    setLastError('');
    try {
      const outcome = await runOutlineRebuild(workspace.project.id, {
        post: path => request(path, token, 'POST', {}),
        reload: async () => { await reload(); },
        errorMessage: userFacingMessage,
      });
      if (outcome.kind === 'success') {
        if (outcome.reloaded) {
          callbackRef.current?.();
        } else {
          setLastError('目录已重新生成，但页面没有刷到最新状态；请刷新浏览器核对。');
        }
      } else {
        if (outcome.kind === 'error' && outcome.error) report(outcome.error);
        setLastError(outcome.message);
      }
    } finally {
      setRunning(false);
    }
  }

  const detail = [failure.reason, lastError].filter((part, index, parts) => part && parts.indexOf(part) === index).join(' ');

  return (
    <Alert
      className="editor-notice"
      type="error"
      showIcon
      data-testid="outline-model-failed"
      message="目录模型编排失败"
      description={`${detail}${allowed ? '' : ' 需要公司管理员或平台管理员重跑模型目录。'}`}
      action={allowed ? (
        <Button
          size="small"
          type="primary"
          icon={<ReloadOutlined />}
          loading={running}
          disabled={running || busy || !!disabled}
          onClick={() => void rebuild()}
          data-testid="outline-rebuild-button"
        >
          重新生成目录
        </Button>
      ) : undefined}
    />
  );
}
