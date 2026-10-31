// 为什么有这个文件：落地 A-03 扩展字段与企业设置键表单框架（APP-M2-T025）。
// 它解决什么问题：
// 1. 集中管理企业级安全策略、编辑协同参数、导出合规红线与大纲/AI预算；
// 2. 贯彻“越界提示平台上下限，公司设置只能调严不能调宽”安全基线；
// 3. 严格落实 9.11 编辑锁心跳三元数学约束校验；
// 4. 精细化适配 8 大标准 RBAC 角色权限，提供管理员可控保存与普通成员只读态。

import React, { useEffect, useState, useMemo } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  SafetyCertificateOutlined,
  EditOutlined,
  FileDoneOutlined,
  AppstoreOutlined,
  PlusOutlined,
  SaveOutlined,
  ReloadOutlined,
  LockOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

import type { ApplicationSession } from '../shared/types.ts';
import {
  buildInitialCompanySettings,
  checkCompanySettingsPermission,
  validateCompanySettings,
  PLATFORM_SETTING_BOUNDS,
  type CompanySettingsData,
  type CustomFieldMetadata,
} from './company-settings-core.ts';
import { WordTemplateCard } from './WordTemplateCard.tsx';
import { TaskModelRoutesCard } from './TaskModelRoutesCard.tsx';
import { fetchCompanySettings, updateCompanySettings } from './company-settings-api.ts';
import { settingsFromApi, settingsPayload } from './company-settings-sync.ts';
import { userFacingMessage } from '../shared/api.ts';

const { Text, Paragraph } = Typography;

export interface CompanySettingsPageProps {
  session?: ApplicationSession | null;
  currentUser?: { id?: string; name?: string; role?: string; primary_role?: string; company_id?: string } | null;
  currentRole?: string;
  token?: string | null;
}

export function CompanySettingsPage({ session, currentUser, currentRole: explicitRole, token }: CompanySettingsPageProps) {
  const activeRole = explicitRole || session?.user?.primary_role || session?.user?.role || currentUser?.primary_role || currentUser?.role || 'company_admin';
  const permission = useMemo(() => checkCompanySettingsPermission(activeRole), [activeRole]);

  // 表单受控数据
  const [settings, setSettings] = useState<CompanySettingsData>(() =>
    buildInitialCompanySettings(currentUser?.company_id || session?.user?.company_id || 'alpha')
  );

  const companyId = currentUser?.company_id || session?.user?.company_id || 'alpha';
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [savedAt, setSavedAt] = useState<string | null>(null);

  // 打开页面即读取后台保存的设置；读不到时不让保存，避免用默认值覆盖已保存的设置
  useEffect(() => {
    let alive = true;
    setLoading(true);
    fetchCompanySettings(companyId, token ?? null)
      .then(api => { if (alive) { setSettings(settingsFromApi(api)); setSavedAt(api.updated_at ?? null); setLoadError(''); } })
      .catch(error => { if (alive) setLoadError(userFacingMessage(error)); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [companyId, token]);

  // 新增扩展字段模态框
  const [fieldModalOpen, setFieldModalOpen] = useState(false);
  const [fieldForm] = Form.useForm<CustomFieldMetadata>();

  // 实时合规校验
  const validation = useMemo(() => validateCompanySettings(settings), [settings]);

  // 更新单个字段
  const updateField = <K extends keyof CompanySettingsData>(key: K, value: CompanySettingsData[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  // 保存设置：提交后台（后台再核一次上下限与联动规则），以后台返回为准刷新页面
  const handleSave = async () => {
    if (!validation.valid) {
      message.error(validation.issues[0]?.message || '存在未通过的合规参数校验');
      return;
    }
    setSaving(true);
    try {
      const api = await updateCompanySettings(companyId, settingsPayload(settings), token ?? null);
      setSettings(settingsFromApi(api));
      setSavedAt(api.updated_at ?? null);
      message.success('公司设置已保存，新的编辑锁、对话助手与解析设置对之后的操作生效');
    } catch (error) {
      message.error(userFacingMessage(error));
    } finally {
      setSaving(false);
    }
  };

  // 恢复默认
  const handleReset = () => {
    Modal.confirm({
      title: '确认恢复默认设置？',
      content: '恢复后将重置账号安全、编辑锁与大纲预算为平台初始基线值。',
      okText: '确认重置',
      cancelText: '取消',
      onOk: () => {
        setSettings(prev => ({ ...buildInitialCompanySettings(prev.company_id, prev.company_name) }));
        message.info('已填入平台默认值，点“保存企业设置”后生效');
      },
    });
  };

  // 提交新增扩展字段
  const handleAddCustomField = async () => {
    try {
      const values = await fieldForm.validateFields();
      const newField: CustomFieldMetadata = {
        id: `cf-${Date.now()}`,
        field_key: values.field_key.trim(),
        field_name: values.field_name.trim(),
        field_type: values.field_type,
        required: !!values.required,
        scope: values.scope,
        description: values.description?.trim() || '',
      };
      setSettings(prev => ({
        ...prev,
        custom_fields: [...prev.custom_fields, newField],
      }));
      setFieldModalOpen(false);
      fieldForm.resetFields();
      message.success(`已添加扩展字段「${newField.field_name}」`);
    } catch {
      // 表单内联校验
    }
  };

  // 删除扩展字段
  const handleDeleteCustomField = (id: string, name: string) => {
    setSettings(prev => ({
      ...prev,
      custom_fields: prev.custom_fields.filter(f => f.id !== id),
    }));
    message.info(`已移除扩展字段「${name}」`);
  };

  // 扩展字段列定义
  const customFieldColumns = [
    {
      title: '字段标识 Key',
      dataIndex: 'field_key',
      key: 'field_key',
      render: (val: string) => <Text code>{val}</Text>,
    },
    {
      title: '字段名称',
      dataIndex: 'field_name',
      key: 'field_name',
      render: (name: string, record: CustomFieldMetadata) => (
        <Space>
          <Text strong>{name}</Text>
          {record.required && <Tag color="error">必填</Tag>}
        </Space>
      ),
    },
    {
      title: '数据类型',
      dataIndex: 'field_type',
      key: 'field_type',
      render: (type: string) => {
        const typeMap: Record<string, { label: string; color: string }> = {
          text: { label: '单行文本', color: 'blue' },
          number: { label: '数值', color: 'cyan' },
          select: { label: '下拉单选', color: 'purple' },
          date: { label: '日期', color: 'orange' },
        };
        const meta = typeMap[type] || { label: type, color: 'default' };
        return <Tag color={meta.color}>{meta.label}</Tag>;
      },
    },
    {
      title: '适用作用域',
      dataIndex: 'scope',
      key: 'scope',
      render: (scope: string) => {
        const scopeMap: Record<string, string> = {
          project: '项目基本信息',
          chapter: '章节正文',
          tender: '招标文件解析',
        };
        return <Text type="secondary">{scopeMap[scope] || scope}</Text>;
      },
    },
    {
      title: '说明描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => <Text type="secondary">{desc || '-'}</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: CustomFieldMetadata) => (
        <Button
          type="link"
          danger
          disabled={!permission.canEdit}
          onClick={() => handleDeleteCustomField(record.id, record.field_name)}
          data-testid={`btn-delete-field-${record.field_key}`}
        >
          移除
        </Button>
      ),
    },
  ];

  return (
    <div className="company-settings-page" style={{ padding: '4px 0 24px' }}>
      {/* 顶部概览指标与角色徽标 */}
      <Card
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: '16px 24px' }}
        data-testid="company-settings-overview"
      >
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col xs={24} md={14}>
            <Space direction="horizontal" size="middle">
              <SafetyCertificateOutlined style={{ fontSize: 24, color: '#1677ff' }} />
              <div>
                <Space align="center">
                  <span style={{ fontSize: 18, fontWeight: 600 }}>{settings.company_name}</span>
                  <Tag color="geekblue">租户: {settings.company_id}</Tag>
                  <Tag
                    color={permission.isReadOnly ? 'default' : 'green'}
                    data-testid="company-settings-permission-tag"
                  >
                    {permission.roleLabel} · {permission.isReadOnly ? '只读查阅' : '策略管理'}
                  </Tag>
                </Space>
                <div style={{ color: '#8c8c8c', fontSize: 13, marginTop: 4 }}>
                  越界提示平台上下限，公司设置只能调严不可调宽 · 遵循 PRD §5.10.3 与 9.11 联动规则
                </div>
              </div>
            </Space>
          </Col>
          <Col xs={24} md={10} style={{ textAlign: 'right' }}>
            <Space size="middle">
              <div style={{ textAlign: 'center', padding: '0 12px' }}>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>密码基线</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: '#52c41a' }}>
                  {settings.password_min_length}位 / {settings.password_min_char_classes}类
                </div>
              </div>
              <Divider type="vertical" style={{ height: 32 }} />
              <div style={{ textAlign: 'center', padding: '0 12px' }}>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>编辑锁租约</div>
                <div style={{ fontSize: 15, fontWeight: 600 }}>
                  心跳 {settings.edit_lock_heartbeat_seconds}s / 超时 {settings.edit_lock_timeout_minutes}m
                </div>
              </div>
              <Divider type="vertical" style={{ height: 32 }} />
              <div style={{ textAlign: 'center', padding: '0 12px' }}>
                <div style={{ fontSize: 12, color: '#8c8c8c' }}>扩展字段</div>
                <div style={{ fontSize: 15, fontWeight: 600, color: '#1677ff' }}>
                  {settings.custom_fields.length} 项已启用
                </div>
              </div>
            </Space>
          </Col>
        </Row>
      </Card>

      {loadError && (
        <Alert type="error" showIcon style={{ marginBottom: 16 }} data-testid="company-settings-load-error"
          message={`读取公司设置失败：${loadError}`} description="为避免用默认值覆盖已保存的设置，读取成功前不能保存。" />
      )}

      {/* 只读提示条 */}
      {permission.isReadOnly && (
        <Alert
          type="info"
          showIcon
          message={permission.readOnlyNotice}
          style={{ marginBottom: 16 }}
          data-testid="company-settings-readonly-alert"
        />
      )}

      {/* 合规校验拦截警示条 */}
      {!validation.valid && (
        <Alert
          type="error"
          showIcon
          message="企业合规与联动校验未通过（请根据提示调整参数后再行保存）"
          description={
            <ul style={{ margin: '4px 0 0', paddingLeft: 20 }}>
              {validation.issues.map((issue, idx) => (
                <li key={idx}>{issue.message}</li>
              ))}
            </ul>
          }
          style={{ marginBottom: 16 }}
          data-testid="company-settings-validation-alert"
        />
      )}

      {/* 主表单与分组配置 Tabs */}
      <Card bodyStyle={{ padding: '8px 24px 24px' }}>
        <Tabs
          defaultActiveKey="security"
          data-testid="company-settings-tabs"
          items={[
            {
              key: 'security',
              label: (
                <span>
                  <LockOutlined /> 账号安全策略
                </span>
              ),
              children: (
                <div style={{ paddingTop: 16, maxWidth: 800 }}>
                  <Row gutter={[24, 24]}>
                    <Col span={12}>
                      <Form.Item
                        label="密码最少位数"
                        extra={
                          <Space>
                            <Tag color="blue">平台下限: {PLATFORM_SETTING_BOUNDS.password_min_length.min} 位</Tag>
                            <Text type="secondary">公司只能调严（不低于 8 位）</Text>
                          </Space>
                        }
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.password_min_length.min}
                          max={PLATFORM_SETTING_BOUNDS.password_min_length.max}
                          value={settings.password_min_length}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('password_min_length', val || 8)}
                          addonAfter="位"
                          style={{ width: '100%' }}
                          data-testid="input-password-min-length"
                        />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        label="密码最少字符类别"
                        extra={
                          <Space>
                            <Tag color="blue">平台下限: {PLATFORM_SETTING_BOUNDS.password_min_char_classes.min} 类</Tag>
                            <Text type="secondary">大写/小写/数字/标点</Text>
                          </Space>
                        }
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.password_min_char_classes.min}
                          max={PLATFORM_SETTING_BOUNDS.password_min_char_classes.max}
                          value={settings.password_min_char_classes}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('password_min_char_classes', val || 3)}
                          addonAfter="类"
                          style={{ width: '100%' }}
                          data-testid="input-password-min-char-classes"
                        />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        label="连续登录失败锁定次数"
                        extra={<Text type="secondary">平台上限 5 次，公司只能调严</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.max_login_attempts.min}
                          max={PLATFORM_SETTING_BOUNDS.max_login_attempts.max}
                          value={settings.max_login_attempts}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('max_login_attempts', val || 5)}
                          addonAfter="次"
                          style={{ width: '100%' }}
                          data-testid="input-max-login-attempts"
                        />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item
                        label="会话闲置登出超时"
                        extra={<Text type="secondary">长时间无操作自动锁定会话保护数据</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.session_timeout_minutes.min}
                          max={PLATFORM_SETTING_BOUNDS.session_timeout_minutes.max}
                          value={settings.session_timeout_minutes}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('session_timeout_minutes', val || 120)}
                          addonAfter="分钟"
                          style={{ width: '100%' }}
                          data-testid="input-session-timeout"
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'collaboration',
              label: (
                <span>
                  <EditOutlined /> 编辑协同与排他锁
                </span>
              ),
              children: (
                <div style={{ paddingTop: 16, maxWidth: 800 }}>
                  <Alert
                    type="info"
                    showIcon
                    message="规范 9.11 编辑锁心跳三元数学约束"
                    description="规则要求：自动保存间隔必须 <= 心跳间隔；心跳间隔的 10 倍必须 <= 锁超时时间；锁超时时间不能低于 5 分钟。"
                    style={{ marginBottom: 20 }}
                  />
                  <Row gutter={[24, 24]}>
                    <Col span={8}>
                      <Form.Item
                        label="自动保存间隔"
                        extra={<Text type="secondary">范围 5~60 秒，须 &lt;= 心跳</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.editor_autosave_seconds.min}
                          max={PLATFORM_SETTING_BOUNDS.editor_autosave_seconds.max}
                          value={settings.editor_autosave_seconds}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('editor_autosave_seconds', val || 10)}
                          addonAfter="秒"
                          style={{ width: '100%' }}
                          data-testid="input-editor-autosave"
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        label="排他锁心跳间隔"
                        extra={<Text type="secondary">范围 15~120 秒</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.edit_lock_heartbeat_seconds.min}
                          max={PLATFORM_SETTING_BOUNDS.edit_lock_heartbeat_seconds.max}
                          value={settings.edit_lock_heartbeat_seconds}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('edit_lock_heartbeat_seconds', val || 60)}
                          addonAfter="秒"
                          style={{ width: '100%' }}
                          data-testid="input-edit-lock-heartbeat"
                        />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item
                        label="排他锁超时时长"
                        extra={<Text type="secondary">范围 6~60 分钟</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.edit_lock_timeout_minutes.min}
                          max={PLATFORM_SETTING_BOUNDS.edit_lock_timeout_minutes.max}
                          value={settings.edit_lock_timeout_minutes}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('edit_lock_timeout_minutes', val || 30)}
                          addonAfter="分钟"
                          style={{ width: '100%' }}
                          data-testid="input-edit-lock-timeout"
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'export',
              label: (
                <span>
                  <FileDoneOutlined /> 导出交付与合规红线
                </span>
              ),
              children: (
                <div style={{ paddingTop: 16, maxWidth: 800 }}>
                  <Row gutter={[24, 24]}>
                    <Col span={24}>
                      <Card size="small" style={{ background: '#fafafa' }}>
                        <Row justify="space-between" align="middle">
                          <Col>
                            <div>
                              <Text strong style={{ fontSize: 15 }}>废标红线导出门禁</Text>
                              <Tag color="red" style={{ marginLeft: 8 }}>PRD 核心强制规范</Tag>
                            </div>
                            <Text type="secondary">
                              存在任何 blocker 级别合规缺陷时，严格拦截正式递交版 Word 导出（只能调严，不可关闭）。
                            </Text>
                          </Col>
                          <Col>
                            <Switch
                              checked={settings.export_redline_blocking}
                              disabled={true}
                              data-testid="switch-redline-blocking"
                            />
                          </Col>
                        </Row>
                      </Card>
                    </Col>

                    <Col span={24}>
                      <Card size="small" style={{ background: '#fafafa' }}>
                        <Row justify="space-between" align="middle">
                          <Col>
                            <div>
                              <Text strong style={{ fontSize: 15 }}>涉密项目强制使用本地模型</Text>
                              <Tag color="purple" style={{ marginLeft: 8 }}>防数据外泄红线</Tag>
                            </div>
                            <Text type="secondary">
                              敏感项目只能使用本地模型（含备用模型），由系统强制，不能关闭。
                            </Text>
                          </Col>
                          <Col>
                            <Switch
                              checked={settings.force_local_model}
                              disabled={true}
                              data-testid="switch-force-local-model"
                            />
                          </Col>
                        </Row>
                      </Card>
                    </Col>

                    <Col span={24}>
                      <WordTemplateCard companyId={settings.company_id} token={token ?? null} canEdit={permission.canEdit} />
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'assistant',
              label: (
                <span>
                  <EditOutlined /> 对话助手与检查
                </span>
              ),
              children: (
                <div style={{ paddingTop: 16, maxWidth: 800 }}>
                  <Row gutter={[24, 24]}>
                    <Col span={8}>
                      <Form.Item label="启用对话助手">
                        <Switch checked={settings.assistant_enabled} disabled={!permission.canEdit}
                          onChange={val => updateField('assistant_enabled', val)} data-testid="switch-assistant-enabled" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="新会话默认打开知识库">
                        <Switch checked={settings.assistant_kb_default} disabled={!permission.canEdit}
                          onChange={val => updateField('assistant_kb_default', val)} data-testid="switch-assistant-kb-default" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="允许关闭知识库">
                        <Switch checked={settings.assistant_allow_kb_off} disabled={!permission.canEdit}
                          onChange={val => updateField('assistant_allow_kb_off', val)} data-testid="switch-assistant-allow-kb-off" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="修改样例条数" extra={<Text type="secondary">3~5 条</Text>}>
                        <InputNumber min={3} max={5} value={settings.assistant_suggestion_count} disabled={!permission.canEdit}
                          onChange={val => updateField('assistant_suggestion_count', val || 3)} addonAfter="条" style={{ width: '100%' }}
                          data-testid="input-assistant-count" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="解析置信度阈值" extra={<Text type="secondary">低于此值的条目高亮，0.5~0.99</Text>}>
                        <InputNumber min={0.5} max={0.99} step={0.05} value={settings.parse_confidence_threshold} disabled={!permission.canEdit}
                          onChange={val => updateField('parse_confidence_threshold', val ?? 0.8)} style={{ width: '100%' }}
                          data-testid="input-parse-confidence" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="粘贴识别重合比例" extra={<Text type="secondary">粘贴内容与助手输出重合达到时记为对话助手撰写</Text>}>
                        <InputNumber min={0.5} max={1} step={0.05} value={settings.assistant_paste_match_ratio} disabled={!permission.canEdit}
                          onChange={val => updateField('assistant_paste_match_ratio', val ?? 0.8)} style={{ width: '100%' }}
                          data-testid="input-paste-ratio" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="查重连续相同字数" extra={<Text type="secondary">本公司查重判定的连续字数</Text>}>
                        <InputNumber min={5} max={50} value={settings.dup_min_chars} disabled={!permission.canEdit}
                          onChange={val => updateField('dup_min_chars', val || 8)} addonAfter="字" style={{ width: '100%' }}
                          data-testid="input-dup-min-chars" />
                      </Form.Item>
                    </Col>
                    <Col span={8}>
                      <Form.Item label="查重历史年限">
                        <InputNumber min={1} max={120} value={settings.dup_history_months} disabled={!permission.canEdit}
                          onChange={val => updateField('dup_history_months', val || 24)} addonAfter="月" style={{ width: '100%' }}
                          data-testid="input-dup-history-months" />
                      </Form.Item>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'models',
              label: (
                <span>
                  <AppstoreOutlined /> 任务与模型
                </span>
              ),
              children: (
                <div style={{ paddingTop: 16, maxWidth: 900 }}>
                  <TaskModelRoutesCard token={token ?? null} canEdit={permission.canEdit} />
                </div>
              ),
            },
            {
              key: 'outline',
              label: (
                <span>
                  <AppstoreOutlined /> 大纲规划与 AI 预算
                </span>
              ),
              children: (
                <div style={{ paddingTop: 16, maxWidth: 800 }}>
                  <Row gutter={[24, 24]}>
                    <Col span={8}>
                      <Form.Item
                        label="大纲规划层级上限"
                        extra={<Text type="secondary">支持 2~5 级（卷-章-节-小节）</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.outline_max_depth.min}
                          max={PLATFORM_SETTING_BOUNDS.outline_max_depth.max}
                          value={settings.outline_max_depth}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('outline_max_depth', val || 4)}
                          addonAfter="级"
                          style={{ width: '100%' }}
                          data-testid="input-outline-max-depth"
                        />
                      </Form.Item>
                    </Col>

                    <Col span={8}>
                      <Form.Item
                        label="章节默认基准篇幅"
                        extra={<Text type="secondary">单节写作方案目标字数</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.outline_target_words_default.min}
                          max={PLATFORM_SETTING_BOUNDS.outline_target_words_default.max}
                          step={500}
                          value={settings.outline_target_words_default}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('outline_target_words_default', val || 3000)}
                          addonAfter="字"
                          style={{ width: '100%' }}
                          data-testid="input-outline-target-words"
                        />
                      </Form.Item>
                    </Col>

                    <Col span={8}>
                      <Form.Item
                        label="单章 AI 上下文预算"
                        extra={<Text type="secondary">检索增强与 Prompt Token 上限</Text>}
                      >
                        <InputNumber
                          min={PLATFORM_SETTING_BOUNDS.ai_token_budget_per_chapter.min}
                          max={PLATFORM_SETTING_BOUNDS.ai_token_budget_per_chapter.max}
                          step={1024}
                          value={settings.ai_token_budget_per_chapter}
                          disabled={!permission.canEdit}
                          onChange={val => updateField('ai_token_budget_per_chapter', val || 16384)}
                          addonAfter="Token"
                          style={{ width: '100%' }}
                          data-testid="input-ai-token-budget"
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'custom_fields',
              label: (
                <span>
                  <PlusOutlined /> 自定义扩展字段 ({settings.custom_fields.length})
                </span>
              ),
              children: (
                <div style={{ paddingTop: 16 }}>
                  <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text type="secondary">
                      扩展字段可按作用域动态注入项目表单、标书解析与章节编写界面，支持强类型校验。
                    </Text>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      disabled={!permission.canAddCustomField}
                      onClick={() => setFieldModalOpen(true)}
                      data-testid="btn-add-custom-field"
                    >
                      新增扩展字段
                    </Button>
                  </div>
                  <Table
                    columns={customFieldColumns}
                    dataSource={settings.custom_fields}
                    rowKey="id"
                    pagination={false}
                    size="middle"
                    data-testid="custom-fields-table"
                  />
                </div>
              ),
            },
          ]}
        />

        {/* 底部保存与重置控制条 */}
        <Divider style={{ margin: '24px 0 16px' }} />
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <CheckCircleOutlined style={{ color: validation.valid ? '#52c41a' : '#faad14' }} />
              <Text type="secondary">
                {validation.valid ? (savedAt ? `上次保存 ${new Date(savedAt).toLocaleString('zh-CN', { hour12: false })}` : '尚未保存过，当前为平台默认值') : '存在合规风险提示，请按红线规则修正'}
              </Text>
            </Space>
          </Col>
          <Col>
            <Space size="middle">
              <Button
                icon={<ReloadOutlined />}
                disabled={!permission.canEdit}
                onClick={handleReset}
                data-testid="company-settings-reset-btn"
              >
                恢复平台默认
              </Button>
              <Button
                type="primary"
                icon={<SaveOutlined />}
                disabled={!permission.canSave || !validation.valid || loading || !!loadError}
                loading={saving}
                onClick={() => void handleSave()}
                data-testid="company-settings-save-btn"
              >
                保存企业设置
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 新增扩展字段模态框 */}
      <Modal
        title="新增企业自定义扩展字段"
        open={fieldModalOpen}
        onOk={handleAddCustomField}
        onCancel={() => {
          setFieldModalOpen(false);
          fieldForm.resetFields();
        }}
        okText="确定添加"
        cancelText="取消"
        data-testid="modal-add-custom-field"
      >
        <Form form={fieldForm} layout="vertical" initialValues={{ field_type: 'text', scope: 'project', required: false }}>
          <Form.Item
            name="field_key"
            label="字段标识代码 (英文下划线，必须以 custom_ 开头)"
            rules={[
              { required: true, message: '请输入字段标识 Key' },
              { pattern: /^custom_[a-z0-9_]{2,30}$/, message: '格式必须为 custom_ 开头的英文字符下划线' },
            ]}
          >
            <Input placeholder="例如: custom_bid_bond_no" data-testid="input-new-field-key" />
          </Form.Item>
          <Form.Item
            name="field_name"
            label="显示名称"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="例如: 投标保函核销凭证号" data-testid="input-new-field-name" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="field_type" label="数据类型" rules={[{ required: true }]}>
                <Select
                  options={[
                    { value: 'text', label: '单行文本' },
                    { value: 'number', label: '数值' },
                    { value: 'select', label: '下拉选项' },
                    { value: 'date', label: '日期' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="scope" label="挂接作用域" rules={[{ required: true }]}>
                <Select
                  options={[
                    { value: 'project', label: '项目基本信息' },
                    { value: 'chapter', label: '章节编写台' },
                    { value: 'tender', label: '招标文件' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="required" label="是否设为必填项" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="description" label="说明描述（选填）">
            <Input.TextArea rows={2} placeholder="供项目编写人填报时阅读参考" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
