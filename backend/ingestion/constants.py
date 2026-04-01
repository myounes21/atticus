import re
import tiktoken

EMAIL_SPLIT_MARKERS = (
    r"^\s*-{2,}\s*Original Message\s*-{2,}\s*$",
    r"^\s*On\s+.+?wrote:\s*$",
)

EMAIL_ADDRESS_HEADERS = ("from", "to", "cc", "bcc")

EMBEDDED_HEADER_KEYS = (
    "from",
    "to",
    "subject",
    "date",
    "cc",
    "bcc",
    "message-id",
    "in-reply-to",
    "references",
)

HTML_BLOCK_TAGS_WITH_BREAK = {"p", "div", "br", "li", "tr"}
HTML_BLOCK_TAGS_END_BREAK = {"p", "div", "li", "tr"}

VALID_CATEGORIES = {
    "email",
    "contract",
    "brief",
    "note",
    "invoice",
    "deposition",
    "court_filing",
    "settlement",
    "legal_notice",
    "evidence",
}

ALL_CATEGORIES = VALID_CATEGORIES | {"unknown"}

ALIASES = {
    "legal_brief": "brief",
    "court filing": "court_filing",
    "court-filing": "court_filing",
    "legal notice": "legal_notice",
    "legal-notice": "legal_notice",
}

DETECTION_PROMPT = """
You are a legal document classifier.

Classify the document into exactly one category from this list:
- email
- contract
- brief
- note
- invoice
- deposition
- court_filing
- settlement
- legal_notice
- evidence
- unknown

If the content is unclear, too short, or does not fit any category, return "unknown".

Return exactly one category name. Nothing else.

Document:
{content}
"""

TXT_NOTE_SHORTCUT_MAX_CHARS = 400

FILE_TYPE = ("pdf", "docx", "eml", "txt")

STRUCTURE_MAP = {
    "email": "conversational",
    "deposition": "conversational",
    "contract": "sectioned",
    "settlement": "sectioned",
    "legal_notice": "sectioned",
    "brief": "narrative",
    "court_filing": "narrative",
    "note": "unstructured",
    "invoice": "unstructured",
    "evidence": "unstructured",
}

DEFAULT_DEPOSITION_DOCUMENT_NAME = "unknown.txt"

MAX_TOKENS = 500
OVERLAP_TOKENS = 50
ENCODER = tiktoken.get_encoding("cl100k_base")

SECTION_HEADING_PATTERN = re.compile(
    r"(?:^|\n)"
    r"(?:"
    r"(?:#{1,4}\s+.+)"
    r"|(?:(?:ARTICLE|SECTION|CLAUSE)\s+[\dIVXivx]+[.:]\s*.+)"
    r"|(?:\d{1,3}[.)]\s+[A-Z].+)"
    r"|(?:[A-Z][A-Z ]{4,})"
    r")",
    re.MULTILINE,
)

ES_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "chunk_id":          {"type": "keyword"},
            "file_id":           {"type": "keyword"},
            "case_id":           {"type": "keyword"},
            "assigned_lawyers":  {"type": "keyword"},
            "is_latest":         {"type": "boolean"},
            "document_type":     {"type": "keyword"},
            "document_name":     {"type": "text"},
            "chunk_index":       {"type": "integer"},
            "text":              {"type": "text", "analyzer": "standard"},
        }
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
}

