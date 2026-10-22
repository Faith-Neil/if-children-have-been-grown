// 为什么有这个文件：落实 APP-M2-T026 (A-01 公司与租户管理页) 与 PRD v1.8 §5.10.1、§5.10.2、§6.9、§7.1。
// 它解决什么问题：支持公司多租户基本信息与空间状态维护、安全合规参数配置（脱敏强规则生效标识、本地模型强制开关、密码安全策略只严不松、编辑锁超时与心跳三元联动），并落实集团管理员/公司管理员精细化权限感知与停用二次确认防线。

import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  App as AntApp,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Radio,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Tabs,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  CheckCircleOutlined,
  DatabaseOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  LockOutlined,
  SafetyCertificateOutlined,
  SaveOutlined,
  StopOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons';
import type { Account, ApplicationSession } from '../shared/types.ts';
import {
  canManageCompanySettings,
  DEFAULT_COMPANIES,
  PLATFORM_BASELINE,
  validateCompanyComplianceSettings,
  validateDisableConfirmation,
  type CompanyAdminPermissionResult,
  type CompanyComplianceSettings,
  type CompanyTenantInfo,
} from './company-manage-core.ts';

const { Title, Text, Paragraph } = Typography;

export interface CompanyManagePageProps {
  session?: ApplicationSession | null;
  currentUser?: Account | null;
  companies?: CompanyTenantInfo[];
  onSaveComplianceSettings?: (companyId: string, updated: CompanyComplianceSettings) => Promise<void> | void;
  onDisableCompany?: (companyId: string) => Promise<void> | void;
}

export function CompanyManagePage({
  session,
  currentUser,
  companies: propCompanies,
  onSaveComplianceSettings,
  onDisableCompany,
}: CompanyManagePageProps) {
  const { message, modal } = AntApp.useApp();
  const [companiesList, setCompaniesList] = useState<CompanyTenantInfo[]>(propCompanies || DEFAULT_COMPANIES);

  // 1. 当前选中的公司
  const initialCompanyId = currentUser?.company_id || session?.scope.active_company_id || 'alpha';
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>(initialCompanyId);

  const activeCompany = useMemo(() => {
    return companiesList.find(c => c.id === selectedCompanyId) || companiesList[0];
  }, [companiesList, selectedCompanyId]);

  // 2. 权限感知判定
  const userRole = session?.user?.primary_role || currentUser?.role || 'viewer';
  const userCompanyId = currentUser?.company_id || session?.scope.active_company_id;

  const permissions: CompanyAdminPermissionResult = useMemo(() => {
    return canManageCompanySettings({
      role: userRole,
      targetCompanyId: activeCompany?.id || '',
      userCompanyId,
    });
  }, [userRole, activeCompany?.id, userCompanyId]);

  // 3. 表单与合规设置状态
  const [form] = Form.useForm<CompanyComplianceSettings>();
  const [formDirty, setFormDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // 初始化设置表单数据
  useEffect(() => {
    if (activeCompany) {
      form.setFieldsValue({ ...activeCompany.settings });
      setFormDirty(false);
    }
  }, [activeCompany, form]);

  // 4. 停用二次确认弹窗状态
  const [disableModalOpen, setDisableModalOpen] = useState(false);
  const [confirmInputName, setConfirmInputName] = useState('');
  const [disabling, setDisabling] = useState(false);

  // 5. 保存合规配置
  const handleSaveCompliance = async () => {
    if (!permissions.canEdit) {
      message.error(permissions.readOnlyNotice || '当前角色无权修改合规配置。');
      return;
    }

    try {
      const values = await form.validateFields();
      // 强校验合规规则
      const validation = validateCompanyComplianceSettings(values);
      if (!validation.valid) {
        const errorMessages = validation.issues.filter(i => i.severity === 'error').map(i => i.message);
        modal.error({
          title: '合规参数校验未通过',
          content: (
            <div>
              <p>检测到不符合平台安全合规基线的配置，无法保存：</p>
              <ul>
                {errorMessages.map((msg, idx) => (
                  <li key={idx} style={{ color: '#d9363e', marginBottom: 4 }}>
                    {msg}
                  </li>
                ))}
              </ul>
            </div>
          ),
        });
        return;
      }

      setSaving(true);
      if (onSaveComplianceSettings) {
        await onSaveComplianceSettings(activeCompany.id, values);
      }

      // 本地状态同步
      setCompaniesList(prev =>
        prev.map(c => (c.id === activeCompany.id ? { ...c, settings: { ...c.settings, ...values } } : c))
      );
      setFormDirty(false);
      message.success('企业合规与安全策略已成功保存，并在本公司生效。');
    } catch (err) {
      if (err instanceof Error) {
        message.error(`保存失败: ${err.message}`);
      }
    } finally {
      setSaving(false);
    }
  };

  // 6. 执行停用二次确认
  const handleConfirmDisable = async () => {
    if (!validateDisableConfirmation(confirmInputName, activeCompany.name)) {
      message.error('输入的确认公司名称与实际名称不一致，请仔细核对。');
      return;
    }

    setDisabling(true);
    try {
      if (onDisableCompany) {
        await onDisableCompany(activeCompany.id);
      }
      setCompaniesList(prev =>
        prev.map(c => (c.id === activeCompany.id ? { ...c, status: 'disabled' } : c))
      );
      setDisableModalOpen(false);
      setConfirmInputName('');
      message.warning(`公司【${activeCompany.name}】已成功停用，名下用户登录已被阻断，数据已安全封存。`);
    } catch (err) {
      if (err instanceof Error) {
        message.error(`停用操作失败: ${err.message}`);
      }
    } finally {
      setDisabling(false);
    }
  };

  return (
    <div className="company-manage-page" style={{ paddingBottom: 32 }}>
      {/* 顶部多租户切换与权限告示条 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <ApartmentOutlined style={{ marginRight: 8, color: '#1e4db7' }} />
            企业租户与安全合规中心 (A-01)
          </Title>
          <Text type="secondary" style={{ fontSize: 13 }}>
            维护法人主体基本资料、多租户空间隔离状态及合规基线参数（脱敏强规则、涉密模型约束、密码策略与排他锁心跳联动）
          </Text>
        </div>

        {/* 跨租户查看下拉 (集团管理员 / 平台管理员可见) */}
        {(userRole === 'group_admin' || userRole === 'platform_admin') && (
          <Space>
            <Text style={{ fontSize: 13 }}>切换公司租户:</Text>
            <Select
              style={{ width: 220 }}
              value={selectedCompanyId}
              onChange={setSelectedCompanyId}
              options={companiesList.map(c => ({
                value: c.id,
                label: `${c.name} ${c.status === 'disabled' ? '(已停用)' : ''}`,
              }))}
            />
          </Space>
        )}
      </div>

      {/* 权限视角提示条 (集团管理员视角或普通只读视角) */}
      {!permissions.canEdit && (
        <Alert
          type="info"
          showIcon
          icon={<UserSwitchOutlined style={{ color: '#1e4db7' }} />}
          message={`【权限感知模式】${permissions.roleLabel} 浏览视角`}
          description={
            permissions.readOnlyNotice ||
            '您当前的角色仅具备审阅查看资质，非公司管理员角色不能修改本公司合规配置或停用公司。所有管理修改按钮已自动隐藏。'
          }
          style={{ marginBottom: 16, backgroundColor: '#f0f5ff', borderColor: '#adc6ff' }}
        />
      )}

      {/* 公司基本资料与空间状态卡片 */}
      <Card
        size="small"
        style={{ marginBottom: 16, borderRadius: 6, borderColor: '#e8ebf0' }}
        title={
          <Space>
            <span style={{ fontSize: 14, fontWeight: 600 }}>{activeCompany.name}</span>
            <Tag color={activeCompany.status === 'active' ? 'success' : 'error'}>
              {activeCompany.status === 'active' ? '正常运营' : '已停用'}
            </Tag>
            <Tag color="blue">{activeCompany.group_name}</Tag>
          </Space>
        }
        extra={
          // 仅具备停用权限的平台管理员展示停用按钮，非公司管理员/只读角色隐藏
          permissions.canDisable && activeCompany.status === 'active' ? (
            <Button
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => {
                setConfirmInputName('');
                setDisableModalOpen(true);
              }}
            >
              停用公司租户
            </Button>
          ) : null
        }
      >
        <Descriptions column={{ xs: 1, sm: 2, md: 4 }} size="small" bordered>
          <Descriptions.Item label="统一社会信用代码">
            <Text code copyable>{activeCompany.credit_code}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="法人代表">{activeCompany.legal_person}</Descriptions.Item>
          <Descriptions.Item label="所属集团">{activeCompany.group_name}</Descriptions.Item>
          <Descriptions.Item label="租户开通时间">{activeCompany.created_at}</Descriptions.Item>
          <Descriptions.Item label="资料库隔离空间">
            <Space>
              <DatabaseOutlined style={{ color: '#52c41a' }} />
              <Text style={{ fontSize: 12 }}>{activeCompany.storage_space_id}</Text>
              <Badge status="success" text="逻辑物理隔离" />
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="RAGFlow 知识库">
            <Space>
              <CheckCircleOutlined style={{ color: '#1890ff' }} />
              <Text style={{ fontSize: 12 }}>{activeCompany.rag_collection_id}</Text>
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="注册员工数">
            <Text strong>{activeCompany.user_count} 人</Text>
          </Descriptions.Item>
          <Descriptions.Item label="在编项目数">
            <Text strong>{activeCompany.project_count} 个</Text>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 安全合规参数配置主面板 */}
      <Card
        size="small"
        style={{ borderRadius: 6, borderColor: '#e8ebf0' }}
        title={
          <Space>
            <SafetyCertificateOutlined style={{ color: '#1e4db7' }} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>安全与合规参数配置</span>
            {formDirty && <Badge status="processing" text="有未保存修改" />}
          </Space>
        }
        extra={
          // 仅公司管理员或平台管理员可见“保存合规配置”按钮，集团管理员/只读人员隐藏
          permissions.canEdit ? (
            <Button
              type="primary"
              size="small"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSaveCompliance}
            >
              保存合规配置
            </Button>
          ) : (
            <Tag color="default">当前视角只读 · 无保存权限</Tag>
          )
        }
      >
        <Form
          form={form}
          layout="vertical"
          disabled={!permissions.canEdit}
          onValuesChange={() => setFormDirty(true)}
        >
          <Tabs
            defaultActiveKey="mask"
            items={[
              {
                key: 'mask',
                label: (
                  <Space>
                    <SafetyCertificateOutlined />
                    <span>高敏脱敏规则 (PRD §6.9)</span>
                  </Space>
                ),
                children: (
                  <div style={{ paddingTop: 8 }}>
                    <Alert
                      type="success"
                      showIcon
                      message="【合规底线防御】脱敏强规则已强制生效"
                      description="依据 PRD §6.9 及信息安全规范，每类保留位数可调，但绝不可关闭掩码，系统不提供关闭掩码的开关。标书编辑台与内部稿必须始终对身份证、银行卡等高敏信息保持脱敏。"
                      style={{ marginBottom: 16 }}
                    />

                    <Row gutter={[24, 16]}>
                      <Col xs={24} md={12}>
                        <Form.Item
                          name="mask_strict_mode_enabled"
                          label="脱敏强合规生效标识"
                          tooltip="系统安全底线要求，必须保持启用，不可关闭"
                        >
                          <Space>
                            <Switch checked disabled />
                            <Tag color="green" style={{ marginLeft: 8 }}>
                              强规则已生效 · 严禁关闭
                            </Tag>
                          </Space>
                        </Form.Item>

                        <Form.Item
                          name="mask_id_card_mode"
                          label="居民身份证脱敏模式"
                          tooltip="标准模式保留前6后4位；严格模式仅保留前3后4位"
                        >
                          <Radio.Group>
                            <Radio.Button value="standard">标准模式 (保留前 6 后 4)</Radio.Button>
                            <Radio.Button value="strict">严格模式 (保留前 3 后 4)</Radio.Button>
                          </Radio.Group>
                        </Form.Item>
                      </Col>

                      <Col xs={24} md={12}>
                        <Form.Item label="手机号码脱敏规则">
                          <Input value="保留前 3 位与后 4 位，中间 4 位固定掩码 (380****1234)" disabled />
                        </Form.Item>

                        <Form.Item label="银行账户脱敏规则">
                          <Input value="仅保留后 4 位明文，前序全掩码 (************5678)" disabled />
                        </Form.Item>
                      </Col>
                    </Row>
                  </div>
                ),
              },
              {
                key: 'local_model',
                label: (
                  <Space>
                    <ThunderboltOutlined />
                    <span>本地模型强制约束 (PRD §6.4)</span>
                  </Space>
                ),
                children: (
                  <div style={{ paddingTop: 8 }}>
                    <Alert
                      type="warning"
                      showIcon
                      message="涉密项目本地化强制运行机制"
                      description="当开启此合规选项时，本公司所有涉密标书及包含商业秘密的任务，强制仅允许在内网本地大模型（vLLM）和本地 MinerU 离线运行，物理阻断云端外发路径。"
                      style={{ marginBottom: 16 }}
                    />

                    <Form.Item
                      name="force_local_model"
                      valuePropName="checked"
                      label="涉密与敏感项目强制本地模型"
                      tooltip="开启后，所有标记为敏感的项目将彻底禁止调用公网大模型 API"
                    >
                      <Switch checkedChildren="强制本地" unCheckedChildren="允许合规云端" />
                    </Form.Item>

                    <Paragraph type="secondary" style={{ fontSize: 13 }}>
                      说明：非涉密普通项目若需使用云端大模型，仍需经过服务健康检测与脱敏审计，调用明细将如实记录在 A-06 审计日志中。
                    </Paragraph>
                  </div>
                ),
              },
              {
                key: 'password',
                label: (
                  <Space>
                    <LockOutlined />
                    <span>密码安全策略 (PRD §5.10.2)</span>
                  </Space>
                ),
                children: (
                  <div style={{ paddingTop: 8 }}>
                    <Alert
                      type="info"
                      showIcon
                      message="账号密码强度只能调严，绝不可低于平台默认基线"
                      description="修改密码安全策略后，将在本公司所有账号下次修改密码或首次登录时生效，已有账号原密码仍可使用至下一次轮换。"
                      style={{ marginBottom: 16 }}
                    />

                    <Row gutter={[24, 16]}>
                      <Col xs={24} sm={12}>
                        <Form.Item
                          name="password_min_length"
                          label="密码最少字符长度"
                          tooltip={`不能低于平台安全基线 ${PLATFORM_BASELINE.PASSWORD_MIN_LENGTH} 位，可调高到 12 位或以上（上限 32 位）`}
                          rules={[
                            { required: true, message: '请设置密码最少位数' },
                            {
                              type: 'number',
                              min: PLATFORM_BASELINE.PASSWORD_MIN_LENGTH,
                              max: 32,
                              message: `密码长度不能低于平台基线 ${PLATFORM_BASELINE.PASSWORD_MIN_LENGTH} 位，且不超过 32 位`,
                            },
                          ]}
                        >
                          <InputNumber min={8} max={32} style={{ width: '100%' }} addonAfter="位字符" />
                        </Form.Item>
                      </Col>

                      <Col xs={24} sm={12}>
                        <Form.Item
                          name="password_min_char_classes"
                          label="至少包含的字符类别数"
                          tooltip="字符分为大写字母、小写字母、数字、特殊符号 4 类，至少包含 3 类或 4 类"
                          rules={[
                            { required: true, message: '请设置最少字符类数' },
                            {
                              type: 'number',
                              min: PLATFORM_BASELINE.PASSWORD_MIN_CHAR_CLASSES,
                              max: 4,
                              message: `字符类别数不能低于平台基线 ${PLATFORM_BASELINE.PASSWORD_MIN_CHAR_CLASSES} 类`,
                            },
                          ]}
                        >
                          <InputNumber min={3} max={4} style={{ width: '100%' }} addonAfter="类字符 (大写/小写/数字/符号)" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </div>
                ),
              },
              {
                key: 'lock_heartbeat',
                label: (
                  <Space>
                    <SyncOutlined />
                    <span>编辑锁与自动保存联动 (PRD §5.11.9)</span>
                  </Space>
                ),
                children: (
                  <div style={{ paddingTop: 8 }}>
                    <Alert
                      type="info"
                      showIcon
                      message="心跳、自动保存与锁超时三元数学约束校验"
                      description="公式要求：① 自动保存间隔 ≤ 心跳间隔；② 心跳间隔 × 10 ≤ 锁超时秒数；③ 锁超时必须大于释放前强提示的 5 分钟。"
                      style={{ marginBottom: 16 }}
                    />

                    <Row gutter={[24, 16]}>
                      <Col xs={24} sm={8}>
                        <Form.Item
                          name="editor_autosave_seconds"
                          label="自动保存草稿间隔"
                          tooltip="自动保存只保存草稿，不刷新编辑锁"
                          rules={[{ required: true, message: '请配置自动保存间隔' }]}
                        >
                          <InputNumber min={5} max={60} style={{ width: '100%' }} addonAfter="秒 (范围 5~60)" />
                        </Form.Item>
                      </Col>

                      <Col xs={24} sm={8}>
                        <Form.Item
                          name="edit_lock_heartbeat_seconds"
                          label="编辑锁心跳间隔"
                          tooltip="用户在编辑区有操作时刷新锁状态，无操作不发心跳"
                          rules={[{ required: true, message: '请配置心跳间隔' }]}
                        >
                          <InputNumber min={15} max={120} style={{ width: '100%' }} addonAfter="秒 (范围 15~120)" />
                        </Form.Item>
                      </Col>

                      <Col xs={24} sm={8}>
                        <Form.Item
                          name="edit_lock_timeout_minutes"
                          label="编辑锁超时时长"
                          tooltip="连续无操作超过该时间自动释放独占编辑锁"
                          rules={[{ required: true, message: '请配置锁超时时间' }]}
                        >
                          <InputNumber min={10} max={120} style={{ width: '100%' }} addonAfter="分钟 (范围 10~120)" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </div>
                ),
              },
            ]}
          />
        </Form>
      </Card>

      {/* 停用公司二次确认弹窗 (PRD §5.10.1 约束：停用二次确认) */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#d9363e' }} />
            <span>高危操作二次确认：停用企业租户</span>
          </Space>
        }
        open={disableModalOpen}
        onCancel={() => setDisableModalOpen(false)}
        onOk={handleConfirmDisable}
        confirmLoading={disabling}
        okText="确认停用并封存"
        okButtonProps={{ danger: true, disabled: confirmInputName.trim() !== activeCompany.name }}
      >
        <Alert
          type="error"
          showIcon
          message="停用后该公司所有用户将无法登录系统！"
          description="停用属于不可逆安全管控。停用后该租户名下所有成员登录受阻，所有未完成长任务将被终止；但已沉淀的投标资料、向量知识库与审计留痕将受到加密封存。"
          style={{ marginBottom: 16 }}
        />
        <div style={{ marginBottom: 8, fontSize: 13, color: '#1d2129' }}>
          为防止误操作，请输入目标公司的完整名称：<strong>{activeCompany.name}</strong>
        </div>
        <Input
          placeholder="请输入完整公司名称进行确认"
          value={confirmInputName}
          onChange={e => setConfirmInputName(e.target.value)}
        />
      </Modal>
    </div>
  );
}

export default CompanyManagePage;
