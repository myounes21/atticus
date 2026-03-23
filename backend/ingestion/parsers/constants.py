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

BODY_PREFERENCES_PLAIN = ("plain",)
BODY_PREFERENCES_HTML = ("html",)

TEXT_PLAIN_MIME = "text/plain"

HTML_BLOCK_TAGS_WITH_BREAK = {"p", "div", "br", "li", "tr"}
HTML_BLOCK_TAGS_END_BREAK = {"p", "div", "li", "tr"}
