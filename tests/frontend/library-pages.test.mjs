// 为什么有这个文件：覆盖企业资料库通用列表（T046）与详情通用页/附件槽位（T047）的核心业务规则与安全防线。
// 它解决什么问题：验证五大分类导航、状态推导（有效/待核验/过期/排除）、引用可用性诊断（缺协议/已过期/待核验）、高敏脱敏权限与附件SHA256防篡改。
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LIBRARY_CATEGORIES,
  getCategoryLabel,
  deriveEvidenceStatus,
  checkEvidenceUsability,
  filterEvidenceList,
  canManageLibrary,
  canRevealSensitiveField,
  maskSensitiveValue,
  verifyAttachmentSecurity,
} from '../../frontend/web/src/library-pages-core.ts';

test('LIBRARY_CATEGORIES defines standard categories and supports label lookup', () => {
  const keys = LIBRARY_CATEGORIES.map(c => c.key);
  assert.deepEqual(keys, ['all', 'qualification', 'financial', 'personnel', 'case', 'template']);
  
  assert.equal(getCategoryLabel('qualification'), '主体资质');
  assert.equal(getCategoryLabel('financial'), '财务审计');
  assert.equal(getCategoryLabel('personnel'), '人员证书');
  assert.equal(getCategoryLabel('case'), '业绩案例');
  assert.equal(getCategoryLabel('template'), '通用模板');
  assert.equal(getCategoryLabel('unknown_key'), 'unknown_key');
});

test('deriveEvidenceStatus accurately computes status with expiration checks', () => {
  const todayStr = '2026-10-22';
  const pastStr = '2025-01-01';
  const futureStr = '2028-12-31';

  // Excluded / rejected always takes priority
  assert.equal(deriveEvidenceStatus({ status: 'rejected', valid_until: futureStr }, todayStr), 'rejected');

  // Expired item
  assert.equal(deriveEvidenceStatus({ status: 'confirmed', valid_until: pastStr }, todayStr), 'expired');
  assert.equal(deriveEvidenceStatus({ status: 'pending', valid_until: pastStr }, todayStr), 'expired');

  // Pending item (not expired)
  assert.equal(deriveEvidenceStatus({ status: 'pending', valid_until: futureStr }, todayStr), 'pending');
  assert.equal(deriveEvidenceStatus({ status: 'pending' }, todayStr), 'pending');

  // Confirmed item (valid date or no expiry)
  assert.equal(deriveEvidenceStatus({ status: 'confirmed', valid_until: futureStr }, todayStr), 'confirmed');
  assert.equal(deriveEvidenceStatus({ status: 'confirmed' }, todayStr), 'confirmed');
});

test('checkEvidenceUsability diagnoses invalid reasons for project citation', () => {
  const todayStr = '2026-10-22';

  // History type is reference only
  const historyItem = { id: 'h1', type: 'history', status: 'confirmed', valid_until: '2028-01-01' };
  const historyCheck = checkEvidenceUsability(historyItem, null, todayStr);
  assert.equal(historyCheck.usable, false);
  assert.match(historyCheck.reason, /只能参考/);

  // Expired item cannot be used
  const expiredItem = { id: 'e1', type: 'qualification', status: 'confirmed', valid_until: '2024-01-01' };
  const expiredCheck = checkEvidenceUsability(expiredItem, null, todayStr);
  assert.equal(expiredCheck.usable, false);
  assert.match(expiredCheck.reason, /已过期/);

  // Rejected item cannot be used
  const rejectedItem = { id: 'r1', type: 'qualification', status: 'rejected', valid_until: '2028-01-01' };
  const rejectedCheck = checkEvidenceUsability(rejectedItem, null, todayStr);
  assert.equal(rejectedCheck.usable, false);
  assert.match(rejectedCheck.reason, /已排除/);

  // Pending item cannot be used
  const pendingItem = { id: 'p1', type: 'qualification', status: 'pending', valid_until: '2028-01-01' };
  const pendingCheck = checkEvidenceUsability(pendingItem, null, todayStr);
  assert.equal(pendingCheck.usable, false);
  assert.match(pendingCheck.reason, /待核验/);

  // Missing cooperation agreement
  const coopItem = {
    id: 'c1',
    type: 'performance',
    status: 'confirmed',
    valid_until: '2028-01-01',
    needs_cooperation_agreement: true,
    cooperation_agreement_id: undefined,
  };
  const coopCheck = checkEvidenceUsability(coopItem, null, todayStr);
  assert.equal(coopCheck.usable, false);
  assert.match(coopCheck.reason, /缺合作协议/);

  // With cooperation agreement: valid!
  const coopValidItem = {
    ...coopItem,
    cooperation_agreement_id: 'agr-001',
  };
  const coopValidCheck = checkEvidenceUsability(coopValidItem, null, todayStr);
  assert.equal(coopValidCheck.usable, true);

  // Standard valid item
  const validItem = { id: 'v1', type: 'qualification', status: 'confirmed', valid_until: '2028-01-01' };
  const validCheck = checkEvidenceUsability(validItem, null, todayStr);
  assert.equal(validCheck.usable, true);
});

test('filterEvidenceList filters by category, status, and multi-field keywords', () => {
  const items = [
    {
      id: '1',
      name: '增值电信业务经营许可证',
      type: 'qualification',
      status: 'confirmed',
      valid_until: '2028-01-01',
      system_key: 'QUAL_ICP_2026',
      license_number: 'B2-20260001',
      content: '互联网信息服务业务',
    },
    {
      id: '2',
      name: '2025年度财务审计报告',
      type: 'financial',
      status: 'confirmed',
      valid_until: '2025-05-01', // expired relative to 2026
      system_key: 'FIN_AUDIT_2025',
      content: '无保留意见审计报告',
    },
    {
      id: '3',
      name: 'PMP 项目管理专业人员证书',
      type: 'personnel',
      status: 'pending',
      valid_until: '2027-12-31',
      owner_name: '张三',
      id_card: '110101199003072345',
      content: '项目管理协会认证',
    },
    {
      id: '4',
      name: '某省电子政务云平台实施合同',
      type: 'case',
      status: 'rejected',
      valid_until: '2029-01-01',
      system_key: 'PERF_GOV_2024',
      content: '500万级别云平台建设',
    },
  ];

  const nowStr = '2026-10-22';

  // 1. Filter by category
  const qualResults = filterEvidenceList(items, { category: 'qualification' }, nowStr);
  assert.equal(qualResults.length, 1);
  assert.equal(qualResults[0].id, '1');

  // 2. Filter by status 'expired'
  const expiredResults = filterEvidenceList(items, { category: 'all', status: 'expired' }, nowStr);
  assert.equal(expiredResults.length, 1);
  assert.equal(expiredResults[0].id, '2');

  // 3. Filter by status 'pending'
  const pendingResults = filterEvidenceList(items, { category: 'all', status: 'pending' }, nowStr);
  assert.equal(pendingResults.length, 1);
  assert.equal(pendingResults[0].id, '3');

  // 4. Keyword search on owner_name
  const ownerResults = filterEvidenceList(items, { category: 'all', keyword: '张三' }, nowStr);
  assert.equal(ownerResults.length, 1);
  assert.equal(ownerResults[0].id, '3');

  // 5. Keyword search on license_number
  const licenseResults = filterEvidenceList(items, { category: 'all', keyword: '20260001' }, nowStr);
  assert.equal(licenseResults.length, 1);
  assert.equal(licenseResults[0].id, '1');

  // 6. Keyword search on system_key
  const keyResults = filterEvidenceList(items, { category: 'all', keyword: 'QUAL_ICP' }, nowStr);
  assert.equal(keyResults.length, 1);
  assert.equal(keyResults[0].id, '1');

  // 7. Keyword search on content
  const contentResults = filterEvidenceList(items, { category: 'all', keyword: '电子政务' }, nowStr);
  assert.equal(contentResults.length, 1);
  assert.equal(contentResults[0].id, '4');
});

test('RBAC controls library management permissions', () => {
  // Can manage
  assert.equal(canManageLibrary('admin'), true);
  assert.equal(canManageLibrary('bidding_manager'), true);
  assert.equal(canManageLibrary('legal_reviewer'), true);
  assert.equal(canManageLibrary('quality_auditor'), true);
  assert.equal(canManageLibrary('hr_specialist'), true);

  // Cannot manage
  assert.equal(canManageLibrary('viewer'), false);
  assert.equal(canManageLibrary('bidder'), false);
  assert.equal(canManageLibrary('guest'), false);
  assert.equal(canManageLibrary(undefined), false);
});

test('RBAC controls sensitive field reveal whitelist and masking', () => {
  // Whitelist to unmask sensitive personal records
  assert.equal(canRevealSensitiveField('admin'), true);
  assert.equal(canRevealSensitiveField('legal_reviewer'), true);
  assert.equal(canRevealSensitiveField('hr_specialist'), true);
  assert.equal(canRevealSensitiveField('auditor'), true);

  // Non-whitelisted roles MUST see masked fields
  assert.equal(canRevealSensitiveField('viewer'), false);
  assert.equal(canRevealSensitiveField('bidder'), false);
  assert.equal(canRevealSensitiveField('bidding_manager'), false);

  // ID card masking test
  const idCard = '110101199003072345';
  const maskedId = maskSensitiveValue(idCard, 'id_card');
  assert.equal(maskedId, '110101********2345');
  assert.equal(maskedId.includes('19900307'), false);

  // Phone masking test
  const phone = '13812345678';
  const maskedPhone = maskSensitiveValue(phone, 'phone');
  assert.equal(maskedPhone, '138****5678');
  assert.equal(maskedPhone.includes('1234'), false);

  // Edge cases
  assert.equal(maskSensitiveValue('', 'id_card'), '');
  assert.equal(maskSensitiveValue('123', 'id_card'), '1*3');
});

test('verifyAttachmentSecurity verifies SHA256 integrity and download audit trail', () => {
  const secureAttachment = {
    id: 'att-01',
    name: '营业执照正本扫描件.pdf',
    size_bytes: 1048576,
    sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    storage_url: '/attachments/att-01.pdf',
    uploaded_at: '2026-01-01T00:00:00Z',
  };

  // Valid hash
  const validCheck = verifyAttachmentSecurity(
    secureAttachment,
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  );
  assert.equal(validCheck.verified, true);
  assert.equal(validCheck.tampered, false);
  assert.match(validCheck.audit_message, /指纹比对一致/);

  // Tampered hash mismatch
  const tamperedCheck = verifyAttachmentSecurity(
    secureAttachment,
    'a1b2c3d4e5f60000000000000000000000000000000000000000000000000000'
  );
  assert.equal(tamperedCheck.verified, false);
  assert.equal(tamperedCheck.tampered, true);
  assert.match(tamperedCheck.audit_message, /警告/);

  // Missing hash in metadata
  const missingHashAttachment = {
    id: 'att-02',
    name: '未加签附件.docx',
    size_bytes: 2048,
  };
  const missingCheck = verifyAttachmentSecurity(missingHashAttachment);
  assert.equal(missingCheck.verified, false);
  assert.match(missingCheck.audit_message, /缺少 SHA256/);
});
