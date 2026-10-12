# 为什么有这个文件：QA 对 BE-M0-T02/T03 的独立真实 HTTP 复核脚本（非 pytest 用例）。
# 它解决什么问题：在真实 uvicorn 进程上核对 v1 错误体、状态表与 spec 一致、幂等语义和页面回退路由的边界。
"""Run: python tests/backend/qa_error_idempotency_live_http.py  (uvicorn on a free 127.0.0.1 port, synthetic data only)."""
import http.client
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "bid-core"))
from icg_demo.errors import ERROR_STATUS  # noqa: E402

RESULTS = []
FROZEN_STATUS = "frozen"
DEPRECATION_NOTE = "已废弃。新旧入口并存。前端改用 getOutlinePlan、confirmOutlinePlan 与 startGeneration 之后，由后续 Issue 删除本操作。运行时尚未标出 deprecated。"
DEPRECATED_OPERATIONS = (
    "/api/v1/projects/{project_id}/plan",
    "/api/v1/projects/{project_id}/generate",
    "/api/v1/projects/{project_id}/chapters/{chapter_id}/plan/confirm",
)


def implemented_contract(document):
    """与契约测试相同：已冻结但尚未实现的路径不参与和运行中接口的比较。"""
    spec = json.loads(json.dumps(document))
    spec.pop("x-contract-drafts", None)
    for path, item in list(spec["paths"].items()):
        if isinstance(item, dict) and item.get("x-contract-status") == FROZEN_STATUS:
            del spec["paths"][path]
    for path in DEPRECATED_OPERATIONS:
        operation = spec["paths"][path]["post"]
        operation.pop("deprecated", None)
        if operation.get("description") == DEPRECATION_NOTE:
            operation.pop("description", None)
    schemas = spec["components"]["schemas"]
    for name, body in list(schemas.items()):
        if isinstance(body, dict) and body.get("x-contract-status") == FROZEN_STATUS:
            del schemas[name]
    return spec


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> {detail}"))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def v1_body_ok(r):
    try:
        b = r.json()
    except Exception:
        return False
    return set(b) == {"code", "message", "details", "traceId"} and b["traceId"] == r.headers.get("x-request-id")


def raw_get(port, path):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    c.request("GET", path)
    r = c.getresponse()
    return r.status, r.getheader("content-type") or "", r.read()


def main():
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "icg_demo.main:app", "--host", "127.0.0.1", "--port", str(port)],
                            cwd=ROOT / "backend" / "bid-core", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):
            try:
                httpx.get(base + "/api/v1/session", timeout=1); break
            except Exception:
                time.sleep(0.2)
        c = httpx.Client(base_url=base, timeout=20)

        def login(acc):
            r = c.post("/api/demo/login", json={"account_id": acc}); r.raise_for_status()
            return {"Authorization": "Bearer " + r.json()["access_token"]}

        # ---- spec 与代码状态表一致
        spec = json.loads((ROOT / "spec/openapi/demo-v1.json").read_text(encoding="utf-8"))
        spec_table = spec["components"]["x-error-status"]["statuses"]
        flat = {}
        dup = []
        for st, codes in spec_table.items():
            for code in codes:
                if code in flat: dup.append(code)
                flat[code] = int(st)
        check("spec: 每个 code 只出现一次", not dup, dup)
        check("spec 状态表 == 代码 ERROR_STATUS", flat == ERROR_STATUS,
              {k: (flat.get(k), ERROR_STATUS.get(k)) for k in set(flat) | set(ERROR_STATUS) if flat.get(k) != ERROR_STATUS.get(k)})
        check("spec V1Error.code enum == 代码表", sorted(spec["components"]["schemas"]["V1Error"]["properties"]["code"]["enum"]) == sorted(ERROR_STATUS))
        check("code 总数 141", len(ERROR_STATUS) == 141, len(ERROR_STATUS))
        check("VOLUME_OWNER_REQUIRED=403 / TWO_VOLUMES_REQUIRED=422 / MODEL_UNAVAILABLE=502 / IDEMPOTENCY_KEY_REQUIRED=428",
              (ERROR_STATUS["VOLUME_OWNER_REQUIRED"], ERROR_STATUS["TWO_VOLUMES_REQUIRED"], ERROR_STATUS["MODEL_UNAVAILABLE"],
               ERROR_STATUS["IDEMPOTENCY_KEY_REQUIRED"]) == (403, 422, 502, 428))
        live = httpx.get(base + "/openapi.json")
        if live.status_code == 200:
            check("运行中 OpenAPI == 去掉草案后的 spec/openapi/demo-v1.json", live.json() == implemented_contract(spec))

        # ---- 错误体 + 状态
        r = c.get("/api/v1/session")
        check("401 无 token /api/v1/session", r.status_code == 401 and r.json()["code"] == "UNAUTHENTICATED" and v1_body_ok(r), r.text)
        r = c.get("/api/v1/session", headers={"Authorization": "Bearer bogus"})
        check("401 伪造 token", r.status_code == 401 and v1_body_ok(r), r.text)
        mgr = login("alpha-manager")
        r = c.get(f"/api/v1/projects/{uuid4()}/workspace", headers=mgr)
        check("404 不存在项目 统一错误体", r.status_code == 404 and r.json()["code"] == "NOT_FOUND" and v1_body_ok(r), r.text)
        lib = c.get("/api/v1/library", headers=mgr).json()
        r = c.post("/api/v1/library", headers={**mgr, "If-Match": str(lib["revision"]), "Idempotency-Key": str(uuid4())}, json={"name": ""})
        check("422 VALIDATION_ERROR 统一错误体", r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR" and v1_body_ok(r), r.text)
        viewer = login("alpha-viewer")
        r = c.post("/api/v1/library", headers={**viewer, "If-Match": str(lib["revision"]), "Idempotency-Key": str(uuid4())},
                   json={"name": "查看人无权", "type": "qualification", "content": "合成。"})
        check("403 查看人写资料库", r.status_code == 403 and v1_body_ok(r) and ERROR_STATUS.get(r.json()["code"]) == 403, r.text)
        r = c.post("/api/v1/library", headers={**mgr, "If-Match": "999999", "Idempotency-Key": str(uuid4())},
                   json={"name": "旧版本", "type": "qualification", "content": "合成。"})
        check("409 过期 If-Match 统一错误体且状态与表一致", r.status_code == 409 and v1_body_ok(r) and ERROR_STATUS.get(r.json()["code"]) == 409, r.text)
        ids = set()
        for _ in range(5):
            ids.add(c.get("/api/v1/session").headers["x-request-id"])
        check("traceId 每次唯一", len(ids) == 5)
        r = c.get("/api/v1/session", headers={"X-Request-ID": "client-supplied"})
        check("客户端传入 X-Request-ID 不被采用", r.headers["x-request-id"] != "client-supplied" and v1_body_ok(r))

        # ---- 幂等
        def lib_rev(h): return c.get("/api/v1/library", headers=h).json()

        before = lib_rev(mgr)
        key = "qa-" + uuid4().hex
        payload = {"name": "QA幂等合成资料", "type": "qualification", "content": "QA 合成内容。", "valid_until": "2027-12-31",
                   "status": "confirmed", "reason": "QA 合成核对。"}
        h = {**mgr, "If-Match": str(before["revision"]), "Idempotency-Key": key}
        first = c.post("/api/v1/library", headers=h, json=payload)
        check("首次写入 200 且无重放头", first.status_code == 200 and "idempotent-replayed" not in first.headers, first.text)
        after1 = lib_rev(mgr)
        replay = c.post("/api/v1/library", headers=h, json=payload)
        after2 = lib_rev(mgr)
        check("同键同内容重放：状态+正文一致+重放头", replay.status_code == first.status_code and replay.json() == first.json()
              and replay.headers.get("idempotent-replayed") == "true", replay.text)
        check("重放无二次副作用（资料库版本/条数不变）", after1 == after2)
        conflict = c.post("/api/v1/library", headers=h, json={**payload, "content": "换了内容"})
        check("同键不同内容 409 IDEMPOTENCY_CONFLICT", conflict.status_code == 409 and conflict.json()["code"] == "IDEMPOTENCY_CONFLICT" and v1_body_ok(conflict), conflict.text)
        check("冲突无副作用", lib_rev(mgr) == after2)
        miss = c.post("/api/v1/library", headers={**mgr, "If-Match": str(after2["revision"])}, json=payload)
        check("缺键 428 IDEMPOTENCY_KEY_REQUIRED", miss.status_code == 428 and miss.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED" and v1_body_ok(miss), miss.text)
        for bad in ("short", "has space key", "x" * 121, "中文中文中文中文中文"):
            try:
                r = c.post("/api/v1/library", headers={**mgr, "If-Match": str(after2["revision"]), "Idempotency-Key": bad}, json=payload)
                check(f"非法键 {bad[:12]!r} -> 428", r.status_code == 428, r.status_code)
            except Exception as e:  # 非 ASCII 头 httpx 可能拒发
                check(f"非法键 {bad[:12]!r} 客户端拒发", "ascii" in str(e).lower() or "encode" in str(e).lower(), e)
        # 失败不登记
        k2 = "qa-fail-" + uuid4().hex
        rev = lib_rev(mgr)["revision"]
        bad = c.post("/api/v1/library", headers={**mgr, "If-Match": str(rev), "Idempotency-Key": k2},
                     json={"name": "失败", "type": "qualification", "content": " "})
        good = c.post("/api/v1/library", headers={**mgr, "If-Match": str(rev), "Idempotency-Key": k2},
                      json={"name": "失败", "type": "qualification", "content": "修正后的合成内容。"})
        check("失败(422)不登记，同键修正后 200 且非重放", bad.status_code == 422 and good.status_code == 200
              and "idempotent-replayed" not in good.headers, (bad.status_code, good.text))
        # 作用域：不同用户同键同内容不重放
        other = login("alpha-outsider-manager")
        rev = lib_rev(mgr)["revision"]
        k3 = "qa-scope-" + uuid4().hex
        p3 = {"name": "作用域合成", "type": "qualification", "content": "作用域合成内容。"}
        a = c.post("/api/v1/library", headers={**mgr, "If-Match": str(rev), "Idempotency-Key": k3}, json=p3)
        rev2 = lib_rev(other)["revision"]
        b = c.post("/api/v1/library", headers={**other, "If-Match": str(rev2), "Idempotency-Key": k3}, json=p3)
        check("不同用户同键：不重放（各自执行或按权限拒绝，绝不返回他人回执）",
              a.status_code == 200 and "idempotent-replayed" not in b.headers and (b.status_code != 200 or b.json() != a.json()),
              (a.status_code, b.status_code, b.text[:200]))
        # 并发重放：同键同内容并发 5 次，副作用只发生一次
        rev = lib_rev(mgr)
        k4 = "qa-race-" + uuid4().hex
        import concurrent.futures as cf
        p4 = {"name": "并发合成", "type": "qualification", "content": "并发合成内容。"}
        with cf.ThreadPoolExecutor(5) as ex:
            rs = list(ex.map(lambda _: httpx.post(base + "/api/v1/library", headers={**mgr, "If-Match": str(rev["revision"]), "Idempotency-Key": k4}, json=p4, timeout=20), range(5)))
        ok = [x for x in rs if x.status_code == 200]
        items = [i for i in lib_rev(mgr).get("items", []) if i.get("name") == "并发合成"]
        check("并发同键同内容：只产生一条记录", len(items) == 1, ([x.status_code for x in rs], len(items)))
        check("并发同键：成功响应正文一致", len({json.dumps(x.json(), sort_keys=True) for x in ok}) <= 1)

        # ---- 页面回退 / 路径穿越
        for p in ("/api", "/api/", "/api/nope", "/api/v1", "/api/v1/nope", "/api/v1/projects/x/nope", "/api/v2/x"):
            r = c.get(p)
            check(f"{p} -> JSON 404 非 HTML", r.status_code == 404 and r.headers.get("content-type", "").startswith("application/json"),
                  (r.status_code, r.headers.get("content-type")))
        r = c.get("/api/v1/nope")
        check("/api/v1 未知路径为统一错误体", v1_body_ok(r), r.text)
        secret = (ROOT / "backend/bid-core/icg_demo/main.py").read_bytes()[:60]
        for p in ("/%2e%2e/%2e%2e/%2e%2e/etc/passwd", "/..%2f..%2f..%2fetc%2fpasswd", "/%252e%252e/%252e%252e/etc/passwd",
                  "/assets/..%2f..%2f..%2f..%2fbackend%2fbid-core%2ficg_demo%2fmain.py", "/assets/%2e%2e/%2e%2e/%2e%2e/backend/bid-core/icg_demo/main.py",
                  "/static/%2e%2e/%2e%2e/etc/passwd", "/workbench/%2e%2e%2f%2e%2e%2f%2e%2e%2fbackend%2fbid-core%2ficg_demo%2fmain.py",
                  "/..\\..\\..\\etc\\passwd", "/%2e%2e%5c%2e%2e%5cetc%5cpasswd", "/assets/..%5c..%5c..%5cAGENTS.md"):
            st, ct, body = raw_get(port, p)
            leaked = b"root:x:" in body or secret in body or b"# AGENTS" in body[:200]
            check(f"穿越 {p} 未泄露（{st} {ct.split(';')[0]}）", not leaked and (st in (400, 404) or "text/html" in ct), (st, body[:80]))
        st, ct, body = raw_get(port, "/workbench/deep/link")
        check("深链接回退为 index.html", st == 200 and "text/html" in ct or st == 503, (st, ct))
    finally:
        proc.terminate(); proc.wait(10)
    failed = [n for n, ok in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
