import subprocess
import os

# Aurora models are based on Llama 3.1 via Ollama
# Change AURORA_MEMORY_MODEL to switch the model used by ingest classification.
MODEL_NAME = os.getenv("AURORA_MEMORY_MODEL", "aurora_memory:latest")

def ask_ollama(prompt):
    try:
        result = subprocess.run(
            ["ollama", "run", MODEL_NAME],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if result.returncode != 0:
            err = (result.stderr or "").strip()
            return f"error:ollama_exit_{result.returncode}:{err}"
        return result.stdout.strip()
    except Exception as e:
        return f"error:exception:{e}"
