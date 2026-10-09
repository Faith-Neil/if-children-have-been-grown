# 为什么有这个文件：让后台回归直接导入本仓库真实的demo应用。
# 它解决什么问题：后端目录名带连字符且未安装为包，测试仍能使用同一实际实现。
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend" / "bid-core"
sys.path.insert(0, str(BACKEND_ROOT))
