import re
from typing import Literal, cast
from backend.ingestion.chunkers.base import BaseChunker
from backend.ingestion.chunkers.constants import ENCODER, MAX_TOKENS
from backend.ingestion.constants import DEFAULT_DEPOSITION_DOCUMENT_NAME
from backend.schemas.parsed_document import (
    ParsedDocument,
    DepositionStructure,
    DepositionTurn,
)
from backend.schemas.chunkers_schema import Chunk
from backend.schemas.parsed_document import DOCUMENT_CATEGORY


class DepositionChunker(BaseChunker):

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []

        file_type: Literal["pdf", "docx", "eml", "txt"]
        if document.metadata.file_type is None:
            file_type = "txt"
        else:
            file_type = document.metadata.file_type

        document_type: DOCUMENT_CATEGORY
        if document.metadata.document_category is None:
            document_type = "deposition"
        else:
            document_type = document.metadata.document_category

        document_name = document.metadata.document_name or DEFAULT_DEPOSITION_DOCUMENT_NAME


        if isinstance(document.structure, DepositionStructure):
            turns = document.structure.turns
        else:
            turns = self._extract_turns(document.text)


        blocks = self._group_qa(turns)


        for block in blocks:
            sub_texts = self._split_block_preserving_qa(block)

            for sub_text in sub_texts:
                chunk = Chunk(
                    text=sub_text,
                    chunk_index=len(chunks),
                    file_type=cast(Literal["pdf", "docx", "eml", "txt"], file_type),
                    document_type=cast(DOCUMENT_CATEGORY, document_type),
                    document_name=document_name,
                )
                chunks.append(chunk)

        return chunks


    def _extract_turns(self, text: str) -> list[DepositionTurn]:
        lines = text.split("\n")
        turns: list[DepositionTurn] = []

        pattern = re.compile(r"^(Q[:.]|A[:.]|Mr\.|Ms\.|Dr\.)", re.IGNORECASE)

        current_speaker: Literal["Q", "A", "Lawyer", "Other"] | None = None
        buffer: list[str] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if pattern.match(line):
                if buffer:
                    speaker: Literal["Q", "A", "Lawyer", "Other"]
                    if current_speaker is None:
                        speaker = "Other"
                    else:
                        speaker = current_speaker
                    turns.append(
                        DepositionTurn(
                            speaker=speaker,
                            text=" ".join(buffer),
                        )
                    )
                    buffer = []

                if line.lower().startswith(("q:", "q.")):
                    current_speaker = "Q"
                    buffer.append(line[2:].strip())
                elif line.lower().startswith(("a:", "a.")):
                    current_speaker = "A"
                    buffer.append(line[2:].strip())
                else:
                    current_speaker = "Lawyer"
                    buffer.append(line)

            else:
                buffer.append(line)

        if buffer:
            speaker: Literal["Q", "A", "Lawyer", "Other"]
            if current_speaker is None:
                speaker = "Other"
            else:
                speaker = current_speaker
            turns.append(
                DepositionTurn(
                    speaker=speaker,
                    text=" ".join(buffer),
                )
            )

        return turns

    def _group_qa(self, turns: list[DepositionTurn]) -> list[list[DepositionTurn]]:
        blocks: list[list[DepositionTurn]] = []
        current: list[DepositionTurn] = []

        for turn in turns:
            speaker = turn.speaker

            if speaker == "Q":
                current.append(turn)

            elif speaker == "A":
                current.append(turn)
                blocks.append(current)
                current = []

            else:
                current.append(turn)

        if current:
            blocks.append(current)

        return blocks


    def _format_block(self, block: list[DepositionTurn]) -> str:
        return "\n".join(
            f"{turn.speaker}: {turn.text}" for turn in block
        )

    def _split_block_preserving_qa(self, block: list[DepositionTurn]) -> list[str]:
        block_text = self._format_block(block)
        if len(ENCODER.encode(block_text)) <= MAX_TOKENS:
            return [block_text]

        context_turns = [turn for turn in block if turn.speaker != "A"]
        answer_turns = [turn for turn in block if turn.speaker == "A"]

        # Without clear Q/A structure, fallback to plain token splitting.
        if not context_turns or not answer_turns:
            return self._split_if_needed(block_text)

        context_text = "\n".join(f"{turn.speaker}: {turn.text}" for turn in context_turns)
        answer_text = "\n".join(turn.text for turn in answer_turns)

        prefix = f"{context_text}\n"
        prefix_tokens = len(ENCODER.encode(prefix))
        if prefix_tokens >= MAX_TOKENS:
            return self._split_if_needed(block_text)

        answer_budget = MAX_TOKENS - prefix_tokens
        answer_parts = self._split_with_budget(answer_text, answer_budget)
        return [f"{prefix}A: {part}" for part in answer_parts]


    def _split_if_needed(self, text: str) -> list[str]:
        tokens = ENCODER.encode(text)

        if len(tokens) <= MAX_TOKENS:
            return [text]

        result = []
        for i in range(0, len(tokens), MAX_TOKENS):
            sub_tokens = tokens[i:i + MAX_TOKENS]
            result.append(ENCODER.decode(sub_tokens))

        return result

    def _split_with_budget(self, text: str, max_tokens: int) -> list[str]:
        if max_tokens <= 0:
            return [text]

        tokens = ENCODER.encode(text)
        if len(tokens) <= max_tokens:
            return [text]

        parts: list[str] = []
        for i in range(0, len(tokens), max_tokens):
            part_tokens = tokens[i:i + max_tokens]
            parts.append(ENCODER.decode(part_tokens))

        return parts

