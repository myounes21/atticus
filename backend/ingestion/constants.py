# Parser constants
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


# Detector constants
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


# Other shared ingestion constants
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

CONTRACT_SECTION_PATTERNS = ()

DEFAULT_DEPOSITION_DOCUMENT_NAME = "unknown.txt"

