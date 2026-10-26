# 为什么有这个文件：向后兼容转接层，重导出 icg.domain.outline_plan, icg.domain.outline_service。
# 它解决什么问题：落实去平铺架构与官方拍板 B1，保持现有测试与外部引用的零中断兼容。

from icg.domain.outline_plan import *
from icg.domain.outline_service import *

import sys
import icg.domain.outline_plan as _src_0
globals().update({_k: _v for _k, _v in _src_0.__dict__.items() if not _k.startswith('__')})
import sys
import icg.domain.outline_service as _src_1
globals().update({_k: _v for _k, _v in _src_1.__dict__.items() if not _k.startswith('__')})

sys.modules[__name__] = _src_0
