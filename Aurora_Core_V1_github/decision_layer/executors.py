from __future__ import annotations

import json
import http.client
from typing import Callable

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
MODEL_NAME = "aurora-nucleo:latest"


def _call_llm(prompt: str, stream: bool = False) -> str:
    payload = json.dumps({
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": stream
    })
    headers = {"Content-Type": "application/json"}
    conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT)
    try:
        conn.request("POST", "/api/generate", payload, headers)
        response = conn.getresponse()
        if response.status != 200:
            return f"Erro HTTP {response.status}: {response.reason}"
        if not stream:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "").strip()

        text = ""
        for line in response:
            try:
                obj = json.loads(line.decode("utf-8"))
            except Exception:
                continue
            chunk = obj.get("response", "")
            if chunk:
                print(chunk, end="", flush=True)
                text += chunk
        return text.strip()
    except Exception as e:
        return f"Erro de comunicacao: {e}"
    finally:
        conn.close()


def execute_chat(prompt: str, stream: bool = False) -> str:
    return _call_llm(prompt, stream=stream)


def execute_image(user_input: str) -> str:
    return "Rota imagem selecionada, mas o executor de imagem ainda nao foi implementado."


def execute_video(user_input: str) -> str:
    return "Rota video selecionada, mas o executor de video ainda nao foi implementado."


def execute_tool(user_input: str) -> str:
    return "Rota tool selecionada, mas o executor de ferramentas ainda nao foi implementado."


def execute_route(route: str, prompt: str, user_input: str, stream: bool = False) -> str:
    handlers: dict[str, Callable[[str], str]] = {
        "chat": lambda _u: execute_chat(prompt, stream=stream),
        "image": execute_image,
        "video": execute_video,
        "tool": execute_tool,
    }
    handler = handlers.get(route, handlers["chat"])
    return handler(user_input)
