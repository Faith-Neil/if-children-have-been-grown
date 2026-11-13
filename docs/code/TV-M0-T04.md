为什么有这个文件：说明 TV-M0-T04 的抽取写在哪里。

它解决什么问题：下次改条款抽取时，能看出技术分册和两册旧项目走的不是同一条规则。

# TV-M0-T04 代码说明

规则在 `backend/bid-core/icg/domain/technical_clause_extract.py`。`extract_technical_clauses` 读原文：编号行按条款树逐条收，带「应包含 / 服务方案 / 评分内容」且用顿号、逗号或分号分开的句子拆成要点。标题里出现定义、封面、目录、报价、客观分、资质、证书、社保、发票或照片的整节跳过。

同一件事用去掉编号和标点后的文字比较。短词包含在长词里，且短词不少于四个字，就并成一行。评分要点的原文用词留在行上，规格书来源追加到 `sources`。

`TenderOrchestratorMixin.parse` 只在 `technical_only` 项目调用它，不再走原来的全量条款抽取。抽完把 `technical_extract_empty` 放进工作区。一条都没有时，前端停在招标文件页，不跳到解析确认。
