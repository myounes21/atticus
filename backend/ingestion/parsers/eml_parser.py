from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses
from html.parser import HTMLParser
from pathlib import Path
import re

from backend.ingestion.parsers.constants import (
    BODY_PREFERENCES_HTML,
    BODY_PREFERENCES_PLAIN,
    EMBEDDED_HEADER_KEYS,
    EMAIL_ADDRESS_HEADERS,
    EMAIL_SPLIT_MARKERS,
    HTML_BLOCK_TAGS_END_BREAK,
    HTML_BLOCK_TAGS_WITH_BREAK,
    TEXT_PLAIN_MIME,
)
from backend.ingestion.parsers.base import BaseParser
from backend.schemas.parsed_document import (
    EmailReply,
    EmailStructure,
    Metadata,
    ParsedDocument,
)


class EmlParser(BaseParser):
    _THREAD_MARKERS = EMAIL_SPLIT_MARKERS

    class _HtmlToTextParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.parts: list[str] = []
            self.current_link: str | None = None

        def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
            if tag == "a":
                href = dict(attrs).get("href")
                self.current_link = href.strip() if isinstance(href, str) else None
            elif tag in HTML_BLOCK_TAGS_WITH_BREAK:
                self.parts.append("\n")

        def handle_endtag(self, tag: str) -> None:  # type: ignore[override]
            if tag == "a" and self.current_link:
                self.parts.append(f" ({self.current_link})")
                self.current_link = None
            elif tag in HTML_BLOCK_TAGS_END_BREAK:
                self.parts.append("\n")

        def handle_data(self, data: str) -> None:  # type: ignore[override]
            if data:
                self.parts.append(data)

        def render(self) -> str:
            text = "".join(self.parts)
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            return text.strip()

    def _html_to_text(self, html: str) -> str:
        parser = self._HtmlToTextParser()
        parser.feed(html)
        parser.close()
        return parser.render()

    def _extract_body(self, message: EmailMessage) -> str:
        preferred = message.get_body(preferencelist=BODY_PREFERENCES_PLAIN)
        if preferred is not None:
            return (preferred.get_content() or "").strip()

        # Fallback: collect text/plain parts
        parts: list[str] = []
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == TEXT_PLAIN_MIME:
                    content = part.get_content()
                    if content:
                        parts.append(content.strip())
        else:
            content = message.get_content()
            if content:
                parts.append(str(content).strip())

        body = "\n\n".join(p for p in parts if p).strip()
        if body:
            return body

        # Last fallback: parse html while preserving link targets
        html_part = message.get_body(preferencelist=BODY_PREFERENCES_HTML)
        if html_part is not None:
            html = html_part.get_content() or ""
            return self._html_to_text(html)

        return ""

    def _extract_participants(self, message: EmailMessage) -> set[str]:
        headers = []
        for header_name in EMAIL_ADDRESS_HEADERS:
            values = message.get_all(header_name, [])
            headers.extend(values)

        addresses = getaddresses(headers)
        participants = {addr.lower() for _, addr in addresses if addr}
        return participants

    def _extract_header_addresses(self, message: EmailMessage, header_name: str) -> list[str]:
        values = message.get_all(header_name, [])
        return [addr for _, addr in getaddresses(values) if addr]

    def _extract_addresses_from_header_value(self, value: str) -> list[str]:
        if not value:
            return []
        return [addr for _, addr in getaddresses([value]) if addr]

    def _extract_attachments(self, message: EmailMessage) -> list[str]:
        names: list[str] = []
        for attachment in message.iter_attachments():
            filename = attachment.get_filename()
            if filename:
                names.append(filename)
        return names

    def _split_thread_blocks(self, body: str) -> list[str]:
        if not body.strip():
            return [""]

        marker_pattern = "|".join(self._THREAD_MARKERS)
        chunks = re.split(marker_pattern, body, flags=re.IGNORECASE | re.MULTILINE)
        blocks = [chunk.strip() for chunk in chunks if chunk and chunk.strip()]
        return blocks or [body.strip()]

    def _extract_embedded_headers(self, block: str) -> tuple[dict[str, str], str]:
        lines = block.splitlines()
        headers = {key: "" for key in EMBEDDED_HEADER_KEYS}

        idx = 0
        while idx < len(lines):
            line = lines[idx].strip()
            if not line:
                idx += 1
                break

            lower = line.lower()
            matched = False
            for key in headers:
                prefix = f"{key}:"
                if lower.startswith(prefix):
                    headers[key] = line[len(prefix):].strip()
                    matched = True
                    break

            if not matched:
                break

            idx += 1

        remaining_body = "\n".join(lines[idx:]).strip()
        return headers, remaining_body or block.strip()

    def _build_replies(
        self,
        from_value: str,
        to_value: str,
        subject: str | None,
        date: str | None,
        cc_list: list[str] | None,
        bcc_list: list[str] | None,
        message_id: str | None,
        in_reply_to: str | None,
        references: list[str] | None,
        body: str,
    ) -> list[EmailReply]:
        blocks = self._split_thread_blocks(body)
        replies: list[EmailReply] = []

        for index, block in enumerate(blocks):
            if index == 0:
                replies.append(
                    EmailReply(
                        from_=from_value,
                        to=to_value,
                        subject=subject,
                        date=date,
                        body=block,
                        cc=cc_list,
                        bcc=bcc_list,
                        message_id=message_id,
                        in_reply_to=in_reply_to,
                        references=references,
                    )
                )
                continue

            headers, embedded_body = self._extract_embedded_headers(block)
            replies.append(
                EmailReply(
                    from_=headers["from"] or from_value,
                    to=headers["to"] or to_value,
                    subject=(headers["subject"] or subject) or None,
                    date=(headers["date"] or date) or None,
                    body=embedded_body,
                    cc=self._extract_addresses_from_header_value(headers["cc"]) or cc_list,
                    bcc=self._extract_addresses_from_header_value(headers["bcc"]) or bcc_list,
                    message_id=headers["message-id"] or None,
                    in_reply_to=headers["in-reply-to"] or None,
                    references=[r for r in headers["references"].split() if r] or None,
                )
            )

        return replies

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            with open(file_path, "rb") as f:
                message = BytesParser(policy=policy.default).parse(f)

            from_value = (message.get("from") or "").strip()
            to_value = (message.get("to") or "").strip()
            subject = (message.get("subject") or "").strip() or None
            date = (message.get("date") or "").strip() or None
            body = self._extract_body(message)
            participants = self._extract_participants(message)
            cc_list = self._extract_header_addresses(message, "cc")
            bcc_list = self._extract_header_addresses(message, "bcc")
            references_raw = (message.get("references") or "").strip()
            references = [ref for ref in references_raw.split() if ref] or None
            attachment_names = self._extract_attachments(message)
            message_id = (message.get("message-id") or "").strip() or None
            in_reply_to = (message.get("in-reply-to") or "").strip() or None
            replies = self._build_replies(
                from_value,
                to_value,
                subject,
                date,
                cc_list or None,
                bcc_list or None,
                message_id,
                in_reply_to,
                references,
                body,
            )

            return ParsedDocument(
                text=body,
                metadata=Metadata(
                    document_name=file_path.name,
                    file_type="eml",
                    subject=subject or None,
                    participants=participants or None,
                    attachment_names=attachment_names or None,
                    reply_count=len(replies),
                ),
                structure=EmailStructure(replies=replies),
            )
        except (FileNotFoundError, PermissionError) as e:
            raise ValueError(f"Failed to read file {file_path}: {e}") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode email content from {file_path}: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse email {file_path}: {e}") from e
