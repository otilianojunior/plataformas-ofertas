# Plataformas de Ofertas

Plataforma para coletar ofertas de marketplaces (Mercado Livre, Shopee), gerar
links de afiliado e publicar em grupos (Telegram; WhatsApp planejado).
Backend quase finalizado; frontend (painel administrativo) ainda não iniciado.

## Stack

- Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (psycopg), Pydantic Settings
- Playwright/Chrome (CDP) para gerar links afiliados do Mercado Livre
- Credenciais criptografadas com Fernet (`CREDENTIAL_ENCRYPTION_KEY`)

## Comandos

```bash
source .venv/bin/activate
uvicorn ofertas.main:app --reload          # API (pacote instalado em modo editável)
alembic upgrade head                        # aplicar migrações
alembic revision --autogenerate -m "..."    # nova migração (revisar o arquivo gerado)
pip install -e ".[dev]"                     # dependências de desenvolvimento (pytest)
python -m pytest                            # todos os testes
python -m pytest tests/unit                 # só unitários (sem banco)
python -m compileall -q src                 # checagem rápida de sintaxe
```

Testes de integração (`tests/integration/`) usam o PostgreSQL do `.env` dentro
de uma transação desfeita ao final (nada é gravado) e não executam o `lifespan`.
Não suba a API só para testar: os monitores disparam coletas e publicações reais
no Telegram. O usuário do banco não tem permissão `CREATEDB`.

Variáveis de ambiente: ver `.env.example` e `src/ofertas/core/config.py`.
Nunca versionar `.env` nem exibir credenciais/tokens.

## Arquitetura (`src/ofertas/`)

Camadas, sempre nesta direção: `api/` → `services/` → `repositories/` → `models/`.

- `api/`: routers FastAPI. Fazem `commit`/`rollback` e convertem exceções:
  `LookupError` → 404, `ValueError` → 409/400, `IntegrityError` → 409.
- `services/`: regras de negócio. Dependências injetáveis pelo `__init__`
  (padrão `x or X()`), o que permite testes com `Mock`.
- `repositories/`: acesso ao banco; usam `session.flush()`, nunca `commit`.
- `schemas/`: Pydantic. Updates parciais com `model_dump(exclude_unset=True)`
  e validação de "ao menos um campo" / "não nulo".
- `collectors/`, `affiliates/`, `publishers/`: integrações externas.
- `main.py`: o `lifespan` sobe os monitores internos (sinal de vida, coletas,
  publicações por destino) com `asyncio.to_thread`.

Pontos importantes:
- `configuracoes_sistema` é uma linha única (id=1) com os controles globais:
  `automacoes_ativas`, flags por automação, `intervalo_coleta_minutos`,
  `limite_produtos_por_categoria`.
- `janelas_execucao`: janelas diárias no fuso `America/Sao_Paulo`, sem atravessar
  a meia-noite, sem sobreposição entre janelas ativas. Horários sem fuso;
  início inclusivo, fim exclusivo (para ir até o fim do dia use `23:59:59`). Sem nenhuma janela ativa,
  a execução fica liberada 24h.
- Locks com `pg_advisory_xact_lock` evitam ciclos concorrentes (publicação por
  destino, alterações de janelas).
- `execucoes_coleta.status`: `concluida`, `parcial` (alguma categoria falhou, outras
  não) ou `falhou` (nenhuma categoria coletada). O registro só é commitado no fim
  da coleta, então `em_andamento` não aparece para outras sessões.
- `ciclos_publicacao`: um registro por ciclo automático de destino, com progresso
  gravado a cada produto. Ciclos que ficaram `em_andamento` (API encerrada no
  meio) viram `interrompido` no próximo ciclo do destino. Consulta: `GET /ciclos-publicacao`.
- A Shopee devolve `error [10000]: System Error` de forma intermitente; o
  `ShopeeClient` faz até 3 novas tentativas (2s, 4s, 8s).
- O intervalo entre mensagens (20s, `PublicacaoLoteService`) é independente do
  intervalo entre ciclos de publicação (por destino, no banco).

## Convenções

- Código, nomes e mensagens em português.
- Commits: Conventional Commits em português (`feat:`, `fix:`, `build:`, `docs:`).
- Trabalho na branch `develop`; integração em `main` via PR ao final.

## Roadmap

1. ~~Validar configurações globais e janelas~~ (concluída: testes em `tests/`).
2. Monitoramento: últimas execuções ML/Shopee, ciclos por destino, persistir o
   estado da publicação em andamento, decidir se execuções manuais obedecem às janelas.
3. Documentação e infra: README, variáveis de ambiente, Makefile, Docker Compose
   (API + Postgres), inicialização/encerramento/workers.
4. Publisher WhatsApp (credenciais, destinos/categorias, regras, monitoramento).
5. Painel administrativo (frontend) sobre as rotas existentes.
6. Fechamento: auditoria, segurança, erros, dependências, merge develop → main.
