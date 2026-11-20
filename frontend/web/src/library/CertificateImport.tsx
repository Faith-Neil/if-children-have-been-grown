// 为什么有这个文件：资料库里“从证书附件识别”：上传证书扫描件 → 知识库证书流程解析抽取 → 生成待核验资料。
// 它解决什么问题：资料管理员不必逐字录入证书名称、编号、发证机构、有效期；抽取结果只是草稿，
// 状态固定为“待核验”，必须对照原件确认后才可引用（PRD 原则 1）。

import React from 'react';
import { Alert, Typography } from 'antd';

export interface CertificateImportProps {
  token: string | null;
  disabled?: boolean;
  onDrafted?: () => void;
  wait?: (ms: number) => Promise<void>;
}

/** 证书附件数据集入口已下线；保留挂载位避免父页面布局抖动。 */
export function CertificateImport(_props: CertificateImportProps) {
  return (
    <Alert
      type="info"
      showIcon
      message="证书附件识别已停用"
      description={
        <Typography.Text type="secondary">
          请在公司知识库管理里维护资质资料，或在资料库中手工录入并确认。
        </Typography.Text>
      }
    />
  );
}

export default CertificateImport;
