import re
from pathlib import Path
import http.client
import json

# Caminhos base
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR / "memory"

# Regex: qualquer_nome_DD_MM_AAAA.txt
FILENAME_PATTERN = re.compile(r".+_\d{2}_\d{2}_\d{4}\.txt$")

MEMORY_TYPES = ["identity", "short_term", "long_term"]

# Ollama
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
MODEL_NAME = "aurora_memory:latest"

# Quantas linhas por chamada da IA
CHUNK_SIZE = 4


def chunks(lst, size):
    """Divide lista em blocos menores"""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def classify_chunk_ai(lines: list[str]) -> list[dict]:
    """
    Envia um bloco de linhas para a IA.
    Espera retorno em JSON:
    [
      {"category": "...", "source": "...", "data": "..."},
      ...
    ]
    """
    prompt = "\n".join(lines)

    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT)
    payload = json.dumps({
        "model": MODEL_NAME,
        "prompt": prompt,
        "max_tokens": 512
    })
    headers = {"Content-Type": "application/json"}

    try:
        conn.request("POST", "/api/generate", payload, headers)
        response = conn.getresponse()

        if response.status != 200:
            print(f"❌ Erro HTTP: {response.status}")
            return []

        raw = response.read().decode("utf-8")

        # Junta streaming
        text = ""
        for line in raw.splitlines():
            try:
                obj = json.loads(line)
                text += obj.get("response", "")
            except:
                continue

        return json.loads(text)

    except Exception as e:
        print("❌ Erro IA:", e)
        return []

    finally:
        conn.close()


def process_files():
    if not DATA_DIR.exists():
        print("❌ Pasta data não encontrada")
        return

    files = [
        f for f in DATA_DIR.iterdir()
        if f.is_file() and f.suffix == ".txt" and FILENAME_PATTERN.match(f.name)
    ]

    if not files:
        print("⚠ Nenhum arquivo válido encontrado")
        return

    for file in files:
        with file.open("r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        counters = {t: 0 for t in MEMORY_TYPES}
        safe_name = re.sub(r"[^\w\d]+", "_", file.stem)

        for block in chunks(lines, CHUNK_SIZE):
            results = classify_chunk_ai(block)

            for item in results:
                category = item.get("category")
                source = item.get("source")
                data = item.get("data")

                if category not in MEMORY_TYPES or not data:
                    continue

                counters[category] += 1

                mem_dir = MEMORY_DIR / category
                mem_dir.mkdir(parents=True, exist_ok=True)

                out = mem_dir / f"{category}_{source}_{safe_name}_{counters[category]}.txt"
                out.write_text(data, encoding="utf-8")

    print("✔ Filtragem concluída")
    for t in MEMORY_TYPES:
        p = MEMORY_DIR / t
        print(f"- {t}: {len(list(p.glob('*.txt'))) if p.exists() else 0} arquivos")


if __name__ == "__main__":
    process_files()
