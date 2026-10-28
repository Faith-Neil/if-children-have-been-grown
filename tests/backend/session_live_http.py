# 为什么有这个文件：在真实监听的本机后台上复核可信会话入口的身份、参数拒绝和项目边界。
# 它解决什么问题：避免只依赖TestClient或仓库外临时验证器；不被pytest默认收集，CI可显式运行。
"""Run: python tests/backend/session_live_http.py  (starts uvicorn on a free 127.0.0.1 port, synthetic seed data only)."""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "backend" / "bid-core"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_checks(base_url):
    client = httpx.Client(base_url=base_url, timeout=10)
    results = []

    def login(account):
        response = client.post("/api/v1/auth/login", json={"username": account, "password": "X_2026"})
        response.raise_for_status()
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def check(name, ok, detail=""):
        results.append({"name": name, "pass": bool(ok), "detail": detail})

    for account, role in {"alpha-manager": "project_lead", "alpha-editor": "bid_writer", "alpha-viewer": "viewer"}.items():
        response = client.get("/api/v1/session", headers=login(account))
        data = response.json()
        nav = sorted(item["route_id"] for item in data.get("navigation", []))
        check(f"session {account} -> {role}", response.status_code == 200 and data["user"]["primary_role"] == role
              and not any("company" in n or "platform" in n for n in nav), f"{response.status_code} {nav}")
    manager = login("alpha-manager")
    for account in ("alpha-manager", "alpha-viewer"):
        response = client.get("/api/v1/session", params={"project_id": "alpha-project"}, headers=login(account))
        check(f"{account} reads alpha-project access", response.status_code == 200 and "project_access" in response.json(),
              str(response.status_code))
    for headers, name in (({}, "missing bearer"), ({"Authorization": "Bearer bad"}, "bad bearer")):
        response = client.get("/api/v1/session", headers=headers)
        check(name + " is 401", response.status_code == 401, str(response.status_code))
    for query in ("role=company_admin", "company_id=beta", "user_id=beta-manager",
                  "project_id=alpha-project&project_id=beta-project"):
        response = client.get("/api/v1/session?" + query, headers=manager)
        check(f"forged {query} is 422", response.status_code == 422, str(response.status_code))
    response = client.request("GET", "/api/v1/session", headers=manager, json={"role": "company_admin"})
    check("GET body is 422", response.status_code == 422, str(response.status_code))
    for account, project in (("beta-manager", "alpha-project"), ("alpha-outsider-manager", "alpha-project"),
                             ("alpha-manager", "missing-project")):
        response = client.get("/api/v1/session", params={"project_id": project}, headers=login(account))
        check(f"{account} {project} is 404", response.status_code == 404, str(response.status_code))
    return results


def main():
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "icg_demo.main:app", "--app-dir", str(APP_DIR),
                               "--host", "127.0.0.1", "--port", str(port), "--workers", "1"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base_url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                httpx.get(base_url + "/api/v1/session", timeout=1)
                break
            except httpx.TransportError:
                time.sleep(0.1)
        results = run_checks(base_url)
    finally:
        server.terminate()
        server.wait(timeout=10)
    passed = sum(item["pass"] for item in results)
    print(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"TOTAL {len(results)} PASS {passed}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
