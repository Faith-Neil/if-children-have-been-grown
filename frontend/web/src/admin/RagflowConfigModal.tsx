// 为什么有这个文件：落实用户拍板决策与 PRD §6.2，提供知识库检索服务（RAGFlow）配置弹窗。
// 它解决什么问题：支持租户直连真实 RAGFlow 知识库（/api/v1/ragflow-config），配置 Base URL、API Key、Dataset IDs 并一键执行健康检测与连通性测试。

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
  Row,
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
  DatabaseOutlined,
  GlobalOutlined,
  KeyOutlined,
  ReloadOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import { request, ApiError } from '../shared/api.ts';
import type { ApplicationSession } from '../shared/types.ts';
import {
  type RagflowConfigData,
  buildRagflowUpdatePayload,
} from './ragflow-config-core.ts';

const { Text, Paragraph } = Typography;

export type { RagflowConfigData };

export interface RagflowConfigModalProps {
  open: boolean;
  onClose: () => void;
  token?: string | null;
  session?: ApplicationSession | null;
}

export function RagflowConfigModal({
  open,
  onClose,
  token = null,
  session = null,
}: RagflowConfigModalProps) {
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<RagflowConfigData | null>(null);
  const [form] = Form.useForm();

  // 连通性测试状态
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    duration_ms?: number;
    message?: string;
  } | null>(null);

  // 保存状态
  const [saving, setSaving] = useState(false);

  // 加载租户 RAGFlow 配置
  const fetchConfig = async () => {
    if (!open) return;
    setLoading(true);
    setTestResult(null);
    try {
      const data = await request<RagflowConfigData>('/api/v1/ragflow-config', token);
      setConfig(data);
      form.setFieldsValue({
        base_url: data.base_url,
        api_key: data.api_key_masked || '',
        dataset_ids: (data.dataset_ids || []).join(', '),
        timeout_seconds: data.timeout_seconds || 30,
        is_enabled: data.is_enabled ?? true,
      });
    } catch (err) {
      message.error(err instanceof Error ? err.message : '加载 RAGFlow 知识库配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchConfig();
    }
  }, [open, token]);

  // 执行 RAGFlow 连通性测试
  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const values = form.getFieldsValue();
      const payload: Record<string, unknown> = {
        base_url: values.base_url,
        timeout_seconds: values.timeout_seconds,
      };
      if (values.api_key && values.api_key !== config?.api_key_masked) {
        payload.api_key = values.api_key;
      }
      const res = await request<{
        ok: boolean;
        duration_ms: number;
        message: string;
        health: Record<string, unknown>;
      }>('/api/v1/ragflow-config/test', token, 'POST', payload);

      setTestResult({
        ok: res.ok,
        duration_ms: res.duration_ms,
        message: res.ok
          ? `RAGFlow 服务健康正常，耗时 ${res.duration_ms} ms`
          : `连接失败: ${res.message || '请核实 Base URL 与服务端运行状态'}`,
      });
    } catch (err) {
      setTestResult({
        ok: false,
        message: err instanceof Error ? err.message : '网络请求异常',
      });
    } finally {
      setTesting(false);
    }
  };

  // 保存 RAGFlow 配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      const datasetList = String(values.dataset_ids || '')
        .split(/[,，\n]/)
        .map(d => d.trim())
        .filter(Boolean);

      const payload: Record<string, unknown> = {
        base_url: values.base_url,
        dataset_ids: datasetList,
        timeout_seconds: Number(values.timeout_seconds),
        is_enabled: Boolean(values.is_enabled),
      };

      if (values.api_key !== undefined) {
        payload.api_key = values.api_key;
      }

      const updated = await request<RagflowConfigData>(
        '/api/v1/ragflow-config',
        token,
        'PUT',
        payload,
        config?.revision
      );

      message.success('RAGFlow 知识库配置已保存');
      setConfig(updated);
      setTestResult(null);
      form.setFieldsValue({
        base_url: updated.base_url,
        api_key: updated.api_key_masked || '',
        dataset_ids: (updated.dataset_ids || []).join(', '),
        timeout_seconds: updated.timeout_seconds,
        is_enabled: updated.is_enabled,
      });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        message.error('配置版本已被其他管理员修改，请刷新重试');
        fetchConfig();
      } else {
        message.error(err instanceof Error ? err.message : '保存失败');
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <Space>
          <DatabaseOutlined style={{ color: '#1E4DB7' }} />
          <span>知识库检索服务配置 (RAGFlow)</span>
          <Tag color="cyan">Infiniflow RAGFlow</Tag>
        </Space>
      }
      width={720}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button
            data-testid="ragflow-test-btn"
            icon={<ApiOutlined />}
            loading={testing}
            onClick={handleTestConnection}
          >
            测试连通性
          </Button>
          <Space>
            <Button onClick={onClose}>关闭</Button>
            <Button
              data-testid="ragflow-save-btn"
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
            >
              保存配置
            </Button>
          </Space>
        </div>
      }
      destroyOnClose
    >
      <div data-testid="ragflow-config-modal" style={{ paddingTop: 8 }}>
        {/* 服务状态与刷新 */}
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Space>
            <Text strong>当前接入企业租户：</Text>
            <Tag color="purple">{config?.company_id || session?.scope.active_company_id || '当前租户'}</Tag>
            {config?.has_api_key ? (
              <Tag icon={<CheckCircleOutlined />} color="success">
                已配置 API 密钥
              </Tag>
            ) : (
              <Tag icon={<CloseCircleOutlined />} color="warning">
                未配置 API 密钥
              </Tag>
            )}
          </Space>
          <Button
            icon={<ReloadOutlined />}
            size="small"
            onClick={fetchConfig}
            loading={loading}
            title="刷新"
          />
        </div>

        {/* 连通性测试反馈 */}
        {testResult && (
          <Alert
            style={{ marginBottom: 16 }}
            type={testResult.ok ? 'success' : 'error'}
            showIcon
            message={testResult.ok ? '服务连通正常' : '连通性检查未通过'}
            description={testResult.message}
          />
        )}

        <Spin spinning={loading}>
          <Form form={form} layout="vertical">
            <Form.Item
              name="base_url"
              label="RAGFlow 服务地址 (Base URL)"
              rules={[{ required: true, message: '请输入 RAGFlow 服务端点 URL' }]}
              tooltip="支持本地 Docker 部署 (http://127.0.0.1:9380) 或内网及云端 RAGFlow 服务实例"
            >
              <Input
                prefix={<GlobalOutlined style={{ color: '#8c8c8c' }} />}
                placeholder="http://127.0.0.1:9380"
              />
            </Form.Item>

            <Form.Item
              name="api_key"
              label="RAGFlow API Key"
              tooltip="已采用 Fernet 对称加密保护。留空保持原密钥不变，输入新密钥将自动覆盖。"
            >
              <Input.Password
                prefix={<KeyOutlined style={{ color: '#8c8c8c' }} />}
                placeholder="ragflow-..."
              />
            </Form.Item>

            <Form.Item
              name="dataset_ids"
              label="知识库数据集标识 (Dataset IDs)"
              rules={[{ required: true, message: '请至少指定一个知识库 Dataset ID' }]}
              tooltip="多个 Dataset ID 可使用英文逗号分隔"
            >
              <Input placeholder="如 dataset-alpha-01, dataset-alpha-cases" />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="timeout_seconds"
                  label="检索超时时间 (秒)"
                  rules={[{ required: true }]}
                >
                  <InputNumber min={5} max={300} style={{ width: '100%' }} addonAfter="秒" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="is_enabled"
                  label="启用知识库检索"
                  valuePropName="checked"
                  tooltip="关闭后，大纲生成与编写助理将暂停外呼 RAGFlow，仅依赖本地证据"
                >
                  <Switch checkedChildren="已启用" unCheckedChildren="已暂停" />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Spin>
      </div>
    </Modal>
  );
}

export default RagflowConfigModal;
