# 为什么有这个文件：对已经监听本地端口的真实后台执行一条完整HTTP验收链路。
# 它解决什么问题：确保登录、公司隔离、锁、版本、检查和下载不只在模拟页面中成功。
import argparse
from io import BytesIO
import json
from uuid import uuid4
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import httpx


def request(client, method, url, *, headers=None, payload=None, expected=200):
    response = client.request(method, url, headers=headers, json=payload)
    if response.status_code != expected:
        raise RuntimeError(f"{method} {url}: expected {expected}, got {response.status_code}")
    return response


def authenticate(client, account):
    result = request(client, "POST", "/api/demo/login", payload={"account_id": account})
    return {"Authorization": "Bearer " + result.json()["access_token"]}


def run(base_url):
    with httpx.Client(base_url=base_url, timeout=10, trust_env=False) as client:
        request(client, "GET", "/api/projects", expected=401)
        accounts = request(client, "GET", "/api/demo/accounts").json()["accounts"]
        editor = authenticate(client, "alpha-editor")
        manager = authenticate(client, "alpha-manager")
        viewer = authenticate(client, "alpha-viewer")
        beta = authenticate(client, "beta-editor")
        projects = request(client, "GET", "/api/projects", headers=beta).json()["projects"]
        assert "alpha-project" not in {project["id"] for project in projects}
        assert {chapter["id"] for chapter in request(
            client, "GET", "/api/projects/alpha-project/chapters", headers=editor
        ).json()["chapters"]} >= {"alpha-tech", "alpha-business"}
        # 每次在合成新项目中验收，避免改变页面正在演示的种子项目或继承上次失败的锁。
        project = request(client, "POST", "/api/projects", headers=editor,
                          payload={"name": "HTTP合成验收-" + uuid4().hex[:8]}).json()
        chapters = request(client, "GET", f"/api/projects/{project['id']}/chapters",
                           headers=editor).json()["chapters"]
        assert {item["volume"] for item in chapters} == {"technical", "business"}
        chapter_id = next(item["id"] for item in chapters if item["volume"] == "technical")
        chapter_url = "/api/chapters/" + chapter_id
        chapter = request(client, "GET", chapter_url, headers=editor).json()
        editor_lease = request(client, "POST", chapter_url + "/lock", headers=editor,
                               payload={"takeover_reason": None}).json()["lease_token"]
        request(client, "PUT", chapter_url + "/draft", headers=viewer,
                payload={"lease_token": editor_lease, "base_revision": chapter["revision"],
                         "sequence": 1, "content": "无权写入"}, expected=403)
        manager_lease = request(client, "POST", chapter_url + "/lock", headers=manager,
                                payload={"takeover_reason": "HTTP合成验收接管"}).json()["lease_token"]
        rejected = client.put(chapter_url + "/draft", headers=editor,
                              json={"lease_token": editor_lease, "base_revision": chapter["revision"],
                                    "sequence": 1, "content": "旧锁不得写入"})
        assert rejected.status_code == 423
        before_suggestion = request(client, "GET", chapter_url, headers=manager).json()
        suggestion = request(client, "POST", chapter_url + "/suggestions", headers=manager,
                             payload={"instruction": "补充巡检说明"}).json()
        assert suggestion["provider"] == "demo" and suggestion["is_real_model"] is False
        assert request(client, "GET", chapter_url, headers=manager).json() == before_suggestion
        content = "HTTP验收使用合成资料：建立巡检、备份验证与问题闭环并保留完整记录。"
        submission = {"lease_token": manager_lease, "base_revision": before_suggestion["revision"],
                      "content": content, "idempotency_key": "http-smoke-" + str(uuid4())}
        version = request(client, "POST", chapter_url + "/versions", headers=manager,
                          payload=submission).json()
        repeated = request(client, "POST", chapter_url + "/versions", headers=manager,
                           payload=submission).json()
        assert repeated == version
        check = request(client, "POST", chapter_url + "/checks", headers=manager, payload={}).json()
        assert check["passed"] is True
        exported = request(client, "POST", chapter_url + "/exports", headers=manager,
                           payload={"check_id": check["id"]}).json()
        output = request(client, "GET", exported["download_url"], headers=manager)
        with ZipFile(BytesIO(output.content)) as document:
            assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= set(document.namelist())
            for name in ["[Content_Types].xml", "_rels/.rels", "word/document.xml"]:
                ET.fromstring(document.read(name))
            assert content in "".join(ET.fromstring(document.read("word/document.xml")).itertext())
        current = request(client, "GET", chapter_url, headers=manager).json()
        request(client, "POST", chapter_url + "/versions", headers=manager,
                payload={"lease_token": manager_lease, "base_revision": current["revision"],
                         "content": content + "提交后的新正文。", "idempotency_key": "http-smoke-" + str(uuid4())})
        request(client, "POST", chapter_url + "/exports", headers=manager,
                payload={"check_id": check["id"]}, expected=409)
        request(client, "GET", exported["download_url"], headers=manager, expected=409)
        request(client, "POST", chapter_url + "/lock/release", headers=manager,
                payload={"lease_token": manager_lease})
        return {"http_smoke": "passed", "demo_accounts": len(accounts),
                "docx_bytes": len(output.content), "real_model_called": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="验证已运行后台的真实HTTP与Word输出")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    args = parser.parse_args()
    print(json.dumps(run(args.base_url), ensure_ascii=False))
