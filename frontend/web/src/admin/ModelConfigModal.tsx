// 为什么有这个文件：落实 APP-M2-T036、T037 与用户拍板决策，提供大模型配置弹窗。
// 它解决什么问题：支持查看、切换、新建与编辑租户大模型端点（/api/v1/model-configs），校验敏感项目本地模型标记，提供连通性测试与乐观锁防覆盖。

import React, { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudServerOutlined,
  LockOutlined,
  PlusOutlined,
  ReloadOutlined,
  SaveOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { request, ApiError } from '../shared/api.ts';
import type { ApplicationSession } from '../shared/types.ts';
import {
  fallbackOptions,
  type ModelConfigItem,
  buildModelUpdatePayload,
} from './model-config-core.ts';

const { Text, Title } = Typography;

export type { ModelConfigItem };

export interface ModelConfigModalProps {
  open: boolean;
  onClose: () => void;
  token?: string | null;
  session?: ApplicationSession | null;
  projectId?: string | null;
  projectSensitive?: boolean;
  onBound?: (configId: string) => void;
  /** 公司管理员/平台管理员：可新建、修改、测试连接 */
  canManage?: boolean;
  /** 公司管理员或项目负责人：可把配置应用到当前项目 */
  canBind?: boolean;
}

export function ModelConfigModal({
  open,
  onClose,
  token = null,
  session = null,
  projectId = null,
  projectSensitive = false,
  onBound,
  canManage = false,
  canBind = false,
}: ModelConfigModalProps) {
  const [loading, setLoading] = useState(false);
  const [configs, setConfigs] = useState<ModelConfigItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [isCreatingNew, setIsCreatingNew] = useState(false);
  const [form] = Form.useForm();
  const [projectBoundConfigId, setProjectBoundConfigId] = useState<string | null>(null);
  const [binding, setBinding] = useState(false);
  const [bindError, setBindError] = useState<string | null>(null);

  // 测试连通性状态
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    duration_ms?: number;
    message?: string;
  } | null>(null);

  // 保存状态
  const [saving, setSaving] = useState(false);

  const activeConfig = configs.find(c => c.id === selectedId) || configs[0] || null;

  // 加载配置列表
  const fetchConfigs = async () => {
    if (!open) return;
    setLoading(true);
    setTestResult(null);
    try {
      const res = await request<{ items: ModelConfigItem[] }>('/api/v1/model-configs', token);
      const items = res.items || [];
      setConfigs(items);
      if (items.length > 0 && !selectedId) {
        setSelectedId(items[0].id);
      }
      if (projectId) {
        try {
          const bound = await request<ModelConfigItem>(
            `/api/v1/projects/${encodeURIComponent(projectId)}/model-config`,
            token
          );
          if (bound?.id) {
            setProjectBoundConfigId(bound.id);
          }
        } catch {
          // 未单独绑定或默认配置
        }
      }
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载模型配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchConfigs();
    }
  }, [open, token]);

  // 当选中的配置改变或切换到新建时更新表单
  useEffect(() => {
    setTestResult(null);
    setBindError(null);
    if (isCreatingNew) {
      form.setFieldsValue({
        id: '',
        name: '新模型服务配置',
        provider: 'openai-compatible',
        base_url: 'http://127.0.0.1:8000',
        model: 'qwen2.5-72b',
        api_key: '',
        is_local: true,
        allow_sensitive: true,
        stream_enabled: true,
        json_mode_enabled: false,
        timeout_seconds: 60,
        max_tokens: 2048,
      });
    } else if (activeConfig) {
      form.setFieldsValue({
        id: activeConfig.id,
        name: activeConfig.name,
        provider: activeConfig.provider,
        base_url: activeConfig.base_url,
        model: activeConfig.model,
        api_key: activeConfig.api_key_masked || '',
        is_local: activeConfig.is_local,
        allow_sensitive: activeConfig.allow_sensitive,
        stream_enabled: activeConfig.stream_enabled,
        json_mode_enabled: activeConfig.json_mode_enabled,
        timeout_seconds: activeConfig.timeout_seconds,
        max_tokens: activeConfig.max_tokens,
        fallback_config_id: activeConfig.fallback_config_id ?? undefined,
      });
    }
  }, [activeConfig, isCreatingNew, form]);

  // 执行连通性测试
  const handleTestConnection = async () => {
    if (!activeConfig && !isCreatingNew) return;
    setTesting(true);
    setTestResult(null);
    try {
      if (isCreatingNew) {
        // 新建模式下提示需先保存或测试
        message.info('新建配置请先保存后执行在线测试');
        return;
      }
      const res = await request<{ ok: boolean; provider: string; model: string; duration_ms: number }>(
        `/api/v1/model-configs/${activeConfig!.id}/test`,
        token,
        'POST'
      );
      setTestResult({
        ok: res.ok,
        duration_ms: res.duration_ms,
        message: res.ok ? `服务响应正常，耗时 ${res.duration_ms} ms` : '模型服务连通失败，请检查 Base URL 与 Key',
      });
    } catch (err) {
      setTestResult({
        ok: false,
        message: err instanceof Error ? err.message : '连接异常',
      });
    } finally {
      setTesting(false);
    }
  };

  // 保存模型配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      if (isCreatingNew) {
        const payload: Record<string, unknown> = {
          name: values.name,
          provider: values.provider,
          base_url: values.base_url,
          model: values.model,
          is_local: Boolean(values.is_local),
          allow_sensitive: Boolean(values.allow_sensitive),
          stream_enabled: Boolean(values.stream_enabled),
          json_mode_enabled: Boolean(values.json_mode_enabled),
          timeout_seconds: Number(values.timeout_seconds),
          max_tokens: Number(values.max_tokens),
          fallback_config_id: values.fallback_config_id ?? '',
        };
        if (values.id) payload.id = values.id;
        if (values.api_key) payload.api_key = values.api_key;

        const created = await request<ModelConfigItem>('/api/v1/model-configs', token, 'POST', payload);
        message.success('新模型配置已创建');
        setIsCreatingNew(false);
        await fetchConfigs();
        setSelectedId(created.id);
      } else if (activeConfig) {
        const payload: Record<string, unknown> = {
          name: values.name,
          provider: values.provider,
          base_url: values.base_url,
          model: values.model,
          is_local: Boolean(values.is_local),
          allow_sensitive: Boolean(values.allow_sensitive),
          stream_enabled: Boolean(values.stream_enabled),
          json_mode_enabled: Boolean(values.json_mode_enabled),
          timeout_seconds: Number(values.timeout_seconds),
          max_tokens: Number(values.max_tokens),
          fallback_config_id: values.fallback_config_id ?? '',
        };
        // 密钥传参语义：若与掩码一致则传回掩码（保持不变）；若输入新内容则传入加密
        if (values.api_key !== undefined) {
          payload.api_key = values.api_key;
        }

        const updated = await request<ModelConfigItem>(
          `/api/v1/model-configs/${activeConfig.id}`,
          token,
          'PUT',
          payload,
          activeConfig.revision
        );
        message.success('模型配置保存成功');
        await fetchConfigs();
        setSelectedId(updated.id);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        message.error('配置版本发生冲突，请重新刷新加载最新配置');
        fetchConfigs();
      } else {
        message.error(err instanceof Error ? err.message : '保存失败');
      }
    } finally {
      setSaving(false);
    }
  };

  // 绑定配置至当前项目（仅当在项目上下文中调用时生效）
  const handleBindProject = async () => {
    if (!projectId || !activeConfig) return;
    setBinding(true);
    setBindError(null);
    try {
      await request(
        `/api/v1/projects/${encodeURIComponent(projectId)}/model-config`,
        token,
        'POST',
        { model_config_id: activeConfig.id }
      );
      setProjectBoundConfigId(activeConfig.id);
      message.success(`已将模型「${activeConfig.name}」绑定至本项目`);
      onBound?.(activeConfig.id);
    } catch (err) {
      if (err instanceof ApiError && err.code === 'SENSITIVE_PROJECT_REQUIRES_LOCAL_MODEL') {
        const msg = err.message || '涉密项目必须使用本地模型或允许敏感数据的服务。';
        setBindError(msg);
        message.error(msg);
      } else {
        const msg = err instanceof Error ? err.message : '项目模型绑定失败';
        setBindError(msg);
        message.error(msg);
      }
    } finally {
      setBinding(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <Space>
          <ThunderboltOutlined style={{ color: '#1E4DB7' }} />
          <span>大模型服务配置</span>
          <Tag color="blue">OpenAI 兼容</Tag>
        </Space>
      }
      width={760}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            {canManage && !isCreatingNew && activeConfig && (
              <Button
                data-testid="test-connection-btn"
                icon={<ApiOutlined />}
                loading={testing}
                onClick={handleTestConnection}
              >
                测试连通性
              </Button>
            )}
            {canBind && projectId && !isCreatingNew && activeConfig && (
              <Button
                data-testid="bind-project-model-btn"
                icon={<CloudServerOutlined />}
                loading={binding}
                onClick={handleBindProject}
                type={projectBoundConfigId === activeConfig.id ? 'default' : 'primary'}
                ghost={projectBoundConfigId !== activeConfig.id}
              >
                {projectBoundConfigId === activeConfig.id ? '当前项目已生效' : '应用至当前项目'}
              </Button>
            )}
          </Space>
          <Space>
            <Button onClick={onClose}>关闭</Button>
            {canManage && (
              <Button
                data-testid="save-config-btn"
                type="primary"
                icon={<SaveOutlined />}
                loading={saving}
                onClick={handleSave}
              >
                {isCreatingNew ? '立即创建' : '保存配置'}
              </Button>
            )}
          </Space>
        </div>
      }
      destroyOnClose
    >
      <div data-testid="model-config-modal" style={{ paddingTop: 8 }}>
        {/* 配置选择栏 */}
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Space>
            <Text strong>选择配置：</Text>
            <Select
              style={{ width: 280 }}
              value={isCreatingNew ? 'new' : selectedId}
              disabled={isCreatingNew || loading}
              onChange={val => {
                setSelectedId(val);
                setIsCreatingNew(false);
              }}
              options={[
                ...configs.map(c => ({
                  value: c.id,
                  label: `${c.name} (${c.model})${c.is_local ? ' · 本地' : ''}`,
                })),
              ]}
            />
            <Button
              icon={<ReloadOutlined />}
              size="small"
              onClick={fetchConfigs}
              loading={loading}
              title="刷新配置列表"
            />
            {projectBoundConfigId && activeConfig && projectBoundConfigId === activeConfig.id && (
              <Tag color="green" data-testid="project-bound-tag">本项目当前生效</Tag>
            )}
            {projectSensitive && (
              <Tag color="orange" data-testid="project-sensitive-tag">涉密项目门控</Tag>
            )}
          </Space>

          {canManage && <Button
            data-testid="add-config-btn"
            type={isCreatingNew ? 'default' : 'dashed'}
            icon={isCreatingNew ? <CloseCircleOutlined /> : <PlusOutlined />}
            size="small"
            onClick={() => {
              setIsCreatingNew(!isCreatingNew);
              if (isCreatingNew && configs.length > 0) {
                setSelectedId(configs[0].id);
              }
            }}
          >
            {isCreatingNew ? '取消新建' : '新建模型配置'}
          </Button>}
        </div>

        {/* 涉密项目策略拦截警告 */}
        {bindError && (
          <Alert
            data-testid="sensitive-model-blocked-alert"
            style={{ marginBottom: 16 }}
            type="error"
            showIcon
            message="涉密项目模型策略拦截 (403)"
            description={bindError}
            closable
            onClose={() => setBindError(null)}
          />
        )}

        {/* 测试连通性提示条 */}
        {testResult && (
          <Alert
            style={{ marginBottom: 16 }}
            type={testResult.ok ? 'success' : 'error'}
            showIcon
            message={testResult.ok ? '连通性测试通过' : '连通性测试未通过'}
            description={testResult.message}
          />
        )}

        <Spin spinning={loading}>
          {!canManage && (
            <Alert data-testid="model-config-readonly" type="info" showIcon style={{ marginBottom: 12 }}
              message="只读：模型配置由公司管理员维护"
              description={canBind ? '你可以把已有配置应用到当前项目；新建、修改和测试连接请联系公司管理员。' : '如需更换项目使用的模型，请联系项目负责人或公司管理员。'} />
          )}
          <Form form={form} layout="vertical" disabled={!canManage}>
            <Row gutter={16}>
              <Col span={14}>
                <Form.Item
                  name="name"
                  label="配置名称"
                  rules={[{ required: true, message: '请输入模型配置名称' }]}
                >
                  <Input placeholder="如：默认生产大模型 / 本地 Qwen 专线" />
                </Form.Item>
              </Col>
              <Col span={10}>
                <Form.Item name="provider" label="提供商协议" rules={[{ required: true }]}>
                  <Select
                    options={[
                      { value: 'openai-compatible', label: 'OpenAI-Compatible (标准协议)' },
                      { value: 'demo', label: 'Local Mock (内置演示替身)' },
                    ]}
                  />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={16}>
                <Form.Item
                  name="base_url"
                  label="服务 Base URL"
                  rules={[{ required: true, message: '请输入服务 Base URL' }]}
                  tooltip="如 http://127.0.0.1:8000/v1 或内网模型服务代理地址"
                >
                  <Input prefix={<CloudServerOutlined style={{ color: '#8c8c8c' }} />} placeholder="http://127.0.0.1:8000" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="model"
                  label="模型标识 (Model)"
                  rules={[{ required: true, message: '请输入模型名称' }]}
                >
                  <Input placeholder="如 qwen2.5-72b / deepseek-chat" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="api_key"
              label="API Key"
              tooltip="已采用 Fernet 对称加密。留空保持原密钥不变，输入新值将覆盖更新。"
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#8c8c8c' }} />}
                placeholder="留空保持原密钥，或输入新 API Key"
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={6}>
                <Form.Item
                  name="is_local"
                  label="本地私有化部署"
                  valuePropName="checked"
                  tooltip="涉密及敏感标书项目强制只能选用标记为本地私有化部署的模型"
                >
                  <Switch checkedChildren="本地部署" unCheckedChildren="公网云端" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  name="allow_sensitive"
                  label="允许涉密项目调用"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="允许" unCheckedChildren="禁止" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  name="stream_enabled"
                  label="流式生成 (Stream)"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item
                  name="json_mode_enabled"
                  label="结构化 JSON 输出"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="timeout_seconds"
                  label="超时时间 (秒)"
                  rules={[{ required: true }]}
                >
                  <InputNumber min={5} max={600} style={{ width: '100%' }} addonAfter="秒" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="max_tokens"
                  label="最大输出 Token (Max Tokens)"
                  rules={[{ required: true }]}
                >
                  <InputNumber min={128} max={32768} style={{ width: '100%' }} addonAfter="Tokens" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item noStyle shouldUpdate={(prev, next) => prev.is_local !== next.is_local}>
              {() => (
                <Form.Item name="fallback_config_id" label="备用模型"
                  extra="主模型超时、连接失败、5xx 或限流时改用；本地主模型只能选本地备用，敏感项目只用本地且允许敏感数据的备用。">
                  <Select allowClear placeholder="不配备用模型" data-testid="model-fallback-select"
                    options={fallbackOptions(configs, { id: isCreatingNew ? undefined : activeConfig?.id, is_local: form.getFieldValue('is_local') })} />
                </Form.Item>
              )}
            </Form.Item>
          </Form>
        </Spin>
      </div>
    </Modal>
  );
}

export default ModelConfigModal;
