# 为什么有这个文件：在实际本机服务验证本章方案、事实输入、候选快照与两册输出一起工作。
# 它解决什么问题：证明模型替身真正收到选定事实和当前承诺，而不是只在页面展示这些字段。
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from smoke_demo import authenticate, request
from smoke_reference import word_text
from smoke_sla import run as create_sla_project


def run(base_url, output_dir=None):
    target = urlparse(base_url)
    if target.scheme != 'http' or target.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('此工具只在本机创建合成验收项目。')
    seeded = create_sla_project(base_url)
    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
        manager, editor, beta = [authenticate(client, account) for account in
                                 ('alpha-manager', 'alpha-editor', 'beta-editor')]
        path = '/api/v1/projects/' + seeded['project_id']

        def state():
            return request(client, 'GET', path + '/workspace', headers=manager).json()

        def write(route, payload, method='POST', actor=None, expected=200):
            return request(client, method, path + route, headers={**(actor or manager),
                           'If-Match': str(state()['revision']), 'Idempotency-Key': str(uuid4())},
                           payload=payload, expected=expected).json()

        name = 'ICG写作输入HTTP验收（合成）-' + uuid4().hex[:6]
        write('', {'name': name}, 'PATCH')
        sla_fact = next(f for f in state()['facts'] if f.get('source_type') == 'sla')
        write('/facts/' + sla_fact['id'], {'status': 'confirmed', 'reason': '核对合成项目当前20分钟承诺'}, 'PATCH')
        write('/parse/confirm', {})
        optional = next(f for f in state()['facts'] if f['key'] == '服务期限')
        chapters = state()['chapters']
        technical = next(c for c in chapters if c['volume'] == 'technical')
        plans = [{**{k: c[k] for k in ('id', 'title', 'volume')},
                  'fact_ids': [optional['id']] if c['volume'] == 'technical' else [],
                  'writing_points': '按已确认服务期限和响应时限组织本节；证明不足的地方写待补。',
                  'target_length': 800} for c in chapters]
        write('/plan', {'chapters': plans}, actor=editor, expected=403)
        write('/plan', {'chapters': plans})
        preview_path = path + '/chapters/' + technical['id'] + '/writing-input'
        request(client, 'GET', preview_path, headers=beta, expected=404)
        preview = request(client, 'GET', preview_path, headers=manager).json()
        before = next(c for c in state()['chapters'] if c['id'] == technical['id'])['content']
        generated = write('/generate', {'chapter_ids': [technical['id']]})
        candidate = generated['chapters'][0]['candidate']
        snapshot = candidate['input_snapshot']
        expected_facts = {optional['id'], sla_fact['id']}
        assert {f['id'] for f in snapshot['facts']} == expected_facts, snapshot['facts']
        used_sla = next(f for f in snapshot['facts'] if f['id'] == sla_fact['id'])
        assert used_sla['value'] == '20' and used_sla['unit'] == 'minute', used_sla
        assert snapshot['plan']['target_length'] == 800
        assert candidate['is_real_model'] is False
        assert next(c for c in state()['chapters'] if c['id'] == technical['id'])['content'] == before
        chapter_path = '/api/chapters/' + technical['id']
        suggestion = request(client, 'POST', chapter_path + '/suggestions', headers=manager,
                             payload={'instruction': '整理本章表达，保持变量和事实来源。'}).json()
        assert {f['id'] for f in suggestion['input_snapshot']['facts']} == expected_facts
        assert '{{sla:P1.response}}' in suggestion['content']
        # 候选仍待人工核对；本测试提交明确的合成正文，验证变量解析的实际下载结果。
        current = request(client, 'GET', chapter_path, headers=manager).json()
        lease = request(client, 'POST', chapter_path + '/lock', headers=manager, payload={}).json()
        content = ('技术服务方案（合成验收）\n每月完成数据库巡检并提交报告。\n'
                   '服务期限：{{fact:' + optional['id'] + '}}。\n'
                   '一级故障响应时限：{{sla:P1.response}}。\n仅用于内部合成测试。')
        assert optional['value'] == '12个月' and optional['unit'] == ''
        fact_token = '{{fact:' + optional['id'] + '}}'
        for suffix, expected_code in [('小时', 'FACT_VARIABLE_UNIT_MISMATCH'),
                                      ('个月', 'FACT_VARIABLE_UNIT_DUPLICATED')]:
            current = request(client, 'GET', chapter_path, headers=manager).json()
            request(client, 'POST', chapter_path + '/versions', headers=manager, payload={
                'lease_token': lease['lease_token'], 'input_fingerprint': state()['input_fingerprint'],
                'base_revision': current['revision'], 'content': content.replace(fact_token, fact_token + suffix),
                'idempotency_key': str(uuid4())})
            rejected_check = write('/checks', {'volume': 'all'})['check']
            assert not rejected_check['passed'] and any(item['code'] == expected_code for item in rejected_check['issues'])
            write('/exports', {'check_id': rejected_check['id'], 'kind': 'internal'}, expected=409)
        current = request(client, 'GET', chapter_path, headers=manager).json()
        request(client, 'POST', chapter_path + '/versions', headers=manager, payload={
            'lease_token': lease['lease_token'], 'input_fingerprint': state()['input_fingerprint'], 'base_revision': current['revision'],
            'content': content, 'idempotency_key': str(uuid4())})
        request(client, 'POST', chapter_path + '/lock/release', headers=manager,
                payload={'lease_token': lease['lease_token']})
        check = write('/checks', {'volume': 'all'})['check']
        assert check['passed'] and not check['coverage']['complete'], check['issues']
        exported = write('/exports', {'check_id': check['id'], 'kind': 'internal'})['export']
        downloads = []
        for entry in exported['volumes']:
            data = request(client, 'GET', entry['download_url'], headers=manager).content
            text = word_text(data)
            assert '{{fact:' not in text and '{{sla:' not in text
            if entry['volume'] == 'technical':
                assert optional['value'] in text and '20分钟' in text.replace(' ', ''), text
            if output_dir:
                destination = Path(output_dir) / seeded['project_id']
                destination.mkdir(parents=True, exist_ok=True)
                (destination / entry['filename']).write_bytes(data)
            downloads.append({'filename': entry['filename'], 'bytes': len(data)})
        # 保存新候选后改变来源，证明快照保留旧值且候选/检查/下载需要重新核对。
        fresh = write('/generate', {'chapter_ids': [technical['id']]})['chapters'][0]['candidate']
        old_fingerprint = fresh['input_fingerprint']
        write('/facts/' + optional['id'], {'value': '24个月', 'status': 'confirmed',
                                         'reason': '仅用于来源改变保护验收'}, 'PATCH')
        after = state()
        assert not after['plan_confirmed'] and after['input_fingerprint'] != old_fingerprint
        stored = next(c for c in after['chapters'] if c['id'] == technical['id'])['candidate']
        assert next(f for f in stored['input_snapshot']['facts'] if f['id'] == optional['id'])['value'] == optional['value']
        request(client, 'GET', exported['volumes'][0]['download_url'], headers=manager, expected=409)
        # 来源改变但章节版本未变，旧候选仍须由写入事务拒绝，不能只依赖页面先前的GET。
        current = request(client, 'GET', chapter_path, headers=manager).json()
        lease = request(client, 'POST', chapter_path + '/lock', headers=manager, payload={}).json()
        guarded = {'lease_token': lease['lease_token'], 'base_revision': current['revision'],
                   'content': fresh['content'], 'input_fingerprint': old_fingerprint}
        stale_draft = request(client, 'PUT', chapter_path + '/draft', headers=manager,
                              payload={**guarded, 'sequence': 1}, expected=409).json()
        stale_commit = request(client, 'POST', chapter_path + '/versions', headers=manager,
                               payload={**guarded, 'idempotency_key': str(uuid4())}, expected=409).json()
        assert stale_draft['error']['code'] == stale_commit['error']['code'] == 'INPUT_FINGERPRINT_STALE'
        missing = {k: v for k, v in guarded.items() if k != 'input_fingerprint'}
        request(client, 'POST', chapter_path + '/versions', headers=manager,
                payload={**missing, 'idempotency_key': str(uuid4())}, expected=409)
        assert request(client, 'GET', chapter_path, headers=manager).json()['content'] == content
        request(client, 'POST', chapter_path + '/lock/release', headers=manager,
                payload={'lease_token': lease['lease_token']})
        return {'passed': True, 'project_id': seeded['project_id'], 'project_name': name,
                'selected_fact_ids': sorted(expected_facts), 'sla_input_value': used_sla['value'],
                'candidate_snapshot_verified': True, 'source_change_requires_review': True,
                'embedded_unit_guard_verified': True, 'stale_draft_commit_blocked': True,
                'downloads': downloads, 'preview_available': bool(preview),
                'complete_reference': False, 'word_layout_verified': False}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='本机合成写作输入与候选来源验收。')
    parser.add_argument('--base-url', default='http://127.0.0.1:8710')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    print(json.dumps(run(args.base_url, args.output_dir), ensure_ascii=False))
