# 为什么有这个文件：验证企业设置页提交的整份设置能保存并读回（PRD v1.8 §5.10.2、§5.11.9；页面原先“保存”不写后台）。
# 它解决什么问题：用页面实际发送的字段（含 custom_settings 里的页面项）调用更新接口，再读出核对；越界由后台拒绝；
# 保存后编辑锁时长、对话助手样例条数、解析阈值被业务读取。

from test_reference_flow import client, login  # noqa: F401

PAGE_PAYLOAD = {
    "password_min_length": 12, "password_min_char_classes": 4, "max_login_attempts": 3, "session_timeout_minutes": 60,
    "edit_lock_timeout_minutes": 20, "edit_lock_heartbeat_seconds": 30, "editor_autosave_seconds": 10,
    "assistant_enabled": True, "assistant_suggestion_count": 5, "assistant_kb_default": False, "assistant_allow_kb_off": True,
    "dup_min_chars": 10, "dup_history_months": 36, "parse_confidence_threshold": 0.9,
    "custom_settings": {"ui_outline_max_depth": 3, "ui_outline_target_words_default": 2500, "ui_ai_token_budget_per_chapter": 8192,
                        "ui_custom_fields": [{"id": "x", "field_key": "custom_x", "field_name": "X", "field_type": "text",
                                              "required": False, "scope": "project"}]},
}


def test_page_payload_saves_reads_back_and_takes_effect(client):
    admin = login(client, "alpha-company-admin")
    saved = client.patch("/api/v1/companies/alpha/settings", headers=admin, json=PAGE_PAYLOAD)
    assert saved.status_code == 200, saved.text
    read = client.get("/api/v1/companies/alpha/settings", headers=admin).json()
    for key, value in PAGE_PAYLOAD.items():
        if key != "custom_settings":
            assert read[key] == value, key
    assert read["custom_settings"]["ui_outline_max_depth"] == 3
    assert read["custom_settings"]["ui_custom_fields"][0]["field_key"] == "custom_x"
    assert read["updated_by"] and read["updated_at"]

    state = client.app.state.service.repository.read()
    from icg.domain.company_settings import parse_confidence_threshold
    assert parse_confidence_threshold(state, "alpha") == 0.9
    from icg.domain.selection_rewrite import SelectionRewriteService
    assert SelectionRewriteService._policy(state, "alpha")["count"] == 5

    too_long = client.patch("/api/v1/companies/alpha/settings", headers=admin, json={**PAGE_PAYLOAD, "edit_lock_timeout_minutes": 90})
    assert too_long.status_code == 422 and too_long.json()["code"] == "SETTING_VALUE_OUT_OF_BOUNDS"
    editor = client.patch("/api/v1/companies/alpha/settings", headers=login(client, "alpha-editor"), json=PAGE_PAYLOAD)
    assert editor.status_code == 403
