// 为什么有这个文件：核对服务承诺传播接口（APP-M2-T122 / T119）。
// 它解决什么问题：选用模板后事实尚未确认时，getSlaPropagation 必须返回正确的待处理数量和原因；
// 用例自己建项目、自己建公司模板，不依赖示例项目状态与用例顺序。
// 注：浏览器视角（SPA 工作区时序）不在本测试验证，见 T122/T119 交付文档的缺口说明。
import { expect, test, type APIRequestContext } from '@playwright/test';

async function seed(request: APIRequestContext) {
  const loginResp = await request.post('/api/v1/auth/login', { data: { username: 'alpha-manager', password: 'X_2026' } });
  expect(loginResp.ok(), `login: ${await loginResp.text()}`).toBeTruthy();
  const auth = { Authorization: `Bearer ${(await loginResp.json()).access_token}` };

  const created = await request.post('/api/v1/projects', { headers: auth, data: { name: `SLA传播-${Date.now()}` } });
  expect(created.ok(), `create project: ${await created.text()}`).toBeTruthy();
  const projectId = (await created.json()).id as string;

  const templates = await (await request.get('/api/v1/sla/templates', { headers: auth })).json();
  const template = await request.post('/api/v1/sla/templates', {
    headers: { ...auth, 'If-Match': String(templates.revision), 'Idempotency-Key': crypto.randomUUID() },
    data: {
      name: `合成传播模板-${Date.now()}`, version_no: '1.0', service_hours: 'h7x24', status: 'confirmed',
      body_text: '一级故障响应时限为{{P1_response}}分钟。', reason: 'e2e：合成模板，仅用于界面核对。',
      variables: [{ var_key: 'P1_response', label: '一级故障响应时限', group: 'response', value_type: 'decimal',
        default_value: '30', unit: 'minute', compare_direction: 'lower_better', best_committable_value: '15' }],
    },
  });
  expect(template.ok(), `create template: ${await template.text()}`).toBeTruthy();
  const templateId = (await template.json()).item.id as string;

  const workspace = await (await request.get(`/api/v1/projects/${projectId}/workspace`, { headers: auth })).json();
  const selected = await request.post(`/api/v1/projects/${projectId}/sla/template`, {
    headers: { ...auth, 'If-Match': String(workspace.revision), 'Idempotency-Key': crypto.randomUUID() },
    data: { template_id: templateId },
  });
  expect(selected.ok(), `select template: ${await selected.text()}`).toBeTruthy();
  return { projectId, auth };
}

test('SLA propagation API returns unconfirmed row after template selection (T122/T119)', async ({ request }) => {
  const { projectId, auth } = await seed(request);

  const body = await (await request.get(`/api/v1/projects/${projectId}/sla/propagation`, { headers: auth })).json();

  expect(body.selected, '选用模板后 selected 应为 true').toBe(true);
  expect(body.summary.total, '模板有 1 个变量').toBe(1);
  expect(body.summary.unconfirmed, '初始状态 1 项尚未由负责人确认').toBe(1);
  expect(body.rows).toHaveLength(1);
  expect(body.rows[0].var_key).toBe('P1_response');
  expect(body.rows[0].reasons.map((r: { code: string }) => r.code)).toContain('UNCONFIRMED');
});
