# 为什么有这个文件：在实际本机服务核对多个项目成员的分工、逐章确认、旧锁撤销和两册下载。
# 它解决什么问题：进程内测试通过后，仍须证明页面连接的真实服务按这些权限办理且交接不丢稿。

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from smoke_demo import authenticate, request
from smoke_reference import run as create_reference_project, word_text


def run(base_url, output_dir=None):
    target = urlparse(base_url)
    if target.scheme != 'http' or target.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('成员验收只在本机创建完全合成项目。')
    seeded = create_reference_project(base_url)
    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as client:
        manager, tech, business, assembly, viewer, outsider, beta = [authenticate(client, identity) for identity in (
            'alpha-manager', 'alpha-tech', 'alpha-business', 'alpha-editor', 'alpha-viewer', 'alpha-outsider-manager', 'beta-manager')]
        path = '/api/v1/projects/' + seeded['project_id']
        def state():
            return request(client, 'GET', path + '/workspace', headers=manager).json()
        def write(route, payload, method='POST', actor=None, expected=200, headers=None):
            return request(client, method, path + route, headers=headers or {**(actor or manager),
                'If-Match': str(state()['revision']), 'Idempotency-Key': str(uuid4())}, payload=payload, expected=expected).json()
        name = 'ICG项目分工HTTP验收（合成）-' + uuid4().hex[:6]
        write('', {'name': name}, 'PATCH')
        team = {'members': [
            {'user_id': 'alpha-manager', 'project_role': 'lead', 'volumes': ['technical', 'business']},
            {'user_id': 'alpha-tech', 'project_role': 'writer', 'volumes': ['technical']},
            {'user_id': 'alpha-business', 'project_role': 'writer', 'volumes': ['business']},
            {'user_id': 'alpha-editor', 'project_role': 'writer', 'volumes': ['technical', 'business']},
            {'user_id': 'alpha-viewer', 'project_role': 'readonly', 'volumes': ['technical', 'business']}],
            'volumes': [{'volume': 'technical', 'owner_id': 'alpha-tech'}, {'volume': 'business', 'owner_id': 'alpha-manager'}],
            'assembly_owner_id': 'alpha-editor', 'reason': '按合成人员分工办理，原正文、历史和已保存草稿保留。'}
        write('/team', team, 'PUT')
        chapters = {c['volume']: c['id'] for c in state()['chapters']}
        for volume, actor_id in (('technical', 'alpha-tech'), ('business', 'alpha-business')):
            write('/chapters/' + chapters[volume] + '/assignment', {'assignee_id': actor_id, 'reason': '明确本节编写人，保留已有私有草稿'}, 'PATCH')
        for actor in (outsider, beta):
            for url in (path + '/workspace', path + '/team', '/api/chapters/' + chapters['technical'],
                        '/api/chapters/' + chapters['technical'] + '/versions', state()['files'][0]['download_url']):
                request(client, 'GET', url, headers=actor, expected=404)
            assert seeded['project_id'] not in {j['project_id'] for j in request(client, 'GET', '/api/v1/jobs', headers=actor).json()['jobs']}
        request(client, 'POST', '/api/projects', headers=business, payload={'name': '普通编写人不得新建'}, expected=403)
        write('/team', team, 'PUT', actor=tech, expected=403)
        invalid = json.loads(json.dumps(team))
        invalid['members'][1]['project_role'] = 'lead'
        invalid['members'][1]['volumes'] = ['technical', 'business']
        assert write('/team', invalid, 'PUT', expected=422)['code'] == 'PROJECT_LEAD_COMPANY_ROLE_REQUIRED'
        invalid = json.loads(json.dumps(team))
        invalid['members'][0]['project_role'] = 'writer'
        assert write('/team', invalid, 'PUT', expected=409)['code'] == 'LAST_PROJECT_LEAD_REQUIRED'
        tech_path = '/chapters/' + chapters['technical']
        business_path = '/chapters/' + chapters['business']
        write(tech_path + '/plan', {'fact_ids': [], 'writing_points': '由技术负责人核对巡检措施。', 'target_length': 650}, 'PATCH', actor=tech)
        write(tech_path + '/plan/confirm', {}, actor=tech)
        write('/generate', {'chapter_ids': [chapters['business']]}, actor=business, expected=409)
        candidate = write('/generate', {'chapter_ids': [chapters['technical']]}, actor=tech)['chapters'][0]['candidate']
        assert candidate['input_snapshot']['plan']['confirmed_by'] == 'alpha-tech' and candidate['is_real_model'] is False
        write(business_path + '/plan', {'fact_ids': [], 'writing_points': '资质和业绩证据逐项核对。', 'target_length': 500}, 'PATCH', actor=business)
        write(business_path + '/plan/confirm', {}, actor=business)
        current = state()
        assert next(c for c in current['chapters'] if c['volume'] == 'technical')['writing_input']['is_current']
        write(business_path + '/plan/confirm', {}, actor=tech, expected=403)
        write('/checks', {'volume': 'all'}, actor=assembly, expected=403)
        write('/checks', {'volume': 'all'}, actor=viewer, expected=403)
        write('/checks', {'volume': 'business'}, actor=tech, expected=403)
        write('/generate', {'chapter_ids': [chapters['technical']]}, actor=business, expected=403)
        official = {'technical': '技术分工验收正文：每月完成数据库巡检并提交报告，技术负责人复核。',
                    'business': '商务分工验收正文：合成企业资质及同类项目业绩经逐项核对，仅供内部测试。'}
        for volume, actor in (('technical', tech), ('business', business)):
            url = '/api/chapters/' + chapters[volume]
            chapter = request(client, 'GET', url, headers=actor).json()
            lease = request(client, 'POST', url + '/lock', headers=actor, payload={}).json()['lease_token']
            request(client, 'POST', url + '/versions', headers=actor, payload={'lease_token': lease,
                'base_revision': chapter['revision'], 'content': official[volume],
                'input_fingerprint': state()['input_fingerprint'], 'idempotency_key': str(uuid4())})
            request(client, 'POST', url + '/lock/release', headers=actor, payload={'lease_token': lease})
        # 明确交接，不能拿旧lease或旧收据继续写；个人草稿不会暴露给接手人。
        url = '/api/chapters/' + chapters['business']
        old = request(client, 'GET', url, headers=business).json()
        lease = request(client, 'POST', url + '/lock', headers=business, payload={}).json()['lease_token']
        draft = {'lease_token': lease, 'base_revision': old['revision'], 'sequence': 1,
                 'content': '商务本人私有交接草稿标记', 'input_fingerprint': state()['input_fingerprint']}
        request(client, 'PUT', url + '/draft', headers=business, payload=draft)
        failed = write(business_path + '/assignment', {'assignee_id': 'alpha-editor'}, 'PATCH', expected=409)
        assert failed['code'] == 'HANDOFF_REASON_REQUIRED'
        write(business_path + '/assignment', {'assignee_id': 'alpha-editor', 'reason': '临时交给合标编写人，保留原本人草稿'}, 'PATCH')
        request(client, 'PUT', url + '/draft', headers=business, payload=draft, expected=403)
        assert request(client, 'GET', url, headers=assembly).json()['draft'] is None
        assert request(client, 'GET', url, headers=business).json()['draft']['content'] == draft['content']
        write(business_path + '/assignment', {'assignee_id': 'alpha-business', 'reason': '测试后交还原编写人，保留其原草稿'}, 'PATCH')
        write(business_path + '/plan/confirm', {}, actor=business)
        # 草稿保留用于GUI查看，实际输出只取已提交正文。
        check = write('/checks', {'volume': 'all'})['check']
        assert check['passed'], check['issues']
        exported = write('/exports', {'check_id': check['id'], 'kind': 'internal'})['export']
        outputs = []
        for entry in exported['volumes']:
            payload = request(client, 'GET', entry['download_url'], headers=assembly).content
            text = word_text(payload)
            assert official[entry['volume']] in text and '商务本人私有交接草稿标记' not in text
            request(client, 'GET', entry['download_url'], headers=outsider, expected=404)
            if output_dir:
                directory = Path(output_dir) / seeded['project_id']
                directory.mkdir(parents=True, exist_ok=True)
                (directory / entry['filename']).write_bytes(payload)
            outputs.append({'volume': entry['volume'], 'bytes': len(payload)})
        return {'passed': True, 'project_id': seeded['project_id'], 'project_name': name, 'chapters': chapters,
                'export_id': exported['id'], 'downloads': outputs, 'handoffs': len(state()['team']['handoffs']),
                'private_draft_retained': True, 'real_model_called': False, 'word_layout_verified': False}


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='验证本机ICG成员、分工、逐章方案与两册输出。')
    parser.add_argument('--base-url', default='http://127.0.0.1:8710')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    print(json.dumps(run(args.base_url, args.output_dir), ensure_ascii=False))
