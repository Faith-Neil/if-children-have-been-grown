// 为什么有这个文件：提取招标文件原文预览卡片组件（OriginalPreview）。
// 它解决什么问题：解耦招标文件解析预览、翻页、条款引用高亮与原件安全下载，提高模块复用性。
// PDF 默认显示原件本身并在原件上高亮条款原句（APP-M2-T103），可切换到识别文字对照。

import React, { useEffect, useRef, useState } from 'react';
import { Button, Empty, Select, Tooltip } from 'antd';
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { download, request } from '../shared/api.ts';
import { paginationName, useProject } from '../app/context.tsx';
import type { Preview, Source } from '../shared/types.ts';

function markQuote(line: string, quote: string) {
  if (!quote || !line.includes(quote)) return line;
  const index = line.indexOf(quote);
  return <>{line.slice(0, index)}<mark>{quote}</mark>{line.slice(index + quote.length)}</>;
}

function DocumentHtml({ text, quote }: { text: string; quote: string }) {
  const lines = text.split(/\n+/).map(line => line.trim()).filter(Boolean);
  if (!lines.length) return <p>这一页没有识别出文字。</p>;
  const blocks: React.ReactNode[] = [];
  let table: string[][] = [];
  function flushTable() {
    if (!table.length) return;
    const rows = table;
    table = [];
    blocks.push(
      <table key={`t-${blocks.length}`}>
        <tbody>
          {rows.map((cells, rowIndex) => (
            <tr key={rowIndex}>{cells.map((cell, cellIndex) => <td key={cellIndex}>{markQuote(cell, quote)}</td>)}</tr>
          ))}
        </tbody>
      </table>,
    );
  }
  lines.forEach(line => {
    if (line.includes('|') && line.split('|').filter(Boolean).length >= 2) {
      table.push(line.split('|').map(cell => cell.trim()).filter(Boolean));
      return;
    }
    flushTable();
    const heading = line.length <= 48 && /^(第[0-9一二三四五六七八九十百]+[章节篇条]|[0-9]+(?:\.[0-9]+){0,3}[\s.、])/.test(line);
    const body = markQuote(line, quote);
    blocks.push(heading ? <h3 key={blocks.length}>{body}</h3> : <p key={blocks.length}>{body}</p>);
  });
  flushTable();
  return <>{blocks}</>;
}

export interface OriginalPreviewProps {
  source: Source | null;
}

export function OriginalPreview({ source }: OriginalPreviewProps) {
  const { workspace, token, report } = useProject();
  const [preview, setPreview] = useState<Preview | null>(null);
  const [fileId, setFileId] = useState(source?.file_id || workspace.files[0]?.id || '');
  const [page, setPage] = useState(source?.page || 1);
  const paperRef = useRef<HTMLDivElement>(null);
  const requestEpoch = useRef(0);

  useEffect(() => {
    if (source) {
      setFileId(source.file_id);
      setPage(source.page);
    }
  }, [source]);

  useEffect(() => {
    const epoch = ++requestEpoch.current;
    setPreview(null);
    if (!fileId) return;
    request<Preview>(`/api/v1/projects/${workspace.project.id}/files/${fileId}/preview`, token)
      .then(data => {
        if (epoch === requestEpoch.current) setPreview(data);
      })
      .catch(error => {
        if (epoch === requestEpoch.current && error.code !== 'FILE_NOT_PARSED') report(error);
      });
  }, [fileId, workspace.project.id, workspace.files.find(file => file.id === fileId)?.status]);

  const quote = source?.file_id === fileId ? source.quote : '';
  const file = workspace.files.find(item => item.id === fileId);
  const pages = preview?.pages ?? [];
  const pageOptions = pages.length ? pages.map(item => item.page) : [1];

  useEffect(() => {
    const root = paperRef.current;
    const target = root?.querySelector<HTMLElement>(`#doc-page-${page}`);
    if (!root || !target) return;
    root.scrollTo({ top: Math.max(0, target.offsetTop - 12) });
  }, [page, preview?.filename]);

  return (
    <div className="original-preview">
      <div className="original-toolbar">
        <FileTextOutlined />
        <Select
          aria-label="原文文件"
          size="small"
          value={fileId || undefined}
          onChange={value => {
            setFileId(value);
            setPage(1);
          }}
          options={workspace.files.map(item => ({ value: item.id, label: item.filename }))}
        />
        <Select
          aria-label="原文页码"
          size="small"
          value={page}
          onChange={setPage}
          options={pageOptions.map(value => ({ value, label: `第 ${value} 页` }))}
        />
        {file && (
          <Tooltip title="下载实际上传原件">
            <Button
              size="small"
              type="text"
              icon={<DownloadOutlined />}
              aria-label="下载原文"
              onClick={() => download(file.download_url, token, file.filename).catch(report)}
            />
          </Tooltip>
        )}
      </div>
      <div className="paper-wrap" ref={paperRef}>
        {preview && pages.length ? (
          pages.map(item => (
            <article key={item.page} id={`doc-page-${item.page}`} className={`original-paper${item.page === page ? ' is-current' : ''}`}>
              <DocumentHtml text={item.text} quote={item.page === source?.page && source?.file_id === fileId ? quote : ''} />
            </article>
          ))
        ) : (
          <Empty description={file ? '请先解析文件，再查看原文与条款位置' : '还没有上传招标文件'} />
        )}
      </div>
      {preview && (
        <div className="original-foot">
          第 {page} 页 / 共 {pages.length || 1} 页 · {paginationName(preview.pagination)}
          {preview.warnings.length > 0 && ` · ${preview.warnings.join('；')}`}
        </div>
      )}
    </div>
  );
}
