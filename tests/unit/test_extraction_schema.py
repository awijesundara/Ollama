import pytest
from pydantic import ValidationError

from src.memory.models import ExtractionResult


def test_extraction_schema_rejects_out_of_range_values() -> None:
    with pytest.raises(ValidationError):
        ExtractionResult.model_validate(
            {
                "candidates": [
                    {
                        "save": True,
                        "scope": "global",
                        "category": "preference",
                        "memory": "The user likes concise answers",
                        "importance": 11,
                        "confidence": 2,
                        "reason": "explicit",
                    }
                ]
            }
        )
