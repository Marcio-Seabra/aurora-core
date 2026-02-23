import os
import re
from pathlib import Path

# Caminhos base
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR / "memory"

# Regex: qualquer_nome_DD_MM_AAAA.txt
FILENAME_PATTERN = re.compile(r".+_\d{2}_\d{2}_\d{4}\.txt$")

MEMORY_TYPES = {
    "identity": [],
    "short_term": [],
    "long_term": []
}

def classify_line(line: str) -> str | None:
    """
    Define o tipo de memória baseado no conteúdo.
    Ajuste essa lógica depois se quiser.
    """
    line_lower = line.lower()

    if any(k in line_lower for k in ["meu nome", "sou", "eu sou", "identidade"]):
        return "identity"

    if any(k in line_lower for k in ["hoje", "agora", "no momento"]):
        return "short_term"

    if len(line) > 40:
        return "long_term"

    return None


def process_files():
    if not DATA_DIR.exists():
        print("❌ Pasta data não encontrada")
        return

    txt_files = [
        f for f in DATA_DIR.iterdir()
        if f.is_file()
        and f.suffix == ".txt"
        and FILENAME_PATTERN.match(f.name)
    ]

    if not txt_files:
        print("⚠ Nenhum arquivo TXT válido encontrado em data/")
        return

    for file in txt_files:
        with file.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        for line in lines:
            mem_type = classify_line(line)
            if mem_type:
                MEMORY_TYPES[mem_type].append((file.name, line))

    save_memories()


def save_memories():
    for mem_type, items in MEMORY_TYPES.items():
        if not items:
            continue

        mem_path = MEMORY_DIR / mem_type
        mem_path.mkdir(parents=True, exist_ok=True)

        grouped = {}

        for original_name, content in items:
            new_name = f"{mem_type}_{original_name}"
            grouped.setdefault(new_name, []).append(content)

        for filename, contents in grouped.items():
            output_file = mem_path / filename
            with output_file.open("a", encoding="utf-8") as f:
                for line in contents:
                    f.write(line + "\n")

    print("✔ Filtragem concluída")
    for mem_type, items in MEMORY_TYPES.items():
        print(f"- {mem_type.replace('_', ' ').title()}: {len(items)} itens")


if __name__ == "__main__":
    process_files()
