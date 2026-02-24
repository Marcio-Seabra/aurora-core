import json
import re
import subprocess
import os

MIN_SEGMENT_LEN = 10
# Change AURORA_MEMORY_MODEL for splitter behavior; set USE_LLM_SPLITTER=False
# to force rule-based split (faster and less precise).
MODEL_NAME = os.getenv("AURORA_MEMORY_MODEL", "aurora_memory:latest")
USE_LLM_SPLITTER = True


def _split_by_markers(content: str) -> list[str]:
    parts = re.split(r"(?m)^\\s*>>>\\s*", content)
    segments = []
    for part in parts:
        part = part.strip()
        if part:
            segments.append(part)
    return segments


def _split_by_paragraphs(content: str) -> list[str]:
    parts = re.split(r"\\n\\s*\\n", content)
    segments = []
    for part in parts:
        part = part.strip()
        if part:
            segments.append(part)
    return segments


def _extract_json_array(text: str) -> list[dict] | None:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
        if isinstance(data, list):
            return data
    except Exception:
        return None
    return None


def _split_with_llm(content: str) -> list[dict] | None:
    prompt = (
        "Separe o texto em mensagens individuais e retorne apenas JSON valido.\n"
        "Formato: [{\"category\":\"identity|short_term|long_term\","
        "\"source\":\"user|assistant\",\"data\":\"...\"}]\n"
        "Texto:\n"
        f"{content}"
    )
    try:
        result = subprocess.run(
            ["ollama", "run", MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            return None
        data = _extract_json_array(result.stdout.strip())
        if not data:
            return None
        segments = []
        for item in data:
            text = (item.get("data") or "").strip()
            if len(text) < MIN_SEGMENT_LEN:
                continue
            segments.append(
                {
                    "text": text,
                    "category": item.get("category"),
                    "source": item.get("source"),
                }
            )
        return segments if segments else None
    except Exception:
        return None


def split_content(content: str) -> list[dict]:
    """
    Split raw conversation into smaller chunks before classification.
    Tries LLM-based splitting first for accuracy, then falls back to markers
    and paragraph splitting.
    """
    content = content.replace("\\r\\n", "\\n").strip()
    if not content:
        return []

    if USE_LLM_SPLITTER:
        llm_segments = _split_with_llm(content)
        if llm_segments:
            return llm_segments

    segments = _split_by_markers(content)
    if len(segments) <= 1:
        segments = _split_by_paragraphs(content)

    filtered = [s for s in segments if len(s) >= MIN_SEGMENT_LEN]
    segments = filtered if filtered else segments
    return [{"text": s} for s in segments]
