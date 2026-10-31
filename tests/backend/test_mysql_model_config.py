# 为什么有这个文件：验证模型配置（含备用模型列，迁移 0013）在 MySQL 中保存并重新读出（APP-M2-T177，PRD v1.8 §6.4）。
# 它解决什么问题：模型配置保存函数会吞掉 SQL 错误，只跑其他测试发现不了新列没写进去；这里重开仓储逐字段核对。

import pytest

from icg.infra.mysql_gate import repository_from_environment
from icg.infra.model_config_storage import ModelConfig

pytestmark = pytest.mark.mysql


def test_model_config_with_fallback_round_trips():
    repository = repository_from_environment()

    def write(state):
        state.model_configs["cfg-mysql-backup"] = ModelConfig(id="cfg-mysql-backup", company_id="alpha", name="备用",
                                                             base_url="http://backup.local", model="qwen-backup")
        state.model_configs["cfg-mysql-primary"] = ModelConfig(id="cfg-mysql-primary", company_id="alpha", name="主模型",
                                                              base_url="http://primary.local", model="qwen-primary",
                                                              fallback_config_id="cfg-mysql-backup")
    repository.transaction(write)
    reloaded = repository_from_environment().read()
    assert reloaded.model_configs["cfg-mysql-primary"].fallback_config_id == "cfg-mysql-backup"
    assert reloaded.model_configs["cfg-mysql-backup"].fallback_config_id is None

    def clear(state):
        state.model_configs["cfg-mysql-primary"].fallback_config_id = None
        state.model_configs["cfg-mysql-primary"].revision += 1
    repository.transaction(clear)
    assert repository_from_environment().read().model_configs["cfg-mysql-primary"].fallback_config_id is None
