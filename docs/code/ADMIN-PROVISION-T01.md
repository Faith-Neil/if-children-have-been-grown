为什么有这个文件：解释 ADMIN-PROVISION-T01 代码入口。

它解决什么问题：接手者能找到开通公司与改密字段落点。

# ADMIN-PROVISION-T01 代码说明

- `icg/domain/company_registry.py`：`create_company` 事务写 companies、company_settings.company_name、首个 `company_admin` Account。
- `icg/api/companies.py`：`POST /api/v1/companies` → 201 `CreateCompanyResponse`。
- `icg/domain/user_management.py`：`CreateUserRequest.must_change_password`（缺省 true）。
- `icg/domain/errors.py`：`COMPANY_NAME_DUPLICATED` → 409。
- 测试：`tests/backend/test_company_provisioning.py`。
