#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -f ".venv/bin/activate" ]]; then
    source ".venv/bin/activate"
else
    echo "Erro: ambiente virtual .venv não encontrado."
    exit 1
fi

exec python -m uvicorn ofertas.main:app --reload
