// 为什么有这个文件：章节循环进度页（APP-M2-T130）与轮次时间线抽屉（APP-M2-T131）。
// 它解决什么问题：负责人一眼看到每章“生成→检查→定位修正→复查”停在哪一轮、为什么停、还剩几项；
// 点开一章可逐轮查看查出什么、谁修了哪段、用的模型与实际输入、版本变化以及前章摘要是否缺失。
import { useCallback, useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Descriptions, Drawer, Empty, Progress, Segmented, Space, Spin, Table, Tag, Timeline, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { formatTime, useProject, volumeName } from '../app/context.tsx';
import { editorChapterPath } from '../app/app-route.ts';
import type { ChapterLoopDetail, ChapterLoopList, ChapterLoopRow, Volume } from '../shared/types.ts';
import { queuePaths } from './main-path-core.ts';
import { projectVolumes, technicalOnly, volumeOptions } from './project-volumes.ts';
import {
  fetchChapterLoop, fetchChapterLoops, loopStatus, metaLines, progressPercent, relayNotice, roundColor, roundSummary, timelineLoops,
} from './chapter-loop-core.ts';

export function ChapterLoopPage() {
  const { workspace, token, busy, mutate, navigate, report } = useProject();
  const projectId = workspace.project.id;
  const [volume, setVolume] = useState<Volume | 'all'>('all');
  const [list, setList] = useState<ChapterLoopList | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const sequence = useRef(0);

  // 只采纳最近一次请求的回包：较早发出、较晚到达的旧列表不能覆盖重新检查后的新状态。
  const load = useCallback(async () => {
    const ticket = ++sequence.current;
    setLoading(true);
    try {
      const next = await fetchChapterLoops(projectId, token, volume);
      if (ticket !== sequence.current) return;
      setList(next);
      setFailed(null);
    } catch (error) {
      if (ticket !== sequence.current) return;
      setFailed(error instanceof Error ? error.message : '读取章节循环进度失败');
      report(error);
    } finally {
      if (ticket === sequence.current) setLoading(false);
    }
  }, [projectId, token, volume, report]);
  useEffect(() => { void load(); }, [load, workspace.revision]);

  async function recheck(row: ChapterLoopRow) {
    try {
      await mutate(queuePaths.recheck(projectId, row.chapter_id), 'POST', {});
    } catch {
      /* 错误已提示；列表随项目版本刷新 */
    }
  }

  const totals = list?.totals;
  return (
    <>
      <div className="page-heading">
        <div>
          <h3>章节循环进度</h3>
          <Space size={16} wrap>
            <span>章节 <b>{totals?.chapters ?? 0}</b></span>
            <span>已完成 <b className="green">{totals?.completed ?? 0}</b></span>
            <span>待人工 <b className={totals?.pending_human ? 'red' : ''}>{totals?.pending_human ?? 0}</b></span>
            <span>人工已处理 <b>{totals?.human_handled ?? 0}</b></span>
            <span>未开始 <b>{totals?.not_started ?? 0}</b></span>
            {!!totals?.stale && <Tag color="gold">正文改动待复查 {totals.stale}</Tag>}
            <Progress percent={progressPercent(totals)} size="small" style={{ width: 160 }} />
          </Space>
        </div>
        <Space>
          <Segmented
            value={volume}
            onChange={value => setVolume(value as Volume | 'all')}
            options={volumeOptions(workspace, true)}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void load()} loading={loading}>刷新</Button>
        </Space>
      </div>
      {failed && (
        <Alert type="error" showIcon className="stack-card" message="章节循环进度读取失败" description={failed}
          action={<Button size="small" onClick={() => void load()}>重试</Button>} />
      )}
      <Spin spinning={loading && !list}>
        {list && !list.chapters.length ? (
          <Card><Empty description="本项目还没有章节，先在大纲中建立章节" /></Card>
        ) : (
          <Table<ChapterLoopRow>
            data-testid="chapter-loop-table"
            rowKey="chapter_id"
            size="middle"
            pagination={false}
            dataSource={list?.chapters ?? []}
            columns={[
              { title: '章节', key: 'title', render: (_, row) => <Space direction="vertical" size={0}><b>{row.number} {row.title}</b><span className="muted">{volumeName(row.volume)} · {row.assignee_name ?? '未分配负责人'}</span></Space> },
              { title: '状态', key: 'status', width: 150, render: (_, row) => { const tag = loopStatus(row); return <Tag color={tag.color}>{tag.label}</Tag>; } },
              { title: '最近一次循环', key: 'loop', render: (_, row) => row.loop
                ? <span>第 {row.loop.loop_count} 次 · {row.loop.rounds.length}/{row.loop.max_rounds} 轮 · {row.loop.stop_reason_label}{row.loop.rolled_back ? ' · 已回退' : ''}</span>
                : <span className="muted">{row.has_content ? '有正文，尚未检查' : '尚未生成正文'}</span> },
              { title: '待处理', key: 'pending', width: 90, render: (_, row) => <b className={row.pending ? 'red' : ''}>{row.pending}</b> },
              { title: '操作', key: 'actions', width: 260, render: (_, row) => (
                <Space size={4} wrap>
                  <Button type="link" size="small" disabled={!row.loop} onClick={() => setOpenId(row.chapter_id)}>轮次时间线</Button>
                  <Tooltip title={row.can_recheck ? '' : row.volume_finalized ? '分册已定稿，须先解锁' : !row.has_content ? '本节还没有正文' : '只有本节负责人或项目负责人可以重新检查'}>
                    <Button size="small" disabled={busy || !row.can_recheck} onClick={() => void recheck(row)}>重新检查</Button>
                  </Tooltip>
                  {row.pending > 0 && <Button type="link" size="small" onClick={() => navigate(editorChapterPath(projectId, row.chapter_id))}>去编辑台</Button>}
                </Space>
              ) },
            ]}
          />
        )}
      </Spin>
      <ChapterLoopTimeline projectId={projectId} token={token} chapterId={openId} revision={workspace.revision} onClose={() => setOpenId(null)} />
    </>
  );
}

function ChapterLoopTimeline({ projectId, token, chapterId, revision, onClose }: {
  projectId: string; token: string; chapterId: string | null; revision: number; onClose: () => void;
}) {
  const [detail, setDetail] = useState<ChapterLoopDetail | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const sequence = useRef(0);

  const load = useCallback(async () => {
    const ticket = ++sequence.current;
    if (!chapterId) return;
    setLoading(true);
    try {
      const next = await fetchChapterLoop(projectId, token, chapterId);
      if (ticket !== sequence.current) return;
      setDetail(next);
      setFailed(null);
    } catch (error) {
      if (ticket !== sequence.current) return;
      setFailed(error instanceof Error ? error.message : '读取轮次时间线失败');
    } finally {
      if (ticket === sequence.current) setLoading(false);
    }
  }, [projectId, token, chapterId]);
  useEffect(() => { setDetail(null); void load(); }, [load, revision]);

  const loops = detail ? timelineLoops(detail) : [];
  return (
    <Drawer open={!!chapterId} onClose={onClose} width={640} title={detail ? `轮次时间线 · ${detail.title}` : '轮次时间线'} destroyOnClose>
      {failed && <Alert type="error" showIcon message="读取失败" description={failed} action={<Button size="small" onClick={() => void load()}>重试</Button>} />}
      <Spin spinning={loading}>
        {detail && !loops.length && <Empty description="本节还没有运行过章节循环" />}
        {detail && !!loops.length && (
          <Space direction="vertical" style={{ width: '100%' }} size={16} data-testid="chapter-loop-timeline">
            <Space wrap>
              <Tag>待处理 {detail.counts.pending_human + detail.counts.pending_fix}</Tag>
              <Tag color="green">已解决 {detail.counts.resolved}</Tag>
              <Tag color="blue">人工已处理 {detail.counts.human_handled}</Tag>
              <Tag>已驳回 {detail.counts.rejected}</Tag>
            </Space>
            {loops.map(loop => {
              const notice = relayNotice(loop.meta);
              return (
                <Card key={loop.loop_no} size="small" data-testid="chapter-loop-entry"
                  title={<Space wrap><b>第 {loop.loop_no} 次循环</b><Tag>{loop.kind_label}</Tag>{loop.current && <Tag color="processing">最近一次</Tag>}</Space>}
                  extra={<span className="muted">{formatTime(loop.started_at)}</span>}>
                  <Descriptions size="small" column={1} items={metaLines(loop.meta, loop).map(line => ({ key: line.label, label: line.label, children: line.value }))} />
                  {notice && <Alert className="stack-card" type={notice.type} showIcon message={notice.text} />}
                  <Timeline
                    items={loop.rounds.map((round, index) => ({
                      color: roundColor(round, index === loop.rounds.length - 1, loop),
                      children: (
                        <div data-testid="chapter-loop-round">
                          <b>第 {round.round} 轮</b>：{roundSummary(round)}
                          <div className="muted">{round.conclusion}</div>
                        </div>
                      ),
                    }))}
                  />
                  <div className="muted">停止原因：{loop.stop_reason_label}{loop.rolled_back ? '（已回退到修正前版本）' : ''}</div>
                </Card>
              );
            })}
          </Space>
        )}
      </Spin>
    </Drawer>
  );
}
