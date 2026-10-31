// 为什么有这个文件：编辑台里系统生成章节的状态与操作（APP-M2-T191～T195、T127 预览）。
// 它解决什么问题：正文不能手改；显示是否已生成、数据源是否已变化、还有几处【待补】，并一键按数据源重新生成。
import { useEffect, useState } from 'react';
import { Alert, Button, Space, Tag } from 'antd';
import { useProject } from '../app/context.tsx';
import { request } from '../shared/api.ts';
import { SOURCE_TAB, systemPaths } from './system-chapter-core.ts';

type Preview = { kind: string; label: string; gaps: string[]; generated: boolean; stale: boolean; generated_at?: string | null };

export function SystemChapterPanel({ chapterId, canGenerate }: { chapterId: string; canGenerate: boolean }) {
  const { workspace, token, busy, mutate, navigate, report } = useProject();
  const [preview, setPreview] = useState<Preview | null>(null);
  useEffect(() => {
    request<Preview>(systemPaths.preview(workspace.project.id, chapterId), token).then(setPreview).catch(report);
  }, [chapterId, workspace.revision, token]);
  if (!preview) return null;
  const state = !preview.generated ? { color: 'default', text: '尚未生成' } : preview.stale ? { color: 'gold', text: '数据源已变化，需重新生成' } : { color: 'green', text: '与数据源一致' };
  return (
    <Alert
      type={preview.stale ? 'warning' : 'info'}
      showIcon
      data-testid="system-chapter-panel"
      style={{ marginBottom: 12 }}
      message={<Space wrap>系统生成的{preview.label}<Tag color={state.color}>{state.text}</Tag>{preview.gaps.length > 0 && <Tag color="orange">【待补】{preview.gaps.length} 处</Tag>}</Space>}
      description="本节内容由响应矩阵、项目事实与资料库生成，不调用模型，不能在正文中修改；要改内容，请回到数据源修改后重新生成。"
      action={
        <Space direction="vertical">
          <Button size="small" type="primary" data-testid="system-chapter-generate" disabled={!canGenerate || busy}
            onClick={() => { void mutate(systemPaths.generate(workspace.project.id, chapterId), 'POST', {}).catch(() => undefined); }}>
            {preview.generated ? '重新生成' : '按数据源生成'}
          </Button>
          <Button size="small" onClick={() => navigate(SOURCE_TAB[preview.kind] ?? 'matrix')}>去数据源修改</Button>
        </Space>
      }
    />
  );
}
