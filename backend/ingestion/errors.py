from dataclasses import dataclass
from enum import Enum


class IngestionStage(str, Enum):
    FILE_TYPE = "file_type"
    PARSE = "parse"
    DETECT = "detect"
    CHUNK = "chunk"
    ENRICH = "enrich"


@dataclass(slots=True)
class IngestionStageError(Exception):
    stage: IngestionStage
    message: str
    cause: Exception

    def __str__(self) -> str:
        return f"{self.message}: {self.cause}"

