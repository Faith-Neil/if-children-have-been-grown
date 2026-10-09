# 为什么有这个文件：从实际后端代码导出请求和响应约定。
# 它解决什么问题：避免接口文档与可运行代码采用两套字段。
import json
from pathlib import Path
from icg_demo.main import app

if __name__ == '__main__':
    target = Path(__file__).resolve().parents[2] / 'spec' / 'openapi' / 'demo-v1.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'OpenAPI exported: {target.name}')
