# 为什么有这个文件：让后台回归直接导入本仓库真实的demo应用。
# 它解决什么问题：后端目录名带连字符且未安装为包，测试仍能使用同一实际实现。
from pathlib import Path
import os
import sys

# 保证本机测试夹具与子进程不受 Windows 系统代理干扰
os.environ.setdefault("NO_PROXY", "*")
os.environ.setdefault("no_proxy", "*")
# 本机环境里配了真实 RAGFlow（ICG_RAGFLOW_BASE_URL / API_KEY）时，普通用例不能写到真实服务上；
# 只有显式开启 ICG_RUN_REAL_RAGFLOW_TESTS=1 才保留这些变量。
if os.environ.get("ICG_RUN_REAL_RAGFLOW_TESTS") != "1":
    for _name in ("ICG_RAGFLOW_BASE_URL", "ICG_RAGFLOW_API_KEY", "ICG_RAGFLOW_API_KEY_ENV"):
        os.environ.pop(_name, None)

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend" / "bid-core"
sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def fake_openai_chat():
    from fake_openai_chat import FakeOpenAIChat

    service = FakeOpenAIChat()
    try:
        yield service
    finally:
        service.close()


@pytest.fixture
def fake_ragflow():
    from fake_ragflow import FakeRagflow

    service = FakeRagflow()
    try:
        yield service
    finally:
        service.close()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_call(item):
    # 在测试调用阶段失败，pytest 会计为 failed。夹具阶段的 pytest.fail 只会显示成 error。
    if item.get_closest_marker("live_model") is not None:
        from fake_openai_chat import real_model_skip_reason

        reason = real_model_skip_reason()
        if reason:
            pytest.skip(reason)
    if item.get_closest_marker("live_ragflow") is not None:
        from fake_ragflow import real_ragflow_skip_reason

        reason = real_ragflow_skip_reason()
        if reason:
            pytest.skip(reason)
    if item.get_closest_marker("mysql") is not None:
        from icg_demo.database import mysql_gate

        gate = mysql_gate()
        if gate.action == "skip":
            pytest.skip(gate.reason)
        if gate.action == "fail":
            pytest.fail(gate.reason)
    yield
