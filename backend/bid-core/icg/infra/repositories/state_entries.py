# 为什么有这个文件：把仍只在进程内存里的业务状态（项目工作流、账号、资料库、SLA 模板、任务、审计、RAGFlow 配置、
# 公司设置/字典/方案片段等服务存储）按“范围 + 条目”写入 MySQL 表 demo_state_entry（ISSUE-041）。
# 它解决什么问题：
# 1. 生产 ICG_REQUIRE_MYSQL=1 下重启或多进程不再丢失解析条款、矩阵、检查、导出、用户与资料；
# 2. 每个条目带 rev，写入按 rev 乐观锁，另一进程先改了同一条目时本次事务整体失败（409），不会静默覆盖；
# 3. 读取只比较 rev，只有变化的条目才取正文并反序列化，避免每个事务都解析全部大对象。

from __future__ import annotations

import base64
import json
from dataclasses import asdict, fields, is_dataclass
from typing import Any, Callable

from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError

from icg.domain.domain import Account, DemoState, DomainError

TABLE = "demo_state_entry"


# ---------------------------------------------------------------- 编码

def _encode(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        return {"__b64__": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, (set, frozenset)):
        return {"__set__": sorted((_encode(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True, default=str))}
    if isinstance(value, tuple):
        return {"__tuple__": [_encode(v) for v in value]}
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"状态条目含非字符串键：{key!r}")
            out[key] = _encode(item)
        return out
    if isinstance(value, list):
        return [_encode(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return {"__pydantic__": _encode(value.model_dump())}
    if is_dataclass(value):
        return _encode(asdict(value))
    raise TypeError(f"状态条目含无法持久化的类型：{type(value).__name__}")


def _decode(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {"__b64__"}:
            return base64.b64decode(value["__b64__"])
        if set(value) == {"__set__"}:
            return {_decode(v) for v in value["__set__"]}
        if set(value) == {"__tuple__"}:
            return tuple(_decode(v) for v in value["__tuple__"])
        if set(value) == {"__pydantic__"}:
            return _decode(value["__pydantic__"])
        return {key: _decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


def dumps(value: Any) -> str:
    # 不排序键：工作流里的条款、章节等字典依赖插入顺序（界面顺序与 PRD 条款顺序），重载后必须一致。
    return json.dumps(_encode(value), ensure_ascii=False, separators=(",", ":"))


def loads(raw: str | bytes) -> Any:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    return _decode(json.loads(raw))


def _account_from(data: dict) -> Account:
    allowed = {f.name for f in fields(Account)}
    return Account(**{k: v for k, v in data.items() if k in allowed})


def _ragflow_from(data: dict) -> Any:
    from icg.domain.ragflow_config import RagflowCompanyConfig
    allowed = {f.name for f in fields(RagflowCompanyConfig)}
    return RagflowCompanyConfig(**{k: v for k, v in data.items() if k in allowed})


# ---------------------------------------------------------------- 范围定义
# 每个范围：取出“条目字典”的函数，以及把解码后的数据还原成内存对象的函数。

def _dict_scope(attribute: str, rebuild: Callable[[Any], Any] | None = None):
    def get(state: DemoState) -> dict:
        current = getattr(state, attribute, None)
        if current is None:
            current = {}
            setattr(state, attribute, current)
        return current
    return get, (rebuild or (lambda data: data))


def _audit_get(state: DemoState) -> dict:
    return {str(event.get("id")): event for event in state.audit if event.get("id")}


def _singleton_get(state: DemoState) -> dict:
    return {"library_revisions": state.library_revisions, "resource_acl": state.resource_acl}


SCOPES: dict[str, tuple[Callable[[DemoState], dict], Callable[[Any], Any]]] = {
    "workflow": _dict_scope("workflows"),
    "account": _dict_scope("accounts", _account_from),
    "library": _dict_scope("library"),
    "sla_template": _dict_scope("sla_templates"),
    "job": _dict_scope("jobs"),
    "partners": _dict_scope("project_partners"),
    "ragflow_config": _dict_scope("ragflow_configs", _ragflow_from),
    "service_store": _dict_scope("service_stores"),
    "security_audit": _dict_scope("security_audit"),
    "audit": (_audit_get, lambda data: data),
    "singleton": (_singleton_get, lambda data: data),
}


def snapshot(state: DemoState) -> dict[tuple[str, str], str]:
    result: dict[tuple[str, str], str] = {}
    for scope, (get, _rebuild) in SCOPES.items():
        for entry_id, value in get(state).items():
            result[(scope, str(entry_id))] = dumps(value)
    return result


def _apply(state: DemoState, scope: str, entry_id: str, value: Any | None) -> None:
    get, rebuild = SCOPES[scope]
    if scope == "audit":
        events = [event for event in state.audit if str(event.get("id")) != entry_id]
        if value is not None:
            events.append(value)
            events.sort(key=lambda event: str(event.get("at", "")))
        state.audit[:] = events
        return
    if scope == "singleton":
        if value is None:
            return
        if entry_id == "library_revisions":
            state.library_revisions.clear()
            state.library_revisions.update(value)
        elif entry_id == "resource_acl":
            state.resource_acl[:] = value
        return
    target = get(state)
    if value is None:
        target.pop(entry_id, None)
    else:
        target[entry_id] = rebuild(value)


class StateEntryStore:
    """按 rev 缓存的条目读写器，由 MysqlConnectionRepository 在每个事务前后调用。"""

    def __init__(self) -> None:
        self.cache: dict[tuple[str, str], tuple[int, str]] = {}
        # 首次成功读取条目表之前不写入（旧库缺表，或测试替换了加载步骤）。
        self.available = False

    def load(self, connection: Any, state: DemoState, *, remember: bool) -> list[tuple[str, str]]:
        """把库里有变化的条目应用到 state。remember=False 用于只读快照，不改缓存。

        返回本次改动过缓存的键；事务失败时调用 forget() 让这些键下次重新加载。
        """
        try:
            rows = connection.execute(text(f"SELECT scope, entry_id, rev FROM {TABLE}")).all()
        except Exception as error:  # 未执行 0012 的旧库
            if TABLE in str(error):
                self.available = False
                return []
            raise
        self.available = True
        seen = {(scope, entry_id): int(rev) for scope, entry_id, rev in rows if scope in SCOPES}
        stale = [key for key, rev in seen.items() if self.cache.get(key, (None,))[0] != rev]
        fetched: dict[tuple[str, str], tuple[int, str]] = {}
        by_scope: dict[str, list[str]] = {}
        for scope, entry_id in stale:
            by_scope.setdefault(scope, []).append(entry_id)
        statement = text(f"SELECT entry_id, rev, body FROM {TABLE} WHERE scope = :scope AND entry_id IN :ids") \
            .bindparams(bindparam("ids", expanding=True))
        for scope, ids in by_scope.items():
            for start in range(0, len(ids), 500):
                for entry_id, rev, body in connection.execute(statement, {"scope": scope, "ids": ids[start:start + 500]}).all():
                    body_text = body.decode("utf-8") if isinstance(body, (bytes, bytearray)) else body
                    fetched[(scope, entry_id)] = (int(rev), body_text)
        removed = [key for key in self.cache if key not in seen]
        for key in removed:
            _apply(state, key[0], key[1], None)  # 另一进程已删除
        for (scope, entry_id), (_rev, body_text) in fetched.items():
            _apply(state, scope, entry_id, loads(body_text))
        if not remember:
            return []
        for key in removed:
            del self.cache[key]
        self.cache.update(fetched)
        return list(fetched) + removed

    def forget(self, keys: list[tuple[str, str]]) -> None:
        for key in keys:
            self.cache.pop(key, None)

    def save(self, connection: Any, before: dict[tuple[str, str], str],
             after: dict[tuple[str, str], str]) -> dict[tuple[str, str], tuple[int, str] | None]:
        """写入有变化的条目；返回提交成功后要更新的缓存。"""
        if not self.available:
            return {}
        updates: dict[tuple[str, str], tuple[int, str] | None] = {}
        for key in set(before) | set(after):
            previous, current = before.get(key), after.get(key)
            if previous == current:
                continue
            scope, entry_id = key
            known = self.cache.get(key)
            if current is None:
                if known is not None:
                    deleted = connection.execute(text(
                        f"DELETE FROM {TABLE} WHERE scope = :scope AND entry_id = :id AND rev = :rev"
                    ), {"scope": scope, "id": entry_id, "rev": known[0]})
                    if deleted.rowcount != 1:
                        raise DomainError(409, "VERSION_CONFLICT", "数据已被其他会话更新，请刷新后重试。")
                updates[key] = None
                continue
            if known is None:
                try:
                    connection.execute(text(
                        f"INSERT INTO {TABLE} (scope, entry_id, rev, body, updated_at) "
                        "VALUES (:scope, :id, 1, :body, UTC_TIMESTAMP(6))"
                    ), {"scope": scope, "id": entry_id, "body": current})
                except IntegrityError as error:
                    raise DomainError(409, "VERSION_CONFLICT", "数据已被其他会话更新，请刷新后重试。") from error
                updates[key] = (1, current)
            else:
                changed = connection.execute(text(
                    f"UPDATE {TABLE} SET body = :body, rev = rev + 1, updated_at = UTC_TIMESTAMP(6) "
                    "WHERE scope = :scope AND entry_id = :id AND rev = :rev"
                ), {"scope": scope, "id": entry_id, "rev": known[0], "body": current})
                if changed.rowcount != 1:
                    raise DomainError(409, "VERSION_CONFLICT", "数据已被其他会话更新，请刷新后重试。")
                updates[key] = (known[0] + 1, current)
        return updates

    def commit(self, updates: dict[tuple[str, str], tuple[int, str] | None]) -> None:
        for key, value in updates.items():
            if value is None:
                self.cache.pop(key, None)
            else:
                self.cache[key] = value
