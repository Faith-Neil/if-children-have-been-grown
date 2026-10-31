// 为什么有这个文件：提取招标文件原文预览卡片组件（OriginalPreview）。
// 它解决什么问题：解耦招标文件解析预览、翻页、条款引用高亮与原件安全下载，提高模块复用性。
// PDF 默认显示原件本身并在原件上高亮条款原句（APP-M2-T103），可切换到识别文字对照。

import React, { useEffect, useRef, useState } from 'react';
import { Button, Empty, Segmented, Select, Tooltip } from 'antd';
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons';
import { download, request } from '../shared/api.ts';
import { paginationName, useProject } from '../app/context.tsx';
import type { Preview, Source } from '../shared/types.ts';
import { PdfLocator } from './PdfLocator.tsx';
import { isPdf, type TextRegion } from './pdf-locator-core.ts';

const NO_REGIONS: TextRegion[] = [];
type ViewMode = 'original' | 'text';

export interface OriginalPreviewProps {
  source: Source | null;
}

export function OriginalPreview({ source }: OriginalPreviewProps) {
  const { workspace, token, report } = useProject();
  const [preview, setPreview] = useState<Preview | null>(null);
  const [fileId, setFileId] = useState(source?.file_id || workspace.files[0]?.id || '');
  const [page, setPage] = useState(source?.page || 1);
  const [mode, setMode] = useState<ViewMode>('original');
  const [pdfPages, setPdfPages] = useState(0);
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

  const originalText = preview?.pages.find(item => item.page === page)?.text ?? '';
  const quote = source?.file_id === fileId && source.page === page ? source.quote : '';
  const index = quote ? originalText.indexOf(quote) : -1;
  const file = workspace.files.find(item => item.id === fileId);
  const showPdf = isPdf(file) && mode === 'original' && !!token;
  const regions = preview?.pages.find(item => item.page === page)?.regions ?? NO_REGIONS;
  const pageOptions = preview?.pages.length
    ? preview.pages.map(item => item.page)
    : Array.from({ length: Math.max(1, pdfPages) }, (_, index) => index + 1);

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
            setPdfPages(0);
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
        {isPdf(file) && (
          <Segmented
            size="small"
            aria-label="原文显示方式"
            value={mode}
            onChange={value => setMode(value as ViewMode)}
            options={[{ value: 'original', label: '原件' }, { value: 'text', label: '识别文字' }]}
          />
        )}
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
      <div className="paper-wrap">
        {showPdf && file ? (
          <PdfLocator
            fileUrl={file.download_url}
            token={token}
            page={page}
            quote={source?.file_id === fileId && source.page === page ? source.quote : ''}
            regions={regions}
            onPageCount={setPdfPages}
          />
        ) : preview ? (
          <article className="original-paper">
            <h4>{preview.filename}</h4>
            {index >= 0 ? (
              <p>
                {originalText.slice(0, index)}
                <mark>{quote}</mark>
                {originalText.slice(index + quote.length)}
              </p>
            ) : (
              <p>{originalText}</p>
            )}
            <div className="page-number">— {page} —</div>
          </article>
        ) : (
          <Empty description={file ? '请先解析文件，再查看原文与条款位置' : '还没有上传招标文件'} />
        )}
      </div>
      {preview && (
        <div className="original-foot">
          页码方式：{paginationName(preview.pagination)}
          {preview.warnings.length > 0 && ` · ${preview.warnings.join('；')}`}
        </div>
      )}
    </div>
  );
}
