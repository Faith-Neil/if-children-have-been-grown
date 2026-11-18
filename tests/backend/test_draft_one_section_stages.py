# 为什么有这个文件：_draft_one 必须按序打出 retrieve→deviate→write_section，且偏离后必定写正文。

from __future__ import annotations

from types import SimpleNamespace

import pytest

from icg.domain.technical_matrix import bind_deviation_judge, reset_deviation_judge
from icg.domain.technical_volume import bind_section_writer, reset_section_writer


@pytest.fixture()
def stub_env(monkeypatch):
  collected: list[dict] = []

  def fake_retrieve(_kb, _company, _query, _workflow, *, limit=8):
      return [{"name": "历史.docx", "content": "每30分钟健康检查", "dataset_kind": "history", "score": 0.9}], {
          "query": _query, "history_hits": 1, "material_hits": 0, "tender_hits": 0,
      }

  monkeypatch.setattr("icg.domain.technical_rag.retrieve_for_section", fake_retrieve)
  monkeypatch.setattr("icg.domain.technical_rag.knowledge_prompt_block", lambda _c, _w: "知识块")

  class Model:
      is_real_model = True
      is_local = True
      stream_enabled = False
      base_url = "http://127.0.0.1:9"

      def suggest(self, *_args, **_kwargs):
          raise AssertionError("deviate 应用绑定的 judge，不应走未绑定的 suggest")

  yield collected, Model()


def _emit_factory(collected):
  def emit(event):
      collected.append(event)
  return emit


def test_draft_one_emits_stages_and_never_stops_after_deviate(stub_env):
  collected, model = stub_env
  judge = bind_deviation_judge(lambda _clause, quote: {
      "deviation": "正偏离",
      "reason": "历史巡检为每30分钟一次。",
  } if "30" in quote else {"deviation": "无偏离", "reason": ""})
  writer = bind_section_writer(
      lambda title, row: f"BODY::{title}::{row.get('response_type')}。" + ("按招标逐条落实。" * 6),
  )
  try:
      from icg.domain.technical_volume import _draft_one

      heading = {"task_id": "task-1", "title": "健康检查", "number": "1.1", "requirement_ids": ["req-1"]}
      rows = {
          "req-1": {
              "id": "req-1", "text": "数据库健康检查", "technical_clause": True, "status": "pending",
          },
      }
      tasks = {"task-1": {"requirement_ids": ["req-1"], "response_points": ["按招标巡检"]}}
      emit = _emit_factory(collected)
      patch = _draft_one(
          heading, rows, tasks, model, {"technical_promises": {}}, SimpleNamespace(), "co-1", emit, None,
      )
  finally:
      reset_deviation_judge(judge)
      reset_section_writer(writer)

  patches = [item for item in collected if item.get("event") == "task.patched"]
  stages = [item.get("stage") for item in patches if item.get("stage")]
  assert stages[:3] == ["retrieve", "deviate", "write_section"]
  assert patches[-1].get("generation_status") == "generated"
  assert "section.done" in {item.get("event") for item in collected}
  assert patch.get("body", "").startswith("BODY::")
  assert rows["req-1"].get("response_type") == "exceed"