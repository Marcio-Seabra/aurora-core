from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[5]
MEMORY_DIR = BASE_DIR / "memory"

def write_memory(mem_type, original_filename, content):
    target_dir = MEMORY_DIR / mem_type
    target_dir.mkdir(parents=True, exist_ok=True)

    new_filename = f"{mem_type}_{original_filename}"
    target_path = target_dir / new_filename

    target_path.write_text(content, encoding="utf-8")
