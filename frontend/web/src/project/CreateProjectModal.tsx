// 为什么有这个文件：提取新建投标项目弹窗，降低 App.tsx 单文件行数。
// 它解决什么问题：解耦新建项目表单交互，遵循 Layout First 原则，保持清晰的字段层级与校验规则。

import React from 'react';
import { Alert, Form, Input, Modal, Radio, Select, type FormInstance } from 'antd';
import { VOLUME_MODE_OPTIONS } from './project-volumes.ts';

export interface CreateProjectModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: () => void;
  confirmLoading: boolean;
  canCreate: boolean;
  form: FormInstance;
}

export function CreateProjectModal({
  open,
  onCancel,
  onOk,
  confirmLoading,
  canCreate,
  form,
}: CreateProjectModalProps) {
  return (
    <Modal
      title="新建投标项目"
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      confirmLoading={confirmLoading}
      okText="创建并上传招标文件"
      okButtonProps={{ disabled: !canCreate }}
      width={600}
    >
      <Alert
        type="info"
        showIcon
        message="选择本项目编写范围"
        description="两册模式：技术、商务分册分别定稿，导出后由合标负责人合标。只写技术标：只建技术分册，商务/资格条款标为不在本项目范围，递交版只出一份技术标，不生成合标核对清单。报价由人在系统外处理。"
      />
      <Form form={form} layout="vertical" style={{ marginTop: 20 }} initialValues={{ sensitive: false, volume_mode: 'both' }}>
        <Form.Item name="volume_mode" label="编写范围">
          <Radio.Group data-testid="volume-mode-radio" options={VOLUME_MODE_OPTIONS} />
        </Form.Item>
        <Form.Item
          name="name"
          label="项目名称"
          rules={[{ required: true, whitespace: true, message: '请填写项目名称' }, { max: 200 }]}
        >
          <Input placeholder="请输入完整项目名称" />
        </Form.Item>
        <Form.Item name="tender_number" label="招标编号">
          <Input />
        </Form.Item>
        <Form.Item name="deadline" label="投标截止时间">
          <Input placeholder="2026-12-31 17:00（北京时间）" />
        </Form.Item>
        <Form.Item name="sensitive" label="敏感项目">
          <Select
            options={[
              { value: false, label: '普通项目' },
              { value: true, label: '敏感 · 只能使用本地服务' },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
