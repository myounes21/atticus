from backend.ingestion.parsers.base import BaseParser
from backend.ingestion.parsers.docx_parser import DocxParser
from backend.ingestion.parsers.eml_parser import EmlParser
from backend.ingestion.parsers.pdf_parser import PDFParser
from backend.ingestion.parsers.txt_parser import TxtParser


_PARSER_BY_TYPE: dict[str, type[BaseParser]] = {
	"pdf": PDFParser,
	"docx": DocxParser,
	"eml": EmlParser,
	"txt": TxtParser,
}


def get_parser(file_type: str) -> BaseParser:
	parser_cls = _PARSER_BY_TYPE.get(file_type)
	if parser_cls is None:
		supported = ", ".join(sorted(_PARSER_BY_TYPE))
		raise ValueError(
			f"Unsupported parser file type '{file_type}'. Supported: {supported}"
		)

	return parser_cls()

