"""Robust LLM output parser — extracts structured data from raw LLM responses.

Handles: markdown fences, HTML, partial JSON, embedded JSON in text.
Replaces all manual _parse_llm_output methods across agents.
"""

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError
import structlog

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


def parse_llm_output(raw: str, model_class: type[T], fallback: T | None = None) -> T:
    """Parse raw LLM output into a Pydantic model.

    Tries multiple strategies:
    1. Direct JSON parse
    2. Extract JSON from markdown fences
    3. Find JSON object in mixed text
    4. Fuzzy key extraction as last resort

    Returns validated Pydantic model or fallback if all parsing fails.
    """
    cleaned = _clean_raw(raw)

    # Strategy 1: Direct parse
    result = _try_parse(cleaned, model_class)
    if result:
        return result

    # Strategy 2: Extract from markdown fences
    fenced = _extract_from_fences(raw)
    if fenced:
        result = _try_parse(fenced, model_class)
        if result:
            return result

    # Strategy 3: Find JSON object in text
    json_str = _find_json_object(cleaned)
    if json_str:
        result = _try_parse(json_str, model_class)
        if result:
            return result

    # Strategy 4: Try to build from key extraction
    result = _fuzzy_extract(cleaned, model_class)
    if result:
        return result

    # All strategies failed
    logger.warning(
        "llm_output_parse_failed",
        model=model_class.__name__,
        raw_length=len(raw),
        raw_preview=raw[:200],
    )

    if fallback:
        return fallback

    # Return model with defaults
    try:
        return model_class()
    except ValidationError:
        raise ValueError(f"Cannot parse LLM output into {model_class.__name__}: {raw[:200]}")


def _clean_raw(raw: str) -> str:
    """Clean common LLM output artifacts."""
    cleaned = raw.strip()
    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    # Remove markdown bold/italic
    cleaned = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", cleaned)
    return cleaned


def _extract_from_fences(raw: str) -> str | None:
    """Extract content from ```json ... ``` blocks."""
    matches = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw)
    for match in matches:
        stripped = match.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            return stripped
    return None


def _find_json_object(text: str) -> str | None:
    """Find the largest valid JSON object in text."""
    # Find all potential JSON starts
    starts = [i for i, c in enumerate(text) if c == "{"]
    for start in starts:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        break
    return None


def _try_parse(text: str, model_class: type[T]) -> T | None:
    """Try to parse text as JSON and validate with Pydantic."""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return model_class(**data)
    except (json.JSONDecodeError, ValidationError, TypeError):
        pass
    return None


def _fuzzy_extract(text: str, model_class: type[T]) -> T | None:
    """Last resort: try to extract values by field name patterns."""
    fields = model_class.model_fields
    data = {}

    for field_name, field_info in fields.items():
        # Try to find "field_name": "value" or field_name: value patterns
        pattern = rf'"{field_name}"\s*:\s*"([^"]*)"'
        match = re.search(pattern, text)
        if match:
            data[field_name] = match.group(1)
            continue

        # Try unquoted value
        pattern = r'"' + field_name + r'"\s*:\s*([^,}]+)'
        match = re.search(pattern, text)
        if match:
            val = match.group(1).strip().strip('"')
            data[field_name] = val

    if data:
        try:
            return model_class(**data)
        except (ValidationError, TypeError):
            pass

    return None
