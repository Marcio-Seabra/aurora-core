import json
import http.client
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RULES_PATH = BASE_DIR / "decision_layer" / "rules.json"

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
MODEL_NAME = "aurora-nucleo:latest"


def _load_rules() -> dict:
    if not RULES_PATH.exists():
        return {}
    try:
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _rule_based_route(user_input: str) -> dict | None:
    rules = _load_rules()
    route_rules = rules.get("route_rules", [])
    text = user_input.lower()
    for rule in route_rules:
        keywords = rule.get("keywords", [])
        if any(k in text for k in keywords):
            return {
                "route": rule.get("route", "chat"),
                "mode": rule.get("mode", "natural"),
                "reason": rule.get("reason", "rule_match"),
            }
    return None


def _llm_route(user_input: str) -> dict:
    prompt = (
        "Decida a rota ideal para a pergunta. Responda apenas JSON valido:\n"
        "{ \"route\": \"chat|image|video|tool\", \"mode\": \"natural|analitico|estruturado\", "
        "\"reason\": \"...\" }\n"
        f"Pergunta: {user_input}"
    )

    payload = json.dumps({"model": MODEL_NAME, "prompt": prompt, "stream": False})
    headers = {"Content-Type": "application/json"}
    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT)
    try:
        conn.request("POST", "/api/generate", payload, headers)
        response = conn.getresponse()
        if response.status != 200:
            return {"route": "chat", "mode": "natural", "reason": f"http_{response.status}"}
        data = json.loads(response.read().decode("utf-8"))
        raw = data.get("response", "").strip()
        return json.loads(raw)
    except Exception as e:
        return {"route": "chat", "mode": "natural", "reason": f"fallback:{e}"}
    finally:
        conn.close()


def decide_route(user_input: str) -> dict:
    rule = _rule_based_route(user_input)
    if rule:
        return rule
    return _llm_route(user_input)
