# 为什么有这个文件：让回执、会话和编辑租约测试在一个新的解释器里调用演示接口。
# 它解决什么问题：子进程不会经过 pytest 的路径注入，必须自己找到后台包。

from __future__ import annotations

import sys
from pathlib import Path


def run_action(action: str, payload: dict, queue) -> None:
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "backend" / "bid-core"))
    from fastapi.testclient import TestClient
    from icg_demo.main import create_app

    def body_of(response):
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("application/json"):
            return response.json()
        return response.text

    with TestClient(create_app()) as client:
        if action == "write":
            login = client.post("/api/demo/login", json={"account_id": "alpha-editor"})
            if login.status_code != 200:
                queue.put({"ok": False, "step": "login", "status": login.status_code, "body": login.text})
                return
            token = login.json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            library = client.get("/api/v1/library", headers=headers)
            revision = library.json()["revision"]
            response = client.post(
                "/api/v1/library",
                headers={**headers, "If-Match": str(revision), "Idempotency-Key": payload["key"]},
                json=payload["body"],
            )
            queue.put({
                "ok": response.status_code == 200,
                "status": response.status_code,
                "body": body_of(response),
                "token": token,
                "revision": revision,
                "replayed": response.headers.get("Idempotent-Replayed"),
            })
            return
        if action == "replay":
            headers = {"Authorization": "Bearer " + payload["token"]}
            session = client.get("/api/v1/session", headers=headers)
            response = client.post(
                "/api/v1/library",
                headers={
                    **headers,
                    "If-Match": str(payload["revision"]),
                    "Idempotency-Key": payload["key"],
                },
                json=payload["body"],
            )
            queue.put({
                "ok": session.status_code == 200 and response.status_code == 200,
                "session_status": session.status_code,
                "session": body_of(session),
                "status": response.status_code,
                "body": body_of(response),
                "replayed": response.headers.get("Idempotent-Replayed"),
            })
            return
        if action == "lock_acquire":
            account_id = payload.get("account_id", "alpha-editor")
            login = client.post("/api/demo/login", json={"account_id": account_id})
            if login.status_code != 200:
                queue.put({"ok": False, "step": "login", "status": login.status_code, "body": login.text})
                return
            token = login.json()["access_token"]
            response = client.post(
                "/api/chapters/" + payload.get("chapter_id", "alpha-tech") + "/lock",
                headers={"Authorization": "Bearer " + token},
                json={"takeover_reason": payload.get("takeover_reason")},
            )
            queue.put({
                "ok": response.status_code == 200,
                "status": response.status_code,
                "body": body_of(response),
                "token": token,
            })
            return
        if action == "lock_renew":
            response = client.post(
                "/api/chapters/" + payload.get("chapter_id", "alpha-tech") + "/lock/renew",
                headers={"Authorization": "Bearer " + payload["token"]},
                json={"lease_token": payload["lease_token"]},
            )
            queue.put({
                "ok": response.status_code == 200,
                "status": response.status_code,
                "body": body_of(response),
            })
            return
        queue.put({"ok": False, "step": "unknown", "action": action})
