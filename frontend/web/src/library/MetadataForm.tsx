// 为什么有这个文件：封装统一的元数据驱动表单组件（MetadataForm）。
// 它解决什么问题：
// 1. 消费字段元数据自动生成 Ant Design 表单控件与规则；
// 2. 落实 ★ 关键字段修改提示（醒目高亮与横幅警示，提示需重新确认）；
// 3. 实现系统键双行标签排版（上部业务中文名、下部等宽系统键）；
// 4. 实现未启用或不支持字段置灰禁用与 Tooltip 明确悬浮原因解释；
// 5. 适配 string, textarea, number, date, datetime, boolean, select 数据类型，遵循 WCAG AA 4.5:1 对比度标准。

import React, { useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Switch,
  Tooltip,
  Typography,
  type FormInstance,
} from 'antd';
import {
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  LockOutlined,
  QuestionCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';

import {
  formatStarredWarning,
  getModifiedStarredFields,
  hasModifiedStarredFields,
  resolveFieldDisabledState,
  resolveFormSchema,
  resolveTwoLineLabel,
  type FormFieldMeta,
  type FormSchema,
  type ModifiedStarredField,
} from './metadata-form';
import { FormActionFooter } from '../shared/FormActionFooter';
import {
  detectDirtyFields,
  mapServerFieldErrors,
  scrollFieldIntoView,
  type FieldChangeSummary,
} from '../shared/form-interactions';
import { useUnsavedPrompt } from '../shared/useUnsavedPrompt';
import { ReadOnlyField } from '../shell/ReadOnlyGate';

/* ========================================================================= */
/* 1. 组件属性定义                                                           */
/* ========================================================================= */

export interface MetadataFormProps<T extends Record<string, any> = Record<string, any>> {
  /** 表单模式（Schema 对象或分类 category 标识符） */
  schema: FormSchema | string;
  /** 受控表单实例（可选，缺省时组件内部自动创建） */
  form?: FormInstance<T>;
  /** 初始记录值（用于比对 ★ 关键字段是否发生修改） */
  initialValues?: Partial<T>;
  /** 表单提交回调 */
  onFinish?: (values: T) => void | Promise<void>;
  /** 表单字段变动回调 */
  onValuesChange?: (changedValues: Partial<T>, allValues: T) => void;
  /** 当前用户是否具备编辑权限（false 则整表只读置灰） */
  userCanEdit?: boolean;
  /** 是否开启纯文本只读视图（只读成员与集团管理员看到文本而非控件，默认 false） */
  readOnly?: boolean;
  /** 栅格列数：1 栏纵向、2 栏并排或 3 栏（默认 2） */
  columns?: 1 | 2 | 3;
  /** 是否展示顶部 ★ 关键字段修改合规警示横幅（默认 true） */
  showStarredBanner?: boolean;
  /** 是否显示底部保存按钮（默认 true） */
  showSubmitButton?: boolean;
  /** 是否显示重置按钮（默认 false） */
  showResetButton?: boolean;
  /** 是否显示取消按钮（默认 false） */
  showCancelButton?: boolean;
  /** 提交按钮文字（默认 "保存"） */
  submitText?: string;
  /** 重置按钮文字（默认 "重置"） */
  resetText?: string;
  /** 取消按钮文字（默认 "取消"） */
  cancelText?: string;
  /** 提交加载中状态 */
  loading?: boolean;
  /** 是否启用固底吸附操作条（默认 false） */
  stickyFooter?: boolean;
  /** 是否启用离开未保存拦截保护（默认 false） */
  promptOnUnsaved?: boolean;
  /** 服务端返回的错误体（自动就近映射至表单项） */
  serverErrors?: unknown;
  /** 是否在服务端报错时自动平滑滚动聚焦首个错误项（默认 true） */
  autoScrollToError?: boolean;
  /** 点击重置回调 */
  onReset?: () => void;
  /** 点击取消回调（有脏数据时会触发二次确认） */
  onCancel?: () => void;
  /** 底部操作栏自定义扩展内容 */
  footerExtra?: ReactNode;
  /** ★ 关键字段修改状态变动回调 */
  onStarredModifiedChange?: (modifiedFields: ModifiedStarredField[]) => void;
  /** 自定义类名与样式 */
  className?: string;
  style?: CSSProperties;
}

/* ========================================================================= */
/* 2. MetadataForm 组件实现                                                 */
/* ========================================================================= */

export function MetadataForm<T extends Record<string, any> = Record<string, any>>({
  schema,
  form: externalForm,
  initialValues,
  onFinish,
  onValuesChange,
  userCanEdit = true,
  readOnly = false,
  columns = 2,
  showStarredBanner = true,
  showSubmitButton = true,
  showResetButton = false,
  showCancelButton = false,
  submitText = '保存',
  resetText = '重置',
  cancelText = '取消',
  loading = false,
  stickyFooter = false,
  promptOnUnsaved = false,
  serverErrors,
  autoScrollToError = true,
  onReset,
  onCancel,
  footerExtra,
  onStarredModifiedChange,
  className = '',
  style,
}: MetadataFormProps<T>) {
  const [internalForm] = Form.useForm<T>();
  const form = externalForm || internalForm;

  // 1. 解析 FormSchema
  const formSchema = useMemo(() => resolveFormSchema(schema), [schema]);

  // 2. 当前表单实时输入状态（用于与 initialValues 比对 ★ 字段与脏数据）
  const [currentFormValues, setCurrentFormValues] = useState<Record<string, any>>({
    ...(initialValues || {}),
  });

  // 当外部 initialValues 变化时同步刷新
  useEffect(() => {
    if (initialValues) {
      setCurrentFormValues({ ...initialValues });
      form.setFieldsValue(initialValues as any);
    }
  }, [initialValues, form]);

  // 3. 计算被修改的 ★ 关键字段列表
  const modifiedStarredFields = useMemo(() => {
    return getModifiedStarredFields(
      initialValues as Record<string, any>,
      currentFormValues,
      formSchema.fields
    );
  }, [initialValues, currentFormValues, formSchema.fields]);

  const isStarredModified = modifiedStarredFields.length > 0;
  const modifiedKeySet = useMemo(() => {
    return new Set(modifiedStarredFields.map(f => f.field_key));
  }, [modifiedStarredFields]);

  // 计算整体脏数据状态与修改计数
  const dirtySummary = useMemo(() => {
    return detectDirtyFields(
      initialValues as Record<string, any>,
      currentFormValues,
      formSchema.fields.filter(f => f.is_starred).map(f => f.field_key)
    );
  }, [initialValues, currentFormValues, formSchema.fields]);

  // 未保存离开拦截 Hook
  const { isPromptActive, confirmNavigation } = useUnsavedPrompt({
    isDirty: dirtySummary.isDirty,
    enabled: promptOnUnsaved,
  });

  // 响应外部服务端字段错误注入并自动就近滚动定位
  useEffect(() => {
    if (serverErrors) {
      const mapped = mapServerFieldErrors(serverErrors);
      if (mapped.fieldErrors.length > 0) {
        form.setFields(mapped.fieldErrors as any);
        if (autoScrollToError && mapped.firstErrorField) {
          scrollFieldIntoView(mapped.firstErrorField);
        }
      }
    }
  }, [serverErrors, form, autoScrollToError]);

  // 通知外部关键字段状态变化
  useEffect(() => {
    if (onStarredModifiedChange) {
      onStarredModifiedChange(modifiedStarredFields);
    }
  }, [modifiedStarredFields, onStarredModifiedChange]);

  // 4. 监听表单输入变化
  const handleValuesChange = (changedValues: Partial<T>, allValues: T) => {
    setCurrentFormValues({ ...allValues });
    if (onValuesChange) {
      onValuesChange(changedValues, allValues);
    }
  };

  // 重置处理
  const handleReset = () => {
    form.resetFields();
    if (initialValues) {
      form.setFieldsValue(initialValues as any);
      setCurrentFormValues({ ...initialValues });
    } else {
      setCurrentFormValues({});
    }
    if (onReset) {
      onReset();
    }
  };

  // 取消处理
  const handleCancel = () => {
    if (onCancel) {
      if (promptOnUnsaved && dirtySummary.isDirty) {
        confirmNavigation(onCancel);
      } else {
        onCancel();
      }
    }
  };

  // 5. 列跨度计算（基于 columns 属性）
  const defaultColSpan = columns === 1 ? 24 : columns === 3 ? 8 : 12;

  return (
    <div
      className={`icg-metadata-form-wrapper ${className}`}
      style={style}
      data-testid="metadata-form-container"
    >
      {/* 1. ★ 关键字段修改提示横幅（规范 §5.2.2 与 PRD §5.12） */}
      {showStarredBanner && isStarredModified && (
        <Alert
          className="icg-starred-warning-banner page-notice"
          type="warning"
          showIcon
          icon={<WarningOutlined style={{ color: '#9a5608' }} />}
          message="关键字段已修改提醒"
          description={formatStarredWarning(modifiedStarredFields)}
          style={{ marginBottom: 16 }}
          data-testid="starred-modification-alert"
        />
      )}

      {/* 2. 主表单控件 */}
      <Form
        form={form}
        layout="vertical"
        initialValues={initialValues}
        onFinish={onFinish}
        onValuesChange={handleValuesChange}
        disabled={!userCanEdit}
        className="icg-metadata-form"
      >
        <Row gutter={16}>
          {formSchema.fields.map(field => {
            const disabledState = resolveFieldDisabledState(field, userCanEdit);
            const isModified = modifiedKeySet.has(field.field_key);
            const fieldSpan = field.span || (field.render_type === 'textarea' ? 24 : defaultColSpan);

            // 双行表头渲染（规范 9.2 规则 2）
            const labelNode = (
              <div
                className="icg-form-two-line-label"
                data-testid={`form-label-${field.field_key}`}
              >
                <div className="icg-label-primary">
                  {field.is_starred && (
                    <span
                      className="icg-starred-indicator"
                      title="关键字段（修改后需重新人工确认）"
                    >
                      ★{' '}
                    </span>
                  )}
                  <span>{field.label}</span>
                </div>
                {field.system_key && field.system_key !== field.label && (
                  <div className="icg-label-secondary">{field.system_key}</div>
                )}
              </div>
            );

            // 必填与校验规则
            const rules: any[] = [];
            if (field.required && !disabledState.disabled) {
              rules.push({
                required: true,
                message: `请输入${field.label}`,
              });
            }

            // 表单控件输入组件分流
            let inputControl: ReactNode = null;
            const controlDisabled = disabledState.disabled;

            if (readOnly) {
              const fieldValue = currentFormValues[field.field_key];
              inputControl = (
                <ReadOnlyField
                  value={fieldValue}
                  placeholder={field.placeholder || '-'}
                  readOnly={true}
                  testId={`readonly-value-${field.field_key}`}
                />
              );
            } else if (field.render_type === 'textarea' || field.data_type === 'object') {
              inputControl = (
                <Input.TextArea
                  rows={3}
                  placeholder={field.placeholder}
                  disabled={controlDisabled}
                  data-testid={`input-${field.field_key}`}
                />
              );
            } else if (
              field.render_type === 'number' ||
              field.data_type === 'number' ||
              field.data_type === 'integer'
            ) {
              inputControl = (
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder={field.placeholder}
                  addonAfter={field.unit}
                  disabled={controlDisabled}
                  data-testid={`input-${field.field_key}`}
                />
              );
            } else if (field.render_type === 'date' || field.data_type === 'date') {
              inputControl = (
                <Input
                  type="date"
                  placeholder={field.placeholder}
                  disabled={controlDisabled}
                  data-testid={`input-${field.field_key}`}
                />
              );
            } else if (field.render_type === 'datetime' || field.data_type === 'datetime') {
              inputControl = (
                <Input
                  type="datetime-local"
                  placeholder={field.placeholder}
                  disabled={controlDisabled}
                  data-testid={`input-${field.field_key}`}
                />
              );
            } else if (field.render_type === 'switch' || field.data_type === 'boolean') {
              inputControl = (
                <Switch
                  disabled={controlDisabled}
                  data-testid={`input-${field.field_key}`}
                />
              );
            } else if (field.render_type === 'select' || (field.options && field.options.length > 0)) {
              inputControl = (
                <Select
                  options={field.options}
                  placeholder={field.placeholder}
                  allowClear
                  disabled={controlDisabled}
                  data-testid={`input-${field.field_key}`}
                />
              );
            } else {
              // 默认文本输入框
              inputControl = (
                <Input
                  placeholder={field.placeholder}
                  disabled={controlDisabled}
                  data-testid={`input-${field.field_key}`}
                />
              );
            }

            // 若置灰禁用且有原因解释，包裹 Tooltip 并在下方给出温和辅助说明
            if (!readOnly && disabledState.disabled && disabledState.reason) {
              inputControl = (
                <Tooltip title={disabledState.reason} placement="topLeft">
                  <div className="icg-disabled-control-wrapper">{inputControl}</div>
                </Tooltip>
              );
            }

            return (
              <Col span={fieldSpan} key={field.field_key}>
                <Form.Item
                  name={field.field_key}
                  label={labelNode}
                  rules={rules}
                  valuePropName={
                    field.render_type === 'switch' || field.data_type === 'boolean'
                      ? 'checked'
                      : 'value'
                  }
                  className={`icg-metadata-form-item ${
                    isModified ? 'icg-form-item-starred-modified' : ''
                  }`}
                  data-testid={`form-item-${field.field_key}`}
                  extra={
                    disabledState.disabled && disabledState.reason ? (
                      <span className="icg-field-disabled-hint">
                        <LockOutlined style={{ marginRight: 4 }} />
                        {disabledState.reason}
                      </span>
                    ) : field.description ? (
                      <span className="muted" style={{ fontSize: 12 }}>
                        {field.description}
                      </span>
                    ) : undefined
                  }
                >
                  {inputControl}
                </Form.Item>
              </Col>
            );
          })}
        </Row>

        {/* 3. 表单底部保存与操作栏（集成 FormActionFooter，支持 Sticky 固底与脏数据状态） */}
        {!readOnly && (showSubmitButton || footerExtra || showResetButton || showCancelButton) && (
          <FormActionFooter
            sticky={stickyFooter}
            isDirty={dirtySummary.isDirty}
            modifiedCount={dirtySummary.modifiedCount}
            starredModifiedCount={dirtySummary.starredModifiedCount}
            summaryText={dirtySummary.summaryText}
            loading={loading}
            disabled={!userCanEdit}
            submitText={submitText}
            resetText={resetText}
            cancelText={cancelText}
            showSubmit={showSubmitButton}
            showReset={showResetButton}
            showCancel={showCancelButton}
            onReset={handleReset}
            onCancel={handleCancel}
            extra={
              <Space wrap>
                {footerExtra}
                {isStarredModified && (
                  <span className="orange" style={{ fontSize: 12 }}>
                    <WarningOutlined style={{ marginRight: 4 }} />
                    检测到 ★ 关键字段变动，保存后将需重新核对确认。
                  </span>
                )}
              </Space>
            }
          />
        )}
      </Form>
    </div>
  );
}

export default MetadataForm;
