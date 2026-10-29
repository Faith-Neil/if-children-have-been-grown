# 为什么有这个文件：APP-M1-T06端到端冒烟，自启本机后台跑完E1～E7并交叉核对接口读回与两册Word内容。
# 它解决什么问题：原证据分散在多个smoke_*脚本且需手动起服务；本脚本一次贯通、只用合成数据、退出码0/1可供CI使用。

import argparse
import json
import socket
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

import httpx

from smoke_demo import authenticate, request
from smoke_members import run as run_members
from smoke_reference import word_text

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
APP_DIR = Path(__file__).resolve().parent


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def inspect_docx(payload):
    """只用标准库读取页面设置、字体、样式、表格与标题，供版式核对；不判定视觉效果。"""
    with ZipFile(BytesIO(payload)) as package:
        names = set(package.namelist())
        document = ElementTree.fromstring(package.read('word/document.xml'))
        styles = ElementTree.fromstring(package.read('word/styles.xml')) if 'word/styles.xml' in names else None
    size = document.find(f'.//{W}sectPr/{W}pgSz')
    margin = document.find(f'.//{W}sectPr/{W}pgMar')
    fonts = styles.find(f'.//{W}rPrDefault//{W}rFonts') if styles is not None else None
    style_ids = sorted(s.get(W + 'styleId') for s in styles.iter(W + 'style')) if styles is not None else []
    used = sorted({p.get(W + 'val') for p in document.iter(W + 'pStyle')})
    tables = list(document.iter(W + 'tbl'))
    return {
        'page_size_twips': [size.get(W + 'w'), size.get(W + 'h')] if size is not None else None,
        'margins_twips': {k: margin.get(W + k) for k in ('top', 'right', 'bottom', 'left')} if margin is not None else None,
        'default_fonts': {k: fonts.get(W + k) for k in ('ascii', 'eastAsia', 'hAnsi')} if fonts is not None else None,
        'style_ids': style_ids, 'paragraph_styles_used': used,
        'heading_styles_used': [s for s in used if s and s.lower().startswith('heading')],
        'has_numbering_part': 'word/numbering.xml' in names,
        'has_toc_field': any('TOC' in (n.text or '') for n in document.iter(W + 'instrText'))
                         or any((f.get(W + 'instr') or '').strip().startswith('TOC') for f in document.iter(W + 'fldSimple')),
        'has_header_footer': any(n.startswith('word/header') or n.startswith('word/footer') for n in names),
        'tables': len(tables),
        'tables_with_header_repeat': sum(1 for t in tables if t.find(f'.//{W}tblHeader') is not None),
    }


def run(base_url, output_dir=None):
    checks = []

    def check(name, ok, detail=''):
        checks.append({'name': name, 'pass': bool(ok), 'detail': detail})

    # E1～E6：项目/团队、上传解析、人工确认、矩阵、逐节方案生成提交、检查导出下载（复用已验收冒烟）。
    with_dir = output_dir or None
    members = run_members(base_url, with_dir)
    check('E1-E6 smoke_members/reference passed', members['passed'], members['project_id'])
    project_id, chapters = members['project_id'], members['chapters']
    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
        manager, assembly, outsider = [authenticate(client, a) for a in ('alpha-manager', 'alpha-editor', 'alpha-outsider-manager')]
        path = '/api/v1/projects/' + project_id
        workspace = request(client, 'GET', path + '/workspace', headers=manager).json()
        check('E7 workspace name readback', workspace['project']['name'] == members['project_name'], workspace['project']['name'])
        exports = workspace.get('exports') or []
        current = next((e for e in exports if e['id'] == members['export_id']), None)
        check('E7 export listed in workspace', current is not None, str([e.get('id') for e in exports]))
        docs, layout = {}, {}
        for entry in (current or {}).get('volumes', []):
            payload = request(client, 'GET', entry['download_url'], headers=manager).content
            docs[entry['volume']] = (entry, payload)
            layout[entry['volume']] = inspect_docx(payload)
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                (Path(output_dir) / entry['filename']).write_bytes(payload)
        check('E7 two volumes downloaded', set(docs) == {'technical', 'business'}, str(sorted(docs)))
        for volume, chapter_id in chapters.items():
            chapter = request(client, 'GET', '/api/chapters/' + chapter_id, headers=manager).json()
            committed = (chapter.get('content') or '').strip()
            text = word_text(docs[volume][1]) if volume in docs else ''
            check(f'E7 {volume} committed content == Word text', committed and committed in text,
                  f'api {len(committed)} chars; word {len(text)} chars')
            check(f'E7 {volume} private draft absent from Word', '私有交接草稿' not in text)
            other = 'business' if volume == 'technical' else 'technical'
            other_body = (request(client, 'GET', '/api/chapters/' + chapters[other], headers=manager).json().get('content') or '').strip()
            check(f'E7 {volume} Word excludes other volume body', other_body not in text)
        for volume, (entry, _) in docs.items():
            request(client, 'GET', entry['download_url'], headers=outsider, expected=404)
        check('E7 outsider cannot download (404)', True)
        # 过期：新提交正文后旧导出不可下载。
        tech_url = '/api/chapters/' + chapters['technical']
        tech = authenticate(client, 'alpha-tech')
        chapter = request(client, 'GET', tech_url, headers=tech).json()
        lease = request(client, 'POST', tech_url + '/lock', headers=tech, payload={}).json()['lease_token']
        fp = request(client, 'GET', path + '/workspace', headers=manager).json()['input_fingerprint']
        request(client, 'POST', tech_url + '/versions', headers=tech, payload={'lease_token': lease,
                'base_revision': chapter['revision'], 'content': chapter['content'] + '新增：季度复盘。',
                'input_fingerprint': fp, 'idempotency_key': str(uuid4())})
        request(client, 'POST', tech_url + '/lock/release', headers=tech, payload={'lease_token': lease})
        # PRD §5.9.1 规则 13（APP-M2-T202）：新提交后旧批次标“已过期”，仍提供当时生成的原文件
        old = client.get(docs['technical'][0]['download_url'], headers=manager) if 'technical' in docs else None
        stale = (old.status_code, old.headers.get('X-ICG-Export-Status')) if old is not None else None
        check('E7 old export marked stale after new commit but still downloadable', stale == (200, 'stale'), str(stale))
    return {'passed': all(c['pass'] for c in checks), 'project_id': project_id, 'checks': checks,
            'layout': layout, 'real_model_called': False, 'word_layout_verified': False}


def main():
    parser = argparse.ArgumentParser(description='APP-M1-T06端到端冒烟：自启本机后台，合成数据。')
    parser.add_argument('--base-url', help='已运行的本机后台；省略则自启空闲端口')
    parser.add_argument('--output-dir', help='保存两册Word，供版式人工核对（工作区外）')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    server = None
    base_url = args.base_url
    if not base_url:
        port = free_port()
        base_url = f'http://127.0.0.1:{port}'
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'icg_demo.main:app', '--app-dir', str(APP_DIR),
                                   '--host', '127.0.0.1', '--port', str(port), '--workers', '1'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                httpx.get(base_url + '/health', timeout=1, trust_env=False)
                break
            except httpx.TransportError:
                time.sleep(0.1)
    try:
        result = run(base_url, args.output_dir)
    except Exception as error:  # 任一步失败即非零退出并打印原因
        result = {'passed': False, 'error': f'{type(error).__name__}: {error}'}
    finally:
        if server:
            server.terminate()
            server.wait(timeout=10)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
