# 为什么有这个文件：打通章节 AI 生成与建议端到端闭环（ISSUE-037 / ISSUE-028 贯通，AI-M0 里程碑核心目标）。
# 它解决什么问题：
# 1. 验证真实检索链路（RAGFlow）与配置驱动模型（OpenAI 兼容端点）在章节生成与正文建议中协同工作；
# 2. 验证组装的 input_snapshot 携带 [证] 证据、[片] 检索切片（含 chunk_id 与 document_id 来源出处）及事实变量；
# 3. 闭环敏感项目门禁（403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL）、变量防篡改（409 FACT_VARIABLE_LOST / FACT_LITERAL_REPLACEMENT）；
# 4. 验证知识库关闭跳过检索与模型异常（502 MODEL_UNAVAILABLE）不污染正式正文。

from copy import deepcopy
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from fake_openai_chat import ASSISTANT_TEXT, FakeOpenAIChat
from fake_ragflow import (
    MODE_CHUNKS,
    MODE_EMPTY,
    SYNTHETIC_CHUNK_ID,
    SYNTHETIC_CONTENT,
    SYNTHETIC_DATASET_ID,
    SYNTHETIC_DOCUMENT_ID,
    FakeRagflow,
)
from icg_demo.adapters import MemoryRepository, seed_state
from icg_demo.domain import DemoState
from icg_demo.main import create_app
from icg_demo.model_config_storage import ModelConfig, encrypt_api_key
from icg_demo.ragflow_client import RagflowConfig, RagflowRetrievalClient
from icg_demo.retrieval import EvidenceCandidateService
from test_generation_context import CONTEXT_TENDER, generate, prepare_context, preview, suggest
from test_reference_flow import login


@pytest.fixture
def secret_key(monkeypatch):
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("ICG_SECRET_KEY", key)
    return key


@pytest.fixture
def rag_and_chat_env(fake_ragflow, fake_openai_chat, secret_key):
    """装配假 RAGFlow 检索服务与假 OpenAI 对话端点，提供独立客户端与服务句柄。"""
    fake_ragflow.mode = MODE_CHUNKS
    rag_client = RagflowRetrievalClient(
        base_url=fake_ragflow.base_url,
        api_key="test-rag-key",
        timeout_seconds=5.0,
    )
    evidence_service = EvidenceCandidateService(
        ragflow_client=rag_client,
        company_datasets={"alpha": SYNTHETIC_DATASET_ID},
        rerank_id="rerank-bge-m3",
    )

    repository = MemoryRepository(seed_state())
    app = create_app(repository=repository, evidence_service=evidence_service)
    client = TestClient(app)

    # 在系统预置绑定模型配置，指向 fake_openai_chat
    headers = login(client, "alpha-manager")
    enc_key = encrypt_api_key("sk-test-model-key")
    cfg = ModelConfig(
        id="cfg-e2e-rag-model",
        company_id="alpha",
        name="端到端集成模型",
        provider="openai-compatible",
        base_url=fake_openai_chat.base_url,
        model="qwen2.5-32b-instruct",
        encrypted_api_key=enc_key,
        is_local=True,
        allow_sensitive=True,
        stream_enabled=False,
        json_mode_enabled=False,
        timeout_seconds=5.0,
    )

    def inject_model_cfg(state: DemoState):
        state.model_configs[cfg.id] = cfg

    repository.transaction(inject_model_cfg)

    yield {
        "client": client,
        "repository": repository,
        "fake_ragflow": fake_ragflow,
        "fake_openai_chat": fake_openai_chat,
        "evidence_service": evidence_service,
        "model_config": cfg,
        "headers": headers,
    }


def bind_project_model(env, project_id, model_config_id="cfg-e2e-rag-model"):
    res = env["client"].post(
        f"/api/v1/projects/{project_id}/model-config",
        headers=env["headers"],
        json={"model_config_id": model_config_id},
    )
    assert res.status_code == 200, res.text


def test_end_to_end_chapter_generation_with_ragflow_chunks(rag_and_chat_env):
    """验证章节生成全流程：
    1. 触发 RAGFlow 检索并解析切片；
    2. 生成包含 [片]、chunk_id/document_id 溯源与 [证] 证据的 prompt；
    3. 调用动态配置的 OpenAI 兼容大模型；
    4. 将检索片段写入 input_snapshot.retrieved_evidence。
    """
    env = rag_and_chat_env
    client, repository = env["client"], env["repository"]
    setup = prepare_context(client, repository, sla=True)
    bind_project_model(env, setup["flow"].id)

    # 1. 执行章节生成
    result = generate(setup)
    candidate = result["chapters"][0]["candidate"]

    # 2. 验证 RAGFlow 检索被触发并收到章节 query
    assert len(env["fake_ragflow"].calls) >= 1
    rag_call = env["fake_ragflow"].calls[0]
    assert rag_call.path == "/api/v1/retrieval"
    import json
    rag_body = json.loads(rag_call.body.decode("utf-8"))
    assert setup["chapter"]["title"] in rag_body["question"]
    assert rag_body["dataset_ids"] == [SYNTHETIC_DATASET_ID]
    assert rag_body["rerank_id"] == "rerank-bge-m3"

    # 3. 验证模型收到了组装了 [片]、出处、[证] 与事实变量的 Prompt
    assert len(env["fake_openai_chat"].calls) == 1
    chat_call = env["fake_openai_chat"].calls[0]
    assert chat_call.header("Authorization") == "Bearer sk-test-model-key"
    user_prompt = chat_call.json["messages"][1]["content"]

    # 验证检索证据切片 [片] 与 provenance
    assert "[片] 检索证据片段" in user_prompt
    assert f"chunk_id: {SYNTHETIC_CHUNK_ID}" in user_prompt
    assert f"document_id: {SYNTHETIC_DOCUMENT_ID}" in user_prompt
    assert SYNTHETIC_CONTENT in user_prompt

    # 验证已确认资料证据 [证] 与已确认事实变量
    assert "[证] 已确认可引用证据：" in user_prompt
    assert setup["evidence"]["name"] in user_prompt
    assert "{{sla:P1.response}}" in user_prompt
    assert "{{fact:" + setup["selected"]["id"] + "}}" in user_prompt

    # 4. 验证 input_snapshot 中包含结构化 retrieved_evidence
    snapshot = candidate["input_snapshot"]
    assert "retrieved_evidence" in snapshot
    assert len(snapshot["retrieved_evidence"]) >= 1
    first_chunk = snapshot["retrieved_evidence"][0]
    assert first_chunk["tag"] == "[片]"
    assert first_chunk["chunk_id"] == SYNTHETIC_CHUNK_ID
    assert first_chunk["document_id"] == SYNTHETIC_DOCUMENT_ID
    assert first_chunk["content"] == SYNTHETIC_CONTENT
    assert candidate["provider"] == "openai-compatible"
    assert candidate["is_real_model"] is True


def test_end_to_end_chapter_suggestion_with_ragflow_chunks(rag_and_chat_env):
    """验证章节建议全流程：DemoService.suggest 走同一检索增强快照与模型配置。"""
    env = rag_and_chat_env
    client, repository = env["client"], env["repository"]
    setup = prepare_context(client, repository, sla=True)
    bind_project_model(env, setup["flow"].id)

    res = suggest(client, setup, instruction="请依据招标文件与检索资料改进章节表述。")
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["provider"] == "openai-compatible"
    assert data["is_real_model"] is True
    assert "retrieved_evidence" in data["input_snapshot"]
    retrieved = data["input_snapshot"]["retrieved_evidence"]
    assert any(c["chunk_id"] == SYNTHETIC_CHUNK_ID for c in retrieved)

    # 验证模型实际收到 prompt
    assert len(env["fake_openai_chat"].calls) == 1
    chat_prompt = env["fake_openai_chat"].calls[0].json["messages"][1]["content"]
    assert "[片] 检索证据片段" in chat_prompt
    assert SYNTHETIC_CHUNK_ID in chat_prompt


def test_zero_hit_ragflow_graceful_fallback(rag_and_chat_env):
    """当 RAGFlow 返回 0 个 chunks 时，系统优雅降级，正常推进生成而不报错。"""
    env = rag_and_chat_env
    env["fake_ragflow"].mode = MODE_EMPTY
    client, repository = env["client"], env["repository"]
    setup = prepare_context(client, repository, sla=True)
    bind_project_model(env, setup["flow"].id)

    result = generate(setup)
    candidate = result["chapters"][0]["candidate"]
    snapshot = candidate["input_snapshot"]

    # retrieved_evidence 为空列表，不报错
    assert snapshot["retrieved_evidence"] == []

    # 模型 prompt 仍包含事实与 [证] 证据，但不含 [片]
    user_prompt = env["fake_openai_chat"].calls[0].json["messages"][1]["content"]
    assert "[证] 已确认可引用证据：" in user_prompt
    assert "[片] 检索证据片段" not in user_prompt


def test_knowledge_base_disabled_skips_ragflow_completely(rag_and_chat_env):
    """知识库关闭（knowledge_base_enabled=False）时不发起任何 RAGFlow 网络调用。"""
    env = rag_and_chat_env
    env["evidence_service"].knowledge_base_enabled = False
    client, repository = env["client"], env["repository"]
    setup = prepare_context(client, repository, sla=True)
    bind_project_model(env, setup["flow"].id)

    result = generate(setup)
    assert result["chapters"][0]["candidate"] is not None

    # RAGFlow 零网络调用
    assert len(env["fake_ragflow"].calls) == 0

    # retrieved_evidence 为空，生成依然成功
    assert result["chapters"][0]["candidate"]["input_snapshot"]["retrieved_evidence"] == []


def test_sensitive_project_blocks_cloud_model_with_403(rag_and_chat_env):
    """敏感项目阻断非本地模型：在调用模型前拦截 403 SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL。"""
    env = rag_and_chat_env
    client, repository = env["client"], env["repository"]
    setup = prepare_context(client, repository, sla=True)

    # 1. 创建云端非本地模型配置（is_local=False, allow_sensitive=False）
    enc_key = encrypt_api_key("sk-cloud-key")
    cloud_cfg = ModelConfig(
        id="cfg-cloud-remote",
        company_id="alpha",
        name="公有云模型",
        provider="openai-compatible",
        base_url=env["fake_openai_chat"].base_url,
        model="cloud-gpt-4o",
        encrypted_api_key=enc_key,
        is_local=False,
        allow_sensitive=False,
    )

    def inject_cloud_cfg(state: DemoState):
        state.model_configs[cloud_cfg.id] = cloud_cfg

    repository.transaction(inject_cloud_cfg)
    bind_project_model(env, setup["flow"].id, "cfg-cloud-remote")

    # 绑定后将项目标记为敏感项目
    def mark_sensitive(state: DemoState):
        state.projects[setup["flow"].id].sensitive = True

    repository.transaction(mark_sensitive)

    # 2. 章节生成被 403 阻断
    gen_res = generate(setup, expected=403)
    assert gen_res["code"] == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 3. 章节建议同样被 403 阻断
    sug_res = suggest(client, setup)
    assert sug_res.status_code == 403
    sug_data = sug_res.json()
    err_code = sug_data.get("code") or (sug_data.get("error", {}).get("code") if isinstance(sug_data.get("error"), dict) else sug_data.get("error"))
    assert err_code == "SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL"

    # 4. 验证模型端点绝对未收到任何请求（防数据外泄门禁）
    assert len(env["fake_openai_chat"].calls) == 0


def test_model_variable_tampering_blocks_and_preserves_content(rag_and_chat_env):
    """模型输出篡改或遗漏正式正文中的变量时阻断（409），且正式正文不受破坏。"""
    env = rag_and_chat_env
    client, repository = env["client"], env["repository"]
    setup = prepare_context(client, repository, sla=True)
    bind_project_model(env, setup["flow"].id)

    # 给正式正文写入事实变量
    fact_id = setup["selected"]["id"]
    formal_content = f"正式正文本章要求执行服务期限：{{{{fact:{fact_id}}}}}。"

    def set_content(state: DemoState):
        state.chapters[setup["chapter"]["id"]].content = formal_content
        state.chapters[setup["chapter"]["id"]].revision += 1

    repository.transaction(set_content)

    # 1. 模拟模型删除了正式正文中的事实变量
    env["fake_openai_chat"].assistant_text = "手写正文内容，去除了所有事实变量。"
    gen_res = generate(setup, expected=409)
    assert gen_res["code"] == "FACT_VARIABLE_LOST"

    # 验证正式正文未被破坏
    curr_chapter = repository.read().chapters[setup["chapter"]["id"]]
    assert curr_chapter.content == formal_content

    # 2. 模拟模型把事实变量改成手写取值（服务期限：12个月）
    # 当正式正文不含变量时，输出直接替换为字面值将触发 FACT_LITERAL_REPLACEMENT
    def clear_content(state: DemoState):
        state.chapters[setup["chapter"]["id"]].content = "初始空白正文。"
        state.chapters[setup["chapter"]["id"]].revision += 1

    repository.transaction(clear_content)
    env["fake_openai_chat"].assistant_text = "正文输出服务期限：12个月，未保留变量占位符。"
    tamper_res = generate(setup, expected=409)
    assert tamper_res["code"] == "FACT_LITERAL_REPLACEMENT"
    assert repository.read().chapters[setup["chapter"]["id"]].content == "初始空白正文。"


def test_upstream_model_error_maps_to_502_without_corrupting_official_content(rag_and_chat_env):
    """上游模型报错（500/网络超时）时转换为 502 MODEL_UNAVAILABLE，正式正文安全保留。"""
    env = rag_and_chat_env
    client, repository = env["client"], env["repository"]
    setup = prepare_context(client, repository, sla=True)
    bind_project_model(env, setup["flow"].id)

    original_content = repository.read().chapters[setup["chapter"]["id"]].content

    # 设置假模型返回 500 内部错误
    env["fake_openai_chat"].status_code = 500
    gen_res = generate(setup, expected=502)
    assert gen_res["code"] == "MODEL_UNAVAILABLE"

    # 正式正文不变
    assert repository.read().chapters[setup["chapter"]["id"]].content == original_content
