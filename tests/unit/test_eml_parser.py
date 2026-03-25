from pathlib import Path
from datetime import datetime

from backend.ingestion.parsers.eml_parser import EmlParser


def test_eml_parser_extracts_thread_and_metadata(tmp_path: Path) -> None:
    eml_content = """From: Alice <alice@example.com>
To: Bob <bob@example.com>
Cc: Carol <carol@example.com>
Subject: Thread Example
Date: Sat, 22 Mar 2026 10:00:00 +0000
Message-ID: <m1@example.com>
In-Reply-To: <m0@example.com>
References: <m0@example.com> <m00@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

Hello Bob,
Current reply body.

-----Original Message-----
From: Bob <bob@example.com>
To: Alice <alice@example.com>
Subject: Re: Thread Example
Date: Fri, 21 Mar 2026 09:00:00 +0000

Previous reply body.
"""

    file_path = tmp_path / "thread.eml"
    file_path.write_text(eml_content, encoding="utf-8")

    parsed = EmlParser().parse(file_path)

    assert parsed.metadata.document_category == "email"
    assert parsed.metadata.subject == "Thread Example"
    assert parsed.metadata.reply_count == 2
    assert parsed.metadata.participants == [
        "alice@example.com",
        "bob@example.com",
        "carol@example.com",
    ]

    assert parsed.structure is not None
    assert len(parsed.structure.replies) == 2
    assert parsed.structure.replies[0].message_id == "<m1@example.com>"
    assert parsed.structure.replies[0].in_reply_to == "<m0@example.com>"
    assert parsed.structure.replies[0].references == ["<m0@example.com>", "<m00@example.com>"]
    assert parsed.structure.replies[0].cc == ["carol@example.com"]
    assert isinstance(parsed.structure.replies[0].date, datetime)
    assert parsed.structure.replies[0].body.startswith("Hello Bob")
    assert "Previous reply body." in parsed.structure.replies[1].body


def test_eml_parser_extracts_attachment_names(tmp_path: Path) -> None:
    eml_content = """From: Alice <alice@example.com>
To: Bob <bob@example.com>
Subject: Attachment Example
Date: Sat, 22 Mar 2026 10:00:00 +0000
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=abc

--abc
Content-Type: text/plain; charset=utf-8

Please review attachment.

--abc
Content-Type: application/pdf
Content-Disposition: attachment; filename="evidence.pdf"

%PDF-1.4
--abc--
"""

    file_path = tmp_path / "attachment.eml"
    file_path.write_text(eml_content, encoding="utf-8")

    parsed = EmlParser().parse(file_path)

    assert parsed.metadata.attachment_names == ["evidence.pdf"]

