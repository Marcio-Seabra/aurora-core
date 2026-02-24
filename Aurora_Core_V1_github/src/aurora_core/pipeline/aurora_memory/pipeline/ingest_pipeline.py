import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from ..ingest.reader import read_data_files
from ..ingest.validator import validate_file
from ..ingest.splitter import split_content
from ..ai.classifier import classify_memory, VALID_TYPES
from ..memory.writer import write_memory

BASE_DIR = Path(__file__).resolve().parents[5]
MEMORY_DIR = BASE_DIR / "memory"
LOG_PATH = MEMORY_DIR / "ingest_log.jsonl"
DEDUP_PATH = MEMORY_DIR / "dedup_index.json"

def _log_event(event: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    event["ts"] = datetime.now(timezone.utc).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _build_dedup_index() -> dict:
    entries: dict[str, dict] = {}
    if not MEMORY_DIR.exists():
        return entries
    for mem_type in ("identity", "short_term", "long_term", "unclassified"):
        path = MEMORY_DIR / mem_type
        if not path.exists():
            continue
        for f in path.glob("*.txt"):
            try:
                content = f.read_text(encoding="utf-8").strip()
            except Exception:
                continue
            h = _hash_text(content)
            entries[h] = {"file": f.name, "type": mem_type}
    return entries


def _load_dedup_index() -> dict:
    if not DEDUP_PATH.exists():
        return _build_dedup_index()
    try:
        data = json.loads(DEDUP_PATH.read_text(encoding="utf-8"))
        return data.get("entries", {})
    except Exception:
        return _build_dedup_index()


def _save_dedup_index(entries: dict) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    DEDUP_PATH.write_text(
        json.dumps({"entries": entries}, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )



def run_pipeline():
    files = read_data_files()

    if not files:
        print("Nenhum arquivo encontrado.")
        return

    stats = {
        "identity": 0,
        "short_term": 0,
        "long_term": 0,
        "unclassified": 0
    }

    dedup_entries = _load_dedup_index()

    for file_path in files:
        valid, result = validate_file(file_path)

        if not valid:
            print(f"[IGNORADO] {file_path.name} -> {result}")
            _log_event(
                {
                    "file": file_path.name,
                    "status": "ignored",
                    "reason": result,
                }
            )
            continue

        content = result
        segments = split_content(content)
        total_segments = max(len(segments), 1)

        for idx, segment in enumerate(segments, start=1):
            segment_text = segment.get("text", "")
            content_hash = _hash_text(segment_text)
            if content_hash in dedup_entries:
                print(f"[DUPLICADO] {file_path.name}#{idx} -> ignorado")
                _log_event(
                    {
                        "file": file_path.name,
                        "segment": idx,
                        "segments_total": total_segments,
                        "status": "duplicate",
                        "dup_of": dedup_entries[content_hash],
                    }
                )
                continue
            preset = segment.get("category")
            if preset in VALID_TYPES:
                mem_type, err, source = preset, None, "splitter"
            else:
                mem_type, err, source = classify_memory(segment_text)

            if err:
                print(f"[ERRO] {file_path.name}#{idx} -> {err}")
                mem_type = "unclassified"

            original_filename = f"{file_path.stem}_part{idx}{file_path.suffix}"
            write_memory(mem_type, original_filename, segment_text)
            stats[mem_type] += 1
            _log_event(
                {
                    "file": file_path.name,
                    "segment": idx,
                    "segments_total": total_segments,
                    "status": "ok" if not err else "error",
                    "type": mem_type,
                    "error": err,
                    "source": source,
                }
            )
            print(f"[OK] {file_path.name}#{idx} -> {mem_type}")
            dedup_entries[content_hash] = {"file": original_filename, "type": mem_type}

    print("Filtragem concluida")
    for k, v in stats.items():
        print(f"- {k}: {v} itens")

    _save_dedup_index(dedup_entries)
