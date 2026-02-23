from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parents[1]
MEMORY_DIR = BASE_DIR / "memory"
INDEX_PATH = MEMORY_DIR / "memory_index.json"
CANONICAL_DIR = MEMORY_DIR / "canonical"

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{3,}")
INJECTION_PATTERNS = [
    r"ignore (todas|todas as|as) instrucoes",
    r"ignore (as )?instrucoes anteriores",
    r"desconsidere (as )?regras",
    r"voce deve",
    r"siga estas instrucoes",
    r"system prompt",
    r"mensagem do sistema",
    r"revel(e|ar) seu prompt",
    r"mostre suas instrucoes",
]


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _summarize(text: str, max_len: int = 200) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _sanitize_memory(text: str) -> str:
    lines = [l.strip() for l in text.splitlines()]
    safe_lines = []
    for line in lines:
        line_low = line.lower()
        if any(re.search(p, line_low) for p in INJECTION_PATTERNS):
            continue
        safe_lines.append(line)
    return "\n".join(safe_lines).strip()


def _truncate_item(text: str, max_len: int) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _extract_tags(text: str, max_tags: int = 8) -> list[str]:
    tokens = _tokenize(text)
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    tags = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
    return [t for t, _ in tags[:max_tags]]


def _list_memory_files() -> list[Path]:
    files: list[Path] = []
    if not MEMORY_DIR.exists():
        return files
    for mem_type in ("identity", "short_term", "long_term", "unclassified"):
        path = MEMORY_DIR / mem_type
        if not path.exists():
            continue
        files.extend(path.glob("*.txt"))
    return files


def build_canonical_memory(
    memory_type: str,
    limit: int = 50,
    max_len: int = 160,
    write_file: bool = True,
) -> str:
    items = load_memory(memory_type, limit=limit)
    if not items:
        return ""
    lines = [f"- {_summarize(item, max_len=max_len)}" for item in items]
    content = "\n".join(lines)
    if write_file:
        CANONICAL_DIR.mkdir(parents=True, exist_ok=True)
        path = CANONICAL_DIR / f"{memory_type}.txt"
        path.write_text(content, encoding="utf-8")
    return content


def load_canonical_memory(memory_type: str) -> str:
    path = CANONICAL_DIR / f"{memory_type}.txt"
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def get_or_build_canonical_memory(memory_type: str) -> str:
    content = load_canonical_memory(memory_type)
    if content:
        return content
    return build_canonical_memory(memory_type, write_file=True)


def _index_is_stale(files: list[Path]) -> bool:
    if not INDEX_PATH.exists():
        return True
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        index_mtime = data.get("index_mtime", 0)
    except Exception:
        return True
    for f in files:
        try:
            if f.stat().st_mtime > index_mtime:
                return True
        except Exception:
            return True
    return False


def build_memory_index(force: bool = False) -> dict:
    files = _list_memory_files()
    if not force and not _index_is_stale(files):
        return load_memory_index()

    entries = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8").strip()
            text = _sanitize_memory(text)
            if not text:
                continue
        except Exception:
            continue
        mem_type = f.parent.name
        entries.append(
            {
                "path": str(f),
                "type": mem_type,
                "mtime": f.stat().st_mtime,
                "summary": _summarize(text),
                "tags": _extract_tags(text),
                "text": text,
            }
        )

    data = {
        "index_mtime": time.time(),
        "count": len(entries),
        "entries": entries,
    }
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return data


def load_memory_index() -> dict:
    if not INDEX_PATH.exists():
        return build_memory_index(force=True)
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return build_memory_index(force=True)


def _tfidf_vectors(texts: list[str]) -> tuple[list[dict[str, float]], dict[str, float]]:
    doc_freq: dict[str, int] = {}
    tokenized = []
    for text in texts:
        tokens = _tokenize(text)
        tokenized.append(tokens)
        unique = set(tokens)
        for t in unique:
            doc_freq[t] = doc_freq.get(t, 0) + 1

    n_docs = max(len(texts), 1)
    idf = {t: math.log((1 + n_docs) / (1 + df)) + 1.0 for t, df in doc_freq.items()}

    vectors: list[dict[str, float]] = []
    for tokens in tokenized:
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        vec: dict[str, float] = {}
        for t, c in tf.items():
            vec[t] = (c / len(tokens)) * idf.get(t, 0.0)
        vectors.append(vec)
    return vectors, idf


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = 0.0
    for k, v in a.items():
        if k in b:
            dot += v * b[k]
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def search_memory(query: str, types: list[str] | None = None, top_k: int = 8) -> list[dict]:
    index = load_memory_index()
    entries = index.get("entries", [])
    if types:
        entries = [e for e in entries if e.get("type") in types]
    if not entries:
        return []

    texts = [e.get("text", "") for e in entries]
    vectors, idf = _tfidf_vectors(texts)
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    q_tf: dict[str, int] = {}
    for t in query_tokens:
        q_tf[t] = q_tf.get(t, 0) + 1
    q_vec: dict[str, float] = {}
    for t, c in q_tf.items():
        q_vec[t] = (c / len(query_tokens)) * idf.get(t, 0.0)

    scored = []
    for entry, vec in zip(entries, vectors):
        score = _cosine(q_vec, vec)
        if score > 0.0:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]]


def load_memory(memory_type: str, limit: int | None = None) -> list[str]:
    path = MEMORY_DIR / memory_type
    if not path.exists():
        return []

    files = sorted(path.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    if limit:
        files = files[:limit]

    memories = []
    for file in files:
        try:
            raw = file.read_text(encoding="utf-8").strip()
            sanitized = _sanitize_memory(raw)
            if sanitized:
                memories.append(sanitized)
        except Exception:
            continue
    return memories


def build_memory_context(
    query: str | None = None,
    short_term_limit: int = 20,
    long_term_limit: int = 10,
    top_k: int = 8,
    include_canonical: bool = True,
    max_item_chars: int = 400,
) -> str:
    sections: list[str] = []

    identity = load_memory("identity")
    if identity:
        sections.append("IDENTITY MEMORY:")
        for item in identity:
            sections.append(f"- {_truncate_item(item, max_item_chars)}")

    if include_canonical:
        identity_canon = get_or_build_canonical_memory("identity")
        if identity_canon:
            sections.append("\nIDENTITY SUMMARY:")
            sections.append(identity_canon)

    if query:
        short_hits = search_memory(query, types=["short_term"], top_k=top_k)
        if short_hits:
            sections.append("\nSHORT-TERM MEMORY:")
            for item in short_hits[:short_term_limit]:
                sections.append(f"- {_truncate_item(item['text'], max_item_chars)}")

        long_hits = search_memory(query, types=["long_term"], top_k=top_k)
        if long_hits:
            sections.append("\nLONG-TERM MEMORY:")
            for item in long_hits[:long_term_limit]:
                sections.append(f"- {_truncate_item(item['text'], max_item_chars)}")
    else:
        short_term = load_memory("short_term", short_term_limit)
        if short_term:
            sections.append("\nSHORT-TERM MEMORY:")
            for item in short_term:
                sections.append(f"- {_truncate_item(item, max_item_chars)}")

        long_term = load_memory("long_term", long_term_limit)
        if long_term:
            sections.append("\nLONG-TERM MEMORY:")
            for item in long_term:
                sections.append(f"- {_truncate_item(item, max_item_chars)}")

    if include_canonical:
        long_canon = get_or_build_canonical_memory("long_term")
        if long_canon:
            sections.append("\nLONG-TERM SUMMARY:")
            sections.append(long_canon)

    return "\n".join(sections)


def build_prompt_with_memory(
    query: str,
    short_term_limit: int = 20,
    long_term_limit: int = 10,
    top_k: int = 8,
    include_canonical: bool = True,
    max_item_chars: int = 400,
) -> str:
    """
    Returns a prompt that includes memory context plus the user query.
    The caller can send this to the model without requesting a final answer here.
    """
    context = build_memory_context(
        query=query,
        short_term_limit=short_term_limit,
        long_term_limit=long_term_limit,
        top_k=top_k,
        include_canonical=include_canonical,
        max_item_chars=max_item_chars,
    ).strip()
    if context:
        return f"{context}\n\nUSER:\n{query}"
    return query
