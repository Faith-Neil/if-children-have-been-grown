from icg.domain.history_commitment import NOTICE_MESSAGE, commitment_notice


def test_notice_when_history_commitment_domain_is_not_in_materials():
    notice = commitment_notice([
        {"dataset_kind": "history", "content_role": "project_specific_commitment",
         "technical_domain": "data_security", "name": "旧标.docx"},
        {"dataset_kind": "materials", "content_role": "enterprise_fact",
         "technical_domain": "operation_maintenance", "name": "说明书.pdf"},
    ])
    assert notice["message"] == NOTICE_MESSAGE
    assert notice["filenames"] == ["旧标.docx"]


def test_no_notice_for_wording_only_or_covered_domain():
    assert commitment_notice([
        {"dataset_kind": "history", "content_role": "general_description",
         "technical_domain": "data_security", "name": "旧标.docx"},
    ]) is None
    assert commitment_notice([
        {"dataset_kind": "history", "content_role": "enterprise_fact",
         "technical_domain": "data_security", "name": "旧标.docx"},
        {"dataset_kind": "materials", "content_role": "enterprise_fact",
         "technical_domain": "data_security", "name": "说明书.pdf"},
    ]) is None
