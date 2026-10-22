# 为什么有这个文件：持久化仓储的通用辅助函数与时间/JSON 转换。
# 它解决什么问题：统一 MySQL 时间戳、UTC 时区、JSON 字段序列化与连接解包逻辑。

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def utc_naive(timestamp: float) -> datetime:
    """将 Unix 时间戳转为无时区信息的 UTC datetime。"""
    return datetime.fromtimestamp(float(timestamp), timezone.utc).replace(tzinfo=None)


def as_timestamp(value: datetime) -> float:
    """将 datetime 转为 UTC 时间戳。"""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def parse_db_timestamp(val: Any) -> float | None:
    """安全解析数据库中可能是 float、int 或 datetime 的时间字段为 Unix 时间戳。"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, datetime):
        return as_timestamp(val)
    return None


def to_utc_naive(val: Any) -> datetime | None:
    """将各种输入格式转换为 naive UTC datetime。"""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            return val.astimezone(timezone.utc).replace(tzinfo=None)
        return val
    try:
        return datetime.fromtimestamp(float(val), timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def json_value(value: Any) -> Any:
    """安全反序列化 JSON 字符串或直接返回对象。"""
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    return value


# 兼容内部下划线私有函数别名
_utc_naive = utc_naive
_as_timestamp = as_timestamp
_parse_db_timestamp = parse_db_timestamp
_to_utc_naive = to_utc_naive
_json_value = json_value
