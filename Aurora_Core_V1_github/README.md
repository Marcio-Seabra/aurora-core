# Aurora Core V1 (GitHub Edition)

Projeto: Aurora (IA administradora com memoria externa).

## Requisitos
- Python 3.11
- Ollama instalado (modelos: `aurora_core`, `aurora_memory`)
- Modelos baseados em Llama 3.1 via Ollama

## Estrutura
- `core/`: loop principal e chat com memoria
- `scripts/aurora_memory/`: pipeline de ingestao e classificacao de memoria
- `decision_layer/`: roteamento de modo/rota

## Rodar o core
```bash
py core\core.py --mode fast
```

## Rodar ingest
```bash
py scripts\aurora_memory\run_ingest.py
```

> Observacao: esta versao nao inclui dados pessoais nem memoria gerada.

## Arquitetura
Veja `docs/architecture.md`.
