import re
import unicodedata

from ai.ollama_client import ask_ollama

VALID_TYPES = ["identity", "short_term", "long_term"]

IDENTITY_PATTERNS = [
    r"\bmeu nome e\b",
    r"\bme chamo\b",
    r"\beu sou\b",
    r"\beu tenho \d+ anos\b",
    r"\bminha idade\b",
    r"\beu moro\b",
    r"\bminha profissao\b",
    r"\btrabalho como\b",
    r"\beu gosto de\b",
    r"\bmeus? hobbies?\b",
]


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def _looks_like_identity(content: str) -> bool:
    normalized = _normalize(content)
    for pat in IDENTITY_PATTERNS:
        if re.search(pat, normalized):
            return True
    return False

PROMPT_TEMPLATE = """
Classifique o texto abaixo em APENAS UM dos tipos:

identity
short_term
long_term

Responda apenas com o nome do tipo.

Texto:
{content}
"""

def classify_memory(content):
    if _looks_like_identity(content):
        return "identity", None, "heuristic"

    prompt = PROMPT_TEMPLATE.format(content=content)
    response = ask_ollama(prompt)
    if not response:
        return None, "empty_response", "model"
    response = response.strip().lower()
    if response.startswith("error:"):
        return None, response, "model"

    first_line = response.splitlines()[0].strip()
    if first_line in VALID_TYPES:
        return first_line, None, "model"

    return None, f"unrecognized_response:{first_line}", "model"
