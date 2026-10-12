# 为什么有这个文件：让后台回归直接导入本仓库真实的demo应用。
# 它解决什么问题：后端目录名带连字符且未安装为包，测试仍能使用同一实际实现。
from pathlib import Path
import sys

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend" / "bid-core"
sys.path.insert(0, str(BACKEND_ROOT))


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_call(item):
    # 在测试调用阶段失败，pytest 会计为 failed。夹具阶段的 pytest.fail 只会显示成 error。
    if item.get_closest_marker("mysql") is not None:
        from icg_demo.database import mysql_gate

        gate = mysql_gate()
        if gate.action == "skip":
            pytest.skip(gate.reason)
        if gate.action == "fail":
            pytest.fail(gate.reason)
    yield
