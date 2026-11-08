import test from 'node:test';
import assert from 'node:assert/strict';
import { moveOutline, placeHeading } from '../../src/project/directory-order.ts';

const rows = [
  { title: '总则', level: 1 },
  { title: '范围', level: 2 },
  { title: '人员', level: 2 },
  { title: '驻场', level: 3 },
];

test('拖到最前时章节成为一级', () => {
  const next = placeHeading(rows, 3, 0, 4);
  assert.deepEqual(next.map(item => item.title), ['驻场', '总则', '范围', '人员']);
  assert.equal(next[0].level, 1);
});

test('停在原位时只改层级，并且不能跳级', () => {
  const next = placeHeading(rows, 2, 2, 4);
  assert.equal(next[2].title, '人员');
  assert.equal(next[2].level, 3);
});

test('向右拖可以变成上一节的下一级', () => {
  const next = placeHeading(rows, 2, 3, 3);
  assert.equal(next[2].title, '人员');
  assert.equal(next[2].level, 3);
});

test('拖动父节时子节跟着走，并一起调整层级', () => {
  const next = moveOutline(rows, 2, 0, 1);
  assert.deepEqual(next.map(item => [item.title, item.level]), [
    ['人员', 1],
    ['驻场', 2],
    ['总则', 1],
    ['范围', 2],
  ]);
});

test('降级不能比上一节深超过一级', () => {
  const next = moveOutline(rows, 1, 1, 4);
  assert.equal(next[1].title, '范围');
  assert.equal(next[1].level, 2);
});
