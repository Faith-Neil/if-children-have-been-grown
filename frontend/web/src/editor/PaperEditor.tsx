// 为什么有这个文件：技术方案正文在编辑台里按纸面排版，而不是展示 Markdown 源码。
// 它解决什么问题：标题、加粗、列表和表格可以直接改；保存时写回章节原有的 Markdown 字段。

import React, { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableHeader from '@tiptap/extension-table-header';
import TableCell from '@tiptap/extension-table-cell';
import Placeholder from '@tiptap/extension-placeholder';
import { docToMarkdown, markdownToDoc, sameMarkdown, type PaperNode } from './paper-markdown';
import { estimatePaperPageCount, paperStackMinHeight } from './paper-pagination';

export interface PaperEditorHandle {
  undo: () => void;
  redo: () => void;
  bold: () => void;
  underline: () => void;
  heading: (level: 1 | 2 | 3) => void;
  paragraph: () => void;
  bullet: () => void;
  ordered: () => void;
  table: () => void;
  insertParagraph: (text: string) => void;
}

interface Props {
  markdown: string;
  editable: boolean;
  generating: boolean;
  onChange: (markdown: string) => void;
  onActivity?: () => void;
}

export const PaperEditor = forwardRef<PaperEditorHandle, Props>(function PaperEditor({ markdown, editable, generating, onChange, onActivity }, ref) {
  const incoming = useRef(markdown);
  incoming.current = markdown;
  const changeRef = useRef(onChange);
  const activityRef = useRef(onActivity);
  changeRef.current = onChange;
  activityRef.current = onActivity;
  const sheetRef = useRef<HTMLDivElement>(null);
  const [pageCount, setPageCount] = useState(1);
  const syncPageLayout = useCallback(() => {
    const sheet = sheetRef.current;
    const surface = sheet?.querySelector('.paper-surface') as HTMLElement | null;
    if (!surface || !sheet) return;
    const pages = estimatePaperPageCount(surface.scrollHeight);
    setPageCount(pages);
    sheet.style.minHeight = `${paperStackMinHeight(pages)}px`;
    sheet.dataset.pages = String(pages);
  }, []);
  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3, 4, 5, 6] } }),
      Underline,
      Table.configure({ resizable: false }),
      TableRow,
      TableHeader,
      TableCell,
      Placeholder.configure({ placeholder: '编写本节投标响应。' }),
    ],
    content: markdownToDoc(markdown),
    editable: editable && !generating,
    editorProps: {
      attributes: { class: 'paper-surface', 'aria-label': '章节正文' },
    },
    onUpdate: ({ editor: current }) => {
      const next = docToMarkdown(current.getJSON() as PaperNode);
      if (sameMarkdown(next, incoming.current)) return;
      activityRef.current?.();
      changeRef.current(next);
    },
  });

  useEffect(() => {
    editor?.setEditable(editable && !generating);
  }, [editor, editable, generating]);

  useEffect(() => {
    if (!editor) return;
    const current = docToMarkdown(editor.getJSON() as PaperNode);
    if (sameMarkdown(current, markdown)) return;
    editor.commands.setContent(markdownToDoc(markdown), false);
  }, [editor, markdown]);

  useEffect(() => {
    if (!editor) return;
    const run = () => requestAnimationFrame(syncPageLayout);
    run();
    editor.on('create', run);
    editor.on('update', run);
    editor.on('transaction', run);
    const surface = sheetRef.current?.querySelector('.paper-surface') as HTMLElement | null;
    const ro = surface ? new ResizeObserver(run) : null;
    if (surface && ro) ro.observe(surface);
    return () => {
      editor.off('create', run);
      editor.off('update', run);
      editor.off('transaction', run);
      ro?.disconnect();
    };
  }, [editor, syncPageLayout]);

  useImperativeHandle(ref, () => ({
    undo: () => { editor?.chain().focus().undo().run(); },
    redo: () => { editor?.chain().focus().redo().run(); },
    bold: () => { editor?.chain().focus().toggleBold().run(); },
    underline: () => { editor?.chain().focus().toggleUnderline().run(); },
    heading: level => { editor?.chain().focus().toggleHeading({ level }).run(); },
    paragraph: () => { editor?.chain().focus().setParagraph().run(); },
    bullet: () => { editor?.chain().focus().toggleBulletList().run(); },
    ordered: () => { editor?.chain().focus().toggleOrderedList().run(); },
    table: () => { editor?.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(); },
    insertParagraph: text => { editor?.chain().focus().insertContent({ type: 'paragraph', content: [{ type: 'text', text }] }).run(); },
  }), [editor]);

  return (
    <div className="paper-workspace" data-testid="paper-workspace">
      <div
        className={`paper-sheet${generating ? ' is-generating' : ''}`}
        data-testid="paper-editor"
        data-page-count={pageCount}
        ref={sheetRef}
      >
        <EditorContent editor={editor} />
        <span className="paper-page-indicator" data-testid="paper-page-indicator">共 {pageCount} 页</span>
        {generating && (
          <div className="paper-wait" data-testid="paper-generating" aria-live="polite">
            <div className="paper-wait-title" />
            <div className="paper-wait-line w-full" />
            <div className="paper-wait-line w-long" />
            <div className="paper-wait-line w-mid" />
            <div className="paper-wait-line w-long" />
            <div className="paper-wait-line w-short" />
            <span className="paper-wait-label">正在撰写</span>
          </div>
        )}
      </div>
    </div>
  );
});
