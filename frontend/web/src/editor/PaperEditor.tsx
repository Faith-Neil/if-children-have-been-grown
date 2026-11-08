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
  caretOffset: () => number | null;
  selectText: (phrase: string) => boolean;
}

interface Props {
  markdown: string;
  editable: boolean;
  generating: boolean;
  onChange: (markdown: string) => void;
  onActivity?: () => void;
  onSelection?: (range: { start: number; end: number; text: string } | null) => void;
}

function markdownOffset(doc: { cut: (from: number, to: number) => { toJSON: () => PaperNode } }, pos: number) {
  if (pos <= 0) return 0;
  return docToMarkdown(doc.cut(0, pos).toJSON()).length;
}

export const PaperEditor = forwardRef<PaperEditorHandle, Props>(function PaperEditor({ markdown, editable, generating, onChange, onActivity, onSelection }, ref) {
  const incoming = useRef(markdown);
  incoming.current = markdown;
  const changeRef = useRef(onChange);
  const activityRef = useRef(onActivity);
  const selectionRef = useRef(onSelection);
  changeRef.current = onChange;
  activityRef.current = onActivity;
  selectionRef.current = onSelection;
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
    const node = sheetRef.current;
    if (!node || !editor) return;
    const apply = (event: Event) => {
      const text = (event as CustomEvent<string>).detail;
      if (typeof text !== 'string') return;
      editor.commands.setContent(markdownToDoc(text), true);
    };
    node.addEventListener('icg-set-markdown', apply);
    return () => node.removeEventListener('icg-set-markdown', apply);
  }, [editor]);

  useEffect(() => {
    if (!editor) return;
    const run = () => requestAnimationFrame(syncPageLayout);
    run();
    const reportSelection = () => {
      const { from, to } = editor.state.selection;
      if (from === to) {
        selectionRef.current?.(null);
        return;
      }
      const text = editor.state.doc.textBetween(from, to, '\n');
      selectionRef.current?.(text
        ? { start: markdownOffset(editor.state.doc, from), end: markdownOffset(editor.state.doc, to), text }
        : null);
    };
    editor.on('create', run);
    editor.on('update', run);
    editor.on('transaction', run);
    editor.on('selectionUpdate', reportSelection);
    const surface = sheetRef.current?.querySelector('.paper-surface') as HTMLElement | null;
    const ro = surface ? new ResizeObserver(run) : null;
    if (surface && ro) ro.observe(surface);
    return () => {
      editor.off('create', run);
      editor.off('update', run);
      editor.off('transaction', run);
      editor.off('selectionUpdate', reportSelection);
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
    caretOffset: () => (editor ? markdownOffset(editor.state.doc, editor.state.selection.from) : null),
    selectText: phrase => {
      if (!editor || !phrase) return false;
      let found: { from: number; to: number } | null = null;
      editor.state.doc.descendants((node, pos) => {
        if (found || !node.isText || !node.text) return;
        const index = node.text.indexOf(phrase);
        if (index < 0) return;
        found = { from: pos + index, to: pos + index + phrase.length };
      });
      if (!found) return false;
      editor.chain().focus().setTextSelection(found).run();
      return true;
    },
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
