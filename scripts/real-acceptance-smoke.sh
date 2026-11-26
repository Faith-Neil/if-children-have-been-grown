#!/usr/bin/env bash
# 一键真机冒烟：真实 RAGFlow + 本地 Qwen 端到端验收（TV-M0 / ISSUE-054）。
# 前置：内网 RAGFlow 容器与本地 Qwen 已启动；环境变量 ICG_RAGFLOW_BASE_URL/ICG_RAGFLOW_API_KEY、
# ICG_MODEL_BASE_URL 已按部署环境配置。CI/离线环境下本脚本直接退出不执行。
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "${CI:-}" = "true" ]; then
  echo "[skip] CI 环境物理断开内网，真机冒烟仅在本地执行"
  exit 0
fi

export ICG_RUN_REAL_RAGFLOW_TESTS=1
export ICG_RUN_REAL_MODEL_TESTS=1

cd backend/bid-core
python -m pytest \
  ../../tests/backend/test_ragflow_kb_sync.py \
  ../../tests/backend/test_history_bid_parse_acceptance.py \
  ../../tests/backend/test_openai_compatible_model.py \
  ../../tests/backend/test_knowledge_base.py \
  -q "$@"
