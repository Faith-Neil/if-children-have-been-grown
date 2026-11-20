import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PAPER_PAGE_BODY_HEIGHT,
  estimatePaperPageCount,
  paperStackMinHeight,
} from '../../src/editor/paper-pagination.ts';

test('estimatePaperPageCount returns at least one page', () => {
  assert.equal(estimatePaperPageCount(0), 1);
  assert.equal(estimatePaperPageCount(-10), 1);
});

test('estimatePaperPageCount grows with content height', () => {
  assert.equal(estimatePaperPageCount(PAPER_PAGE_BODY_HEIGHT / 2), 1);
  assert.equal(estimatePaperPageCount(PAPER_PAGE_BODY_HEIGHT), 1);
  assert.equal(estimatePaperPageCount(PAPER_PAGE_BODY_HEIGHT + 1), 2);
});

test('paperStackMinHeight includes inter-page desk gap', () => {
  assert.equal(paperStackMinHeight(1), 1123);
  assert.equal(paperStackMinHeight(2), 1123 + 1123 + 18);
});
