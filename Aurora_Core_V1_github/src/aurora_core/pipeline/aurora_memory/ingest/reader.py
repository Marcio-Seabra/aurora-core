from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[5]
DATA_DIR = BASE_DIR / "data"

def read_data_files():
    if not DATA_DIR.exists():
        print(f"[ERRO] Pasta data nao encontrada: {DATA_DIR}")
        return []

    return list(DATA_DIR.glob("*.txt"))
