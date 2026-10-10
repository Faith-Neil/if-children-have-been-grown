# 为什么有这个文件：在真实本机端口核对服务承诺从模板、原文到检查和Word的协作。
# 它解决什么问题：证明前后端共同接口能办成事，并留下可以在页面继续查看的合成项目。
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

import httpx

from smoke_demo import authenticate, request
from smoke_reference import run as create_reference_project, word_text


def run(base_url, output_dir=None):
    target = urlparse(base_url)
    if target.scheme != 'http' or target.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('此工具只使用本机HTTP地址和新建合成项目。')
    seeded = create_reference_project(base_url)
    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
        manager, editor, beta = [authenticate(client, account) for account in
                                 ('alpha-manager', 'alpha-editor', 'beta-editor')]
        path = '/api/v1/projects/' + seeded['project_id']

        def state():
            return request(client, 'GET', path + '/workspace', headers=manager).json()

        def write(route, payload, method='POST', expected=200, actor=None):
            return request(client, method, path + route, headers={**(actor or manager),
                           'If-Match': str(state()['revision']), 'Idempotency-Key': str(uuid4())},
                           payload=payload, expected=expected).json()

        library_version = request(client, 'GET', '/api/v1/sla/templates', headers=manager).json()['revision']
        template = request(client, 'POST', '/api/v1/sla/templates', headers={**manager,
                           'If-Match': str(library_version), 'Idempotency-Key': str(uuid4())}, payload={
            'name': '合成服务承诺模板-' + uuid4().hex[:6], 'edition': 'standard',
            'version_no': '1.0', 'service_hours': 'h7x24',
            'body_text': '一级故障响应时限为{{P1.response}}。',
            'status': 'confirmed', 'reason': '合成验收值，不表示任何真实公司的能力。',
            'variables': [{'var_key': 'P1.response', 'label': '一级故障响应时限', 'group': 'response',
                           'value_type': 'integer', 'default_value': '30', 'unit': 'minute',
                           'compare_direction': 'lower_better', 'best_committable_value': '15'}],
        }).json()['item']
        assert template['id'] not in {item['id'] for item in request(
            client, 'GET', '/api/v1/sla/templates', headers=beta).json()['items']}
        write('/sla/template', {'template_id': template['id'], 'reason': '合成流程验收'})
        response_requirement = next(item for item in state()['requirements'] if '重大故障' in item['text'])
        write('/requirements/' + response_requirement['id'], {'category': 'sla'}, 'PATCH')
        binding = {'requirement_id': response_requirement['id'], 'tender_required_value': '30',
                   'tender_unit': 'minute', 'project_unit': 'minute',
                   'reason': '已逐项核对合成原文的30分钟要求。'}
        route = '/sla/values/P1.response'
        write(route, {**binding, 'project_value': '60'}, 'PATCH')
        assert state()['sla']['rows'][0]['judgment'] == 'not_satisfied'
        write(route + '/review', {'reason': '不能批准不满足条目'}, expected=409)
        write('/sla/apply-tender', {})
        assert state()['sla']['rows'][0]['project_value'] == '30'
        write(route, {'project_value': '10', 'reason': '合成超能力风险场景'}, 'PATCH')
        assert state()['sla']['rows'][0]['judgment'] == 'exceeds_capability'
        write(route + '/review', {'reason': '普通编写人无权批准'}, expected=403, actor=editor)
        write('/sla/commitment', {}, expected=409)
        write(route + '/review', {'reason': '合成负责人确认风险；正式履约能力须另核实。'})
        fact = next(item for item in state()['facts'] if item.get('source_type') == 'sla')
        write('/facts/' + fact['id'], {'value': '9'}, 'PATCH', expected=409)
        write('/facts/' + fact['id'], {'status': 'confirmed', 'reason': '逐项核对合成承诺'}, 'PATCH')
        write('/parse/confirm', {})
        chapters = state()['chapters']
        write('/plan', {'chapters': [{k: item[k] for k in ('id', 'title', 'volume')} for item in chapters]})
        technical = next(item for item in state()['chapters'] if item['volume'] == 'technical')
        chapter_path = '/api/chapters/' + technical['id']
        lease = request(client, 'POST', chapter_path + '/lock', headers=manager, payload={}).json()
        content = '技术服务方案（合成验收）\n每月完成数据库巡检并提交报告。\n一级故障响应时限：{{sla:P1.response}}。\n全部内容仅用于测试。'
        request(client, 'POST', chapter_path + '/versions', headers=manager, payload={
            'lease_token': lease['lease_token'], 'base_revision': technical['revision'],
            'content': content, 'idempotency_key': str(uuid4())})
        request(client, 'POST', chapter_path + '/lock/release', headers=manager,
                payload={'lease_token': lease['lease_token']})
        check = write('/checks', {'volume': 'all'})['check']
        assert check['passed'] and not check['coverage']['complete'], check['issues']
        volumes = write('/exports', {'check_id': check['id'], 'kind': 'internal'})['export']
        commitment = write('/sla/commitment', {})['commitment']
        downloads = []
        for entry in [*volumes['volumes'], commitment]:
            data = request(client, 'GET', entry['download_url'], headers=manager).content
            text = word_text(data)
            assert '{{sla:' not in text
            if entry.get('volume') != 'business':
                assert '一级故障响应时限' in text and '10' in text
            if entry is commitment:
                with ZipFile(BytesIO(data)) as package:
                    xml = ElementTree.fromstring(package.read('word/document.xml'))
                assert list(xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl'))
            if output_dir:
                destination = Path(output_dir) / seeded['project_id']
                destination.mkdir(parents=True, exist_ok=True)
                (destination / entry['filename']).write_bytes(data)
            downloads.append({'filename': entry['filename'], 'bytes': len(data)})
        write(route, {'project_value': '20', 'reason': '验证修改后旧确认和下载失效'}, 'PATCH')
        assert next(item for item in state()['facts'] if item['id'] == fact['id'])['status'] == 'needs_review'
        request(client, 'GET', commitment['download_url'], headers=manager, expected=409)
        request(client, 'GET', volumes['volumes'][0]['download_url'], headers=manager, expected=409)
        # 保留最后的需复核状态，便于页面直观看见失效保护，不假装已重新确认。
        return {**seeded, 'sla_http_passed': True, 'final_sla_value': '20', 'final_fact_status': 'needs_review',
                'sla_downloads': downloads, 'complete_reference': False, 'word_layout_verified': False}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='真实本机服务承诺闭环验收，全部为合成数据。')
    parser.add_argument('--base-url', default='http://127.0.0.1:8710')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    print(json.dumps(run(args.base_url, args.output_dir), ensure_ascii=False))
