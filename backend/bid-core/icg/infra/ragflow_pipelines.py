# 为什么有这个文件：按招投标业务定义 ICG 自有的 RAGFlow 摄入流程（Ingestion Pipeline），并生成 RAGFlow 1.0 画布 DSL。
# 它解决什么问题：通用切块把投标文件的章节、资质证书、表格切碎，检索时丢掉“这段属于哪一章、哪张证书”；
# 招标要求的说法（“投标人须具备…”）与资料原文（“XX 证书编号…”）字面不重合，召回差。
# 这里为四类知识各定一条流程：按投标文件标题层级切块并保留章节路径、证书整页成块并抽取证书字段、
# 用 LLM 为每块生成“招标文件可能怎么问”的问题和关键词来弥合语义差。
#
# DSL 结构依据实测 RAGFlow v1.0.0-rc2 的内置模板（Title Chunker / Advanced Ingestion Pipeline）：
# components 是后端执行用的参数；graph.nodes[].data.form 是画布界面用的同一套参数（部分字段形状不同）。
# 两边必须同时写对，否则有人在 RAGFlow 界面打开并保存流程时，会用界面表单覆盖后端参数。

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

PIPELINE_VERSION = 1
TITLE_PREFIX = "icg"

# ---------- 解析器（Parser）各文件类型设置：与 RAGFlow 内置模板一致，PDF 用 DeepDOC（版面/表格/扫描件） ----------

_PARSER_SETUPS: dict[str, dict[str, Any]] = {
    "pdf": {"flatten_media_to_text": False, "output_format": "json", "parse_method": "DeepDOC",
            "preprocess": "main_content", "suffix": ["pdf"], "vlm": {}},
    "docx": {"flatten_media_to_text": False, "output_format": "json", "preprocess": "main_content",
             "suffix": ["docx"], "vlm": {}},
    "doc": {"output_format": "json", "preprocess": "main_content", "suffix": ["doc"]},
    "spreadsheet": {"flatten_media_to_text": False, "output_format": "html", "parse_method": "DeepDOC",
                    "preprocess": "main_content", "suffix": ["xls", "xlsx", "csv"], "vlm": {}},
    "image": {"output_format": "json", "parse_method": "ocr", "preprocess": "main_content",
              "suffix": ["jpg", "jpeg", "png", "gif"], "system_prompt": ""},
    "markdown": {"flatten_media_to_text": False, "output_format": "json", "preprocess": "main_content",
                 "suffix": ["md", "markdown", "mdx"], "vlm": {}},
    "text&code": {"output_format": "json", "preprocess": "main_content", "suffix": ["txt"]},
    "html": {"output_format": "json", "preprocess": "main_content", "suffix": ["htm", "html"]},
    "slides": {"output_format": "json", "parse_method": "DeepDOC", "preprocess": "main_content",
               "suffix": ["pptx", "ppt"]},
}
_PARSER_OUTPUTS = {"html": {"type": "string", "value": ""}, "json": {"type": "Array<object>", "value": []},
                   "markdown": {"type": "string", "value": ""}, "text": {"type": "string", "value": ""}}
_CHUNK_OUTPUTS = {"chunks": {"type": "Array<Object>", "value": []}}

# ---------- 招投标文件标题层级 ----------
# 一组 = 一种编号体系，组内按层级从高到低。RAGFlow 会挑与文档最匹配的一组。
BID_HEADING_GROUPS: list[list[str]] = [
    # Markdown（本系统生成的结构化资料）
    [r"^#[^#]", r"^##[^#]", r"^###[^#]", r"^####[^#]"],
    # 招标/投标文件最常见：第X部分/第X章 → 一、 → （一） → 1. → (1)
    [r"^第[零一二三四五六七八九十百0-9]+(部分|篇|卷|册)", r"^第[零一二三四五六七八九十百0-9]+章",
     r"^[零一二三四五六七八九十百]+[、．.]", r"^[（(][零一二三四五六七八九十百]+[)）]",
     r"^[0-9]{1,2}[．.、]([^0-9]|$)", r"^[（(][0-9]{1,2}[)）]"],
    # 数字层级：1 → 1.1 → 1.1.1（技术方案常用）
    [r"^第[零一二三四五六七八九十百0-9]+章", r"^[0-9]{1,2}[．.、 ]([^0-9]|$)",
     r"^[0-9]{1,2}\.[0-9]{1,2}($|[^0-9a-zA-Z/%~.-])", r"^[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}"],
    # 法规条文体（采购需求中的条款）
    [r"^第[零一二三四五六七八九十百0-9]+章", r"^第[零一二三四五六七八九十百0-9]+节",
     r"^第[零一二三四五六七八九十百0-9]+条"],
]

# ---------- 抽取（Extractor）提示词：中文、面向招投标 ----------

QUESTIONS_PROMPT = (
    "角色\n你是投标文件编写专家。\n\n任务\n阅读给定的投标资料片段，写出 {{ topn }} 条“招标文件中可能出现、且本片段可以作为响应依据”的要求或评分项表述。\n\n"
    "要求\n- 使用招标文件的常见说法，例如“投标人须具备……”“供应商应提供……证明材料”“拟派项目负责人须……”“提供……方案的得 X 分”。\n"
    "- 只能依据片段内容，不得编造片段中没有的资质、数字或结论。\n- 各条含义不重复，覆盖片段的主要内容。\n- 每行一条，只输出这些表述。"
)
KEYWORDS_PROMPT = (
    "角色\n你是投标资料标引员。\n\n任务\n从给定片段中提取 {{ topn }} 个最重要的检索关键词。\n\n"
    "要求\n- 优先提取：证书/资质名称与等级、标准编号（如 ISO/IEC 27001、GB/T 19001）、人员职称与证书、项目名称、"
    "采购人类型/行业、技术名词、服务指标（如 7×24、响应时限）。\n- 保持原文用词，不翻译、不改写。\n- 用英文逗号分隔，只输出关键词。"
)
SUMMARY_PROMPT = (
    "你是严谨的投标资料摘要员。用不超过 120 字概括片段内容，只依据原文，不增加任何原文没有的事实或结论，使用原文语言。"
)


@dataclass(frozen=True)
class MetadataField:
    key: str
    description: str
    type: str = "string"

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "description": self.description, "type": self.type}


@dataclass(frozen=True)
class PipelineProfile:
    """一条 ICG 摄入流程的业务定义。"""
    key: str
    title: str
    description: str
    knowledge_kind: str
    file_formats: tuple[str, ...]
    chunker: str  # "title" | "token"
    heading_groups: list[list[str]] = field(default_factory=list)
    hierarchy: int = 3
    include_heading_content: bool = True
    chunk_token_size: int = 512
    overlapped_percent: int = 0
    delimiters: tuple[str, ...] = ("\n", "。", "；", "！", "？")
    questions_top_n: int = 0
    keywords_top_n: int = 0
    summary: bool = False
    metadata_fields: tuple[MetadataField, ...] = ()
    filename_embd_weight: float = 0.1


PROFILES: dict[str, PipelineProfile] = {
    "structured": PipelineProfile(
        key="structured",
        title="结构化资料与方案片段",
        description="本系统生成的资料/片段 Markdown：按 # / ## 标题切块并把标题带进每块，LLM 生成招标式问法与关键词。",
        knowledge_kind="library",
        file_formats=("markdown", "text&code"),
        chunker="title",
        heading_groups=[BID_HEADING_GROUPS[0]],
        hierarchy=2,
        questions_top_n=3,
        keywords_top_n=5,
    ),
    "history_bid": PipelineProfile(
        key="history_bid",
        title="历史投标文件",
        description="历史投标/响应文件原件（docx/pdf/xlsx）：按投标文件章节层级切块并保留章节路径；表格单独成块；"
                    "LLM 生成关键词与招标式问法，并抽取项目名称、采购人、行业、投标日期等文档元数据。仅供参考，不作证据。",
        knowledge_kind="history",
        file_formats=("pdf", "docx", "doc", "spreadsheet", "markdown", "text&code", "slides"),
        chunker="title",
        heading_groups=BID_HEADING_GROUPS[1:],
        hierarchy=3,
        questions_top_n=2,
        keywords_top_n=5,
        metadata_fields=(
            MetadataField("project_name", "投标项目名称（原文）"),
            MetadataField("purchaser", "采购人或招标人名称"),
            MetadataField("industry", "采购人所属行业，例如银行、政务、医疗、能源、教育"),
            MetadataField("bid_date", "投标或响应文件日期，格式 YYYY-MM-DD，原文没有则留空"),
            MetadataField("project_type", "项目类型，例如软件采购、运维服务、系统集成、咨询"),
        ),
    ),
    "certificate": PipelineProfile(
        key="certificate",
        title="资质证书与证明附件",
        description="资质证书、人员证书、合同/业绩证明的扫描件或照片：整页成块（不拆证书），OCR，"
                    "抽取证书名称、编号、发证机构、持有人、有效期，供资料管理员核对后录入。",
        knowledge_kind="certificate",
        file_formats=("pdf", "image", "docx"),
        chunker="token",
        chunk_token_size=1024,
        delimiters=("\n\n",),
        keywords_top_n=5,
        metadata_fields=(
            MetadataField("cert_name", "证书或证明文件名称"),
            MetadataField("cert_no", "证书编号或合同编号，原文没有则留空"),
            MetadataField("issuer", "发证机构或签约甲方"),
            MetadataField("holder", "证书持有单位或持证人"),
            MetadataField("valid_to", "有效期截止日期，格式 YYYY-MM-DD；长期有效写 long_term；原文没有则留空"),
            MetadataField("scope", "认证范围、资质等级或业务范围"),
        ),
    ),
    "tender": PipelineProfile(
        key="tender",
        title="招标文件（按项目）",
        description="招标文件原件：DeepDOC 版面解析（含扫描件、表格），按章节层级切块并保留章节路径与页码位置；"
                    "不做 LLM 改写，供条款抽取与编辑台“查招标原文”。",
        knowledge_kind="tender",
        file_formats=("pdf", "docx", "doc", "spreadsheet"),
        chunker="title",
        heading_groups=BID_HEADING_GROUPS[1:],
        hierarchy=4,
    ),
}


def company_tag(company_id: str) -> str:
    """公司在流程标题里的短标识（RAGFlow 1.0 解析任务表的 pipeline_title 列很短，实测超长即入队失败）。"""
    return hashlib.sha1(company_id.encode("utf-8")).hexdigest()[:8]


def pipeline_title(company_id: str, profile: PipelineProfile, version: int = PIPELINE_VERSION) -> str:
    # 形如 icg:history_bid:v1:1a2b3c4d，最长不超过 32 字符；公司全名记在流程描述与本系统索引里。
    return f"{TITLE_PREFIX}:{profile.key}:v{version}:{company_tag(company_id)}"


def parse_pipeline_title(title: str) -> tuple[str, str, int] | None:
    """返回 (公司短标识, 流程键, 版本)。"""
    parts = (title or "").split(":")
    if len(parts) != 4 or parts[0] != TITLE_PREFIX or not parts[2].startswith("v"):
        return None
    try:
        return parts[3], parts[1], int(parts[2][1:])
    except ValueError:
        return None


@dataclass(frozen=True)
class PipelineOptions:
    """公司级可调项（存在知识库设置里）。None 表示用流程默认值。"""
    llm_id: str = ""
    chunk_token_size: int | None = None
    questions_top_n: int | None = None
    keywords_top_n: int | None = None
    extra_heading_patterns: tuple[str, ...] = ()


def _node_id(kind: str, profile: PipelineProfile) -> str:
    # 组件 id 形如 “类型:名字”，名字稳定可复现（按流程键派生），便于升级时对比与在 parser_config 里引用。
    suffix = hashlib.sha1(f"{profile.key}:{kind}".encode()).hexdigest()[:8]
    return f"{kind}:Icg{profile.key.title().replace('_', '')}{suffix}"


def build_dsl(profile: PipelineProfile, options: PipelineOptions | None = None) -> dict[str, Any]:
    """生成完整画布 DSL：File → Parser → 切块器 → [Extractor] → Tokenizer（索引）。"""
    opts = options or PipelineOptions()
    parser_id = _node_id("Parser", profile)
    chunker_kind = "TitleChunker" if profile.chunker == "title" else "TokenChunker"
    chunker_id = _node_id(chunker_kind, profile)
    questions = profile.questions_top_n if opts.questions_top_n is None else max(0, opts.questions_top_n)
    keywords = profile.keywords_top_n if opts.keywords_top_n is None else max(0, opts.keywords_top_n)
    use_extractor = bool(questions or keywords or profile.summary or profile.metadata_fields)
    extractor_id = _node_id("Extractor", profile) if use_extractor else None
    tokenizer_id = _node_id("Tokenizer", profile)

    # --- Parser ---
    parser_params: dict[str, Any] = {fmt: copy.deepcopy(_PARSER_SETUPS[fmt]) for fmt in profile.file_formats}
    parser_params["outputs"] = copy.deepcopy(_PARSER_OUTPUTS)
    parser_params["enable_vision_enhancement"] = False
    parser_form = {"outputs": copy.deepcopy(_PARSER_OUTPUTS), "setups": [
        {"fileFormat": fmt, **{k: copy.deepcopy(v) for k, v in _PARSER_SETUPS[fmt].items() if k != "suffix"}}
        for fmt in profile.file_formats]}

    # --- Chunker ---
    if chunker_kind == "TitleChunker":
        groups = [list(g) for g in profile.heading_groups]
        if opts.extra_heading_patterns:
            groups.insert(0, list(opts.extra_heading_patterns))
        chunker_params = {"hierarchy": profile.hierarchy, "include_heading_content": profile.include_heading_content,
                          "levels": groups, "method": "hierarchy", "outputs": copy.deepcopy(_CHUNK_OUTPUTS)}
        chunker_form = {"hierarchy": str(profile.hierarchy), "include_heading_content": profile.include_heading_content,
                        "method": "hierarchy", "outputs": copy.deepcopy(_CHUNK_OUTPUTS),
                        "rules": [{"levels": [{"expression": e} for e in g]} for g in groups]}
        chunker_label, chunker_name = "TitleChunker", "Title Chunker_0"
    else:
        size = opts.chunk_token_size or profile.chunk_token_size
        chunker_params = {"children_delimiters": [], "chunk_token_size": size, "delimiter_mode": "delimiter",
                          "delimiters": list(profile.delimiters), "image_context_size": 0,
                          "outputs": copy.deepcopy(_CHUNK_OUTPUTS), "overlapped_percent": profile.overlapped_percent,
                          "table_context_size": 0}
        chunker_form = copy.deepcopy(chunker_params)
        chunker_label, chunker_name = "TokenChunker", "Token Chunker_0"

    # --- Extractor ---
    extractor_params: dict[str, Any] | None = None
    if use_extractor:
        extractor_params = {
            "frequencyPenaltyEnabled": True, "frequency_penalty": 0.7, "llm_id": opts.llm_id,
            "maxTokensEnabled": False, "max_tokens": 512,
            "keywords": {"system_prompt": KEYWORDS_PROMPT, "top_n": keywords},
            "questions": {"system_prompt": QUESTIONS_PROMPT, "top_n": questions},
            "summary": {"enabled": profile.summary, "system_prompt": SUMMARY_PROMPT},
            "metadata": {"built_in_metadata": [], "enabled": bool(profile.metadata_fields),
                         "metadata": [m.to_dict() for m in profile.metadata_fields]},
            "tags": {"tag_file_id": "", "top_n": 0},
            "outputs": copy.deepcopy(_CHUNK_OUTPUTS),
            "presencePenaltyEnabled": True, "presence_penalty": 0.4,
            # 抽取与改写都要贴原文：低温度、低 top_p。
            "temperature": 0.1, "temperatureEnabled": True, "topPEnabled": True, "top_p": 0.3,
        }

    tokenizer_params = {"fields": "text", "filename_embd_weight": profile.filename_embd_weight, "outputs": {},
                        "search_method": ["embedding", "full_text"]}

    chain = ["File", parser_id, chunker_id] + ([extractor_id] if extractor_id else []) + [tokenizer_id]
    objs: dict[str, tuple[str, dict]] = {
        "File": ("File", {}),
        parser_id: ("Parser", parser_params),
        chunker_id: (chunker_label, chunker_params),
        tokenizer_id: ("Tokenizer", tokenizer_params),
    }
    if extractor_id:
        objs[extractor_id] = ("Extractor", extractor_params)
    components = {}
    for index, node in enumerate(chain):
        name, params = objs[node]
        components[node] = {"downstream": chain[index + 1:index + 2], "upstream": chain[index - 1:index] if index else [],
                            "obj": {"component_name": name, "params": params}}

    forms = {parser_id: ("parserNode", "Parser", "Parser_0", parser_form),
             chunker_id: ("chunkerNode", chunker_label, chunker_name, chunker_form),
             tokenizer_id: ("tokenizerNode", "Tokenizer", "Indexer_0", copy.deepcopy(tokenizer_params))}
    if extractor_id:
        forms[extractor_id] = ("contextNode", "Extractor", "Auto Extract", copy.deepcopy(extractor_params))
    nodes = [{"data": {"label": "File", "name": "File"}, "id": "File", "position": {"x": 50, "y": 200},
              "sourcePosition": "left", "targetPosition": "right", "type": "beginNode"}]
    for index, node in enumerate(chain[1:], start=1):
        node_type, label, name, form = forms[node]
        nodes.append({"data": {"form": form, "label": label, "name": name}, "id": node,
                      "position": {"x": 50 + 300 * index, "y": 200}, "sourcePosition": "right",
                      "targetPosition": "left", "type": node_type})
    edges = [{"id": f"xy-edge__{a}start-{b}end", "source": a, "sourceHandle": "start", "target": b,
              "targetHandle": "end"} for a, b in zip(chain, chain[1:])]
    return {"components": components, "globals": {"sys.history": []}, "graph": {"edges": edges, "nodes": nodes},
            "history": [], "messages": [], "path": [], "retrieval": [], "variables": []}


def dsl_fingerprint(dsl: dict[str, Any]) -> str:
    """只按后端执行参数计算指纹，用于判断已部署流程是否被人改过或需要升级。"""
    components = {k: v["obj"] for k, v in (dsl.get("components") or {}).items()}
    return hashlib.sha256(json.dumps(components, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
