# 为什么有这个文件：对实际启动的产品执行合成招标到两册下载的HTTP验收。
# 它解决什么问题：检查页面对应的真实端口，而不只在进程内测试，并留下可继续操作的合成项目。
import argparse
import base64
from io import BytesIO
import json
import sys
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

import httpx

from smoke_demo import authenticate, request


TENDER = ('合成招标文件：星河数据库维保项目\n招标编号：DEMO-2026-001\n'
          '投标截止时间：2026-12-31T17:00:00+08:00\n服务期限：12个月\n'
          '★技术要求：每月完成数据库巡检并提交报告。\n'
          '技术要求：重大故障响应不超过30分钟。\f'
          '商务要求：提供有效企业资质证明。\n商务要求：提供同类项目业绩证明。')
BODY = {
    'technical': '技术服务方案（合成验收）\n每月完成数据库巡检并提交报告，由项目负责人复核。\n重大故障在30分钟内响应，处理方案经双方核对后执行。\n全部内容仅用于测试。',
    'business': '商务响应（合成验收）\n企业资质与同类数据库维保业绩已逐项核对，对应合成证明材料。\n本项目编制技术、商务两册；全部内容仅用于测试。',
}


def word_text(content):
    with ZipFile(BytesIO(content)) as package:
        assert package.testzip() is None
        root = ElementTree.fromstring(package.read('word/document.xml'))
    return '\n'.join(item.text or '' for item in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))


def run(base_url, output_dir=None):
    # 该工具会创建和修改合成项目，只允许明确的本机验收地址。
    target = urlparse(base_url)
    if target.scheme != 'http' or target.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('此验收工具只运行在本机HTTP地址。')
    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
        editor, manager, viewer, beta = [authenticate(client, account) for account in
                                         ('alpha-editor', 'alpha-manager', 'alpha-viewer', 'beta-editor')]
        project = request(client, 'POST', '/api/projects', headers=editor,
                          payload={'name': 'ICG主流程HTTP验收（合成）-' + uuid4().hex[:6]}).json()
        path = '/api/v1/projects/' + project['id']

        def state():
            response = request(client, 'GET', path + '/workspace', headers=editor)
            assert response.headers['etag'] == '"' + str(response.json()['revision']) + '"'
            return response.json()

        def write(route, payload, method='POST', expected=200):
            return request(client, method, path + route, headers={**editor,
                           'If-Match': str(state()['revision']), 'Idempotency-Key': str(uuid4())},
                           payload=payload, expected=expected).json()

        write('', {'tender_number': 'DEMO-2026-001', 'deadline': '2026-12-31T09:00:00Z'}, 'PATCH')
        write('/files', {'filename': '合成招标.txt', 'content_base64': base64.b64encode(TENDER.encode()).decode()})
        write('/parse', {})
        for item in state()['requirements']:
            write('/requirements/' + item['id'], {'status': 'confirmed'}, 'PATCH')
        for item in state()['facts']:
            write('/facts/' + item['id'], {'status': 'confirmed', 'reason': '人工核对合成原文'}, 'PATCH')
        write('/parse/confirm', {})
        chapters = state()['chapters']
        evidence = []
        for kind, name in [('qualification', '合成企业资质证明'), ('performance', '合成维保项目业绩')]:
            library = request(client, 'GET', '/api/v1/library', headers=editor).json()
            item = request(client, 'POST', '/api/v1/library', headers={**editor,
                           'If-Match': str(library['revision']), 'Idempotency-Key': str(uuid4())},
                           payload={'name': name, 'type': kind, 'content': '完全虚构的测试证明材料。',
                                    'valid_until': '2027-12-31', 'status': 'confirmed', 'reason': '人工核对合成材料'}).json()['item']
            evidence.append(item)
        for item in state()['requirements']:
            chapter = next(c for c in chapters if c['volume'] == item['volume'])
            proof = [evidence[1 if '业绩' in item['text'] else 0]['id']] if item['volume'] == 'business' else []
            write('/requirements/' + item['id'], {'chapter_id': chapter['id'], 'response': '依据合成资料核对并按原文要求响应。',
                                                  'evidence_ids': proof}, 'PATCH')
        # 本章来源、矩阵与证据先整理好，再由当前负责账号确认方案。
        request(client, 'POST', path + '/plan', headers={**manager,
                'If-Match': str(state()['revision']), 'Idempotency-Key': str(uuid4())},
                payload={'chapters': [{'id': c['id'], 'title': c['title'], 'volume': c['volume']} for c in chapters]})
        for chapter in chapters:
            chapter_path = '/api/chapters/' + chapter['id']
            current = request(client, 'GET', chapter_path, headers=editor).json()
            lease = request(client, 'POST', chapter_path + '/lock', headers=editor, payload={}).json()
            request(client, 'POST', chapter_path + '/versions', headers=editor,
                    payload={'lease_token': lease['lease_token'], 'input_fingerprint': state()['input_fingerprint'], 'base_revision': current['revision'],
                             'content': BODY[chapter['volume']], 'idempotency_key': str(uuid4())})
            request(client, 'POST', chapter_path + '/lock/release', headers=editor, payload={'lease_token': lease['lease_token']})
        request(client, 'GET', path + '/workspace', headers=beta, expected=404)
        request(client, 'POST', path + '/checks', headers={**viewer, 'If-Match': str(state()['revision']),
                'Idempotency-Key': str(uuid4())}, payload={'volume': 'all'}, expected=403)
        # 为页面恢复验收保留经理旧草稿：另一账号提交后，它必须保持旧版，不能自动盖过正文。
        technical = next(c for c in chapters if c['volume'] == 'technical')
        chapter_path = '/api/chapters/' + technical['id']
        current = request(client, 'GET', chapter_path, headers=manager).json()
        lease = request(client, 'POST', chapter_path + '/lock', headers=manager, payload={}).json()
        request(client, 'PUT', chapter_path + '/draft', headers=manager,
                payload={'lease_token': lease['lease_token'], 'input_fingerprint': state()['input_fingerprint'], 'base_revision': current['revision'], 'sequence': 1,
                         'content': BODY['technical'] + '\n旧草稿独立核对记录（合成）。'})
        request(client, 'POST', chapter_path + '/lock/release', headers=manager, payload={'lease_token': lease['lease_token']})
        lease = request(client, 'POST', chapter_path + '/lock', headers=editor, payload={}).json()
        request(client, 'POST', chapter_path + '/versions', headers=editor,
                payload={'lease_token': lease['lease_token'], 'input_fingerprint': state()['input_fingerprint'], 'base_revision': current['revision'],
                         'content': BODY['technical'], 'idempotency_key': str(uuid4())})
        request(client, 'POST', chapter_path + '/lock/release', headers=editor, payload={'lease_token': lease['lease_token']})
        assert request(client, 'GET', chapter_path, headers=manager).json()['draft']['base_revision'] < state()['chapters'][0]['revision']

        check = write('/checks', {'volume': 'all'})['check']
        assert check['passed'] and not check['coverage']['complete']
        exported = write('/exports', {'check_id': check['id'], 'kind': 'internal'})['export']
        downloaded = []
        for entry in exported['volumes']:
            data = request(client, 'GET', entry['download_url'], headers=editor).content
            text = word_text(data)
            assert BODY[entry['volume']] in text
            assert BODY['business' if entry['volume'] == 'technical' else 'technical'] not in text
            if output_dir:
                destination = Path(output_dir) / project['id']
                destination.mkdir(parents=True, exist_ok=True)
                (destination / entry['filename']).write_bytes(data)
            downloaded.append({'volume': entry['volume'], 'bytes': len(data)})
        return {'passed': True, 'project_id': project['id'], 'project_name': project['name'], 'downloads': downloaded,
                'complete_reference': False, 'word_layout_verified': False, 'manager_draft_base_revision': current['revision']}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='本机合成ICG主流程HTTP验收，不代表完整产品验收。')
    parser.add_argument('--base-url', default='http://127.0.0.1:8710')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    print(json.dumps(run(args.base_url, args.output_dir), ensure_ascii=False))
