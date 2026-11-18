# Plataformas de Ofertas - comandos do dia a dia. Rode `make` para ver a lista.

SHELL := /bin/bash
.DEFAULT_GOAL := ajuda

RAIZ        := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
VENV        := $(RAIZ)/.venv
PY          := $(VENV)/bin/python
COMPOSE     := docker compose
SERVICO     := plataformas-ofertas-api
UNIT_DIR    := $(HOME)/.config/systemd/user
UNIT        := $(UNIT_DIR)/$(SERVICO).service
API_HOST    ?= 127.0.0.1
API_PORTA   ?= 8000
BACKUPS     := $(RAIZ)/backups
BACKUPS_MANTER ?= 14
SERVICO_BACKUP := plataformas-ofertas-backup

# psql dentro do container, com o usuário e o banco do próprio container.
PSQL_DB = $(COMPOSE) exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

.PHONY: ajuda instalar subir parar status \
        db db-parar db-logs db-psql db-backup backup-agendar backup-desagendar db-importar \
        migrar testes testes-unit api \
        chrome-login chrome-verificar chrome-status chrome-fechar \
        painel-instalar painel painel-build painel-tipos usuario-admin usuario-senha \
        whatsapp-login whatsapp-verificar whatsapp-status whatsapp-fechar whatsapp-teste \
        servico-instalar servico-iniciar servico-parar servico-reiniciar \
        servico-status servico-logs servico-desinstalar

ajuda: ## Mostra esta ajuda
	@echo "Uso: make <comando>"
	@echo
	@grep -hE '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "} {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- instalação
instalar: ## Cria o .venv, instala as dependências e o .env (se faltar)
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip
	$(VENV)/bin/pip install -q -e ".[dev]"
	@test -f .env || { cp .env.example .env; \
		echo ">> .env criado a partir do .env.example: preencha POSTGRES_SENHA,"; \
		echo "   DATABASE_URL e CREDENTIAL_ENCRYPTION_KEY antes de continuar."; }

# ------------------------------------------------------------ uso diário
subir: db migrar servico-iniciar ## Sobe o banco, aplica migrações e inicia a API
	@echo ">> API em http://$(API_HOST):$(API_PORTA)/docs"

parar: servico-parar db-parar ## Para a API e o banco

status: ## Mostra banco, API e Chrome do Mercado Livre
	@echo "== Banco";  $(COMPOSE) ps db
	@echo "== API";    systemctl --user is-active $(SERVICO) || true
	@echo "== Chrome"; $(PY) -m scripts.chrome_mercado_livre status

# ------------------------------------------------------------------- banco
db: ## Sobe o PostgreSQL (Docker) e espera ficar pronto
	$(COMPOSE) up -d --wait db

db-parar: ## Para o PostgreSQL (os dados ficam no volume)
	$(COMPOSE) stop db

db-logs: ## Acompanha os logs do PostgreSQL
	$(COMPOSE) logs -f db

db-psql: ## Abre o psql no banco do projeto
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

db-backup: ## Backup compactado em backups/ (guarda os últimos BACKUPS_MANTER=14)
	@mkdir -p $(BACKUPS)
	@set -o pipefail; destino="$(BACKUPS)/$$(date +%Y-%m-%d_%H%M).sql.gz"; \
	$(COMPOSE) exec -T db sh -c 'pg_dump --no-owner --no-acl -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"' \
		| gzip > "$$destino.parcial" && mv "$$destino.parcial" "$$destino" && ls -lh "$$destino"
	@# Rotação: apaga só os .sql.gz mais antigos de backups/, além dos últimos N.
	@ls -1t "$(BACKUPS)"/*.sql.gz 2>/dev/null | tail -n +$$(( $(BACKUPS_MANTER) + 1 )) | xargs -r rm -f --

backup-agendar: ## Agenda o backup diário (timer systemd; roda ao ligar se perdeu o horário)
	@mkdir -p $(UNIT_DIR)
	sed -e 's|@RAIZ@|$(RAIZ)|g' deploy/$(SERVICO_BACKUP).service > $(UNIT_DIR)/$(SERVICO_BACKUP).service
	cp deploy/$(SERVICO_BACKUP).timer $(UNIT_DIR)/$(SERVICO_BACKUP).timer
	systemctl --user daemon-reload
	systemctl --user enable --now $(SERVICO_BACKUP).timer
	@systemctl --user list-timers $(SERVICO_BACKUP).timer --no-pager | head -2

backup-desagendar: ## Remove o backup diário agendado
	-systemctl --user disable --now $(SERVICO_BACKUP).timer
	rm -f $(UNIT_DIR)/$(SERVICO_BACKUP).service $(UNIT_DIR)/$(SERVICO_BACKUP).timer
	systemctl --user daemon-reload

db-importar: ## Copia um banco existente para o Docker: make db-importar ORIGEM=postgresql://...
	@test -n "$(ORIGEM)" || { echo "Informe ORIGEM=postgresql://usuario:senha@host:porta/banco"; exit 1; }
	@test -z "$$($(PSQL_DB) -tAc "select 1 from information_schema.tables where table_name = 'alembic_version'")" || \
		{ echo "O banco do Docker já tem tabelas. Para recomeçar: docker compose down -v"; exit 1; }
	@echo ">> Copiando dados (a URL não é exibida para não mostrar a senha)..."
	@set -o pipefail; pg_dump --no-owner --no-acl "$(ORIGEM)" | $(PSQL_DB) -q
	@echo ">> Importação concluída. Ajuste a DATABASE_URL do .env para a porta do Docker."

migrar: ## Aplica as migrações pendentes (alembic upgrade head)
	$(VENV)/bin/alembic upgrade head

# ------------------------------------------------------------------ código
testes: ## Roda todos os testes (unitários e de integração com o banco)
	$(PY) -m pytest

testes-unit: ## Roda só os testes unitários (sem banco)
	$(PY) -m pytest tests/unit

api: ## Roda a API em modo desenvolvimento (recarrega ao salvar; liga as automações)
	@! systemctl --user is-active --quiet $(SERVICO) || \
		{ echo "O serviço já está rodando. Use 'make servico-parar' antes."; exit 1; }
	$(VENV)/bin/uvicorn ofertas.main:app --reload --host $(API_HOST) --port $(API_PORTA)

# ---------------------------------------------------- Chrome Mercado Livre
chrome-login: ## Abre o Chrome do projeto para fazer login no Mercado Livre
	$(PY) -m scripts.chrome_mercado_livre login

chrome-verificar: ## Confere se a sessão do Mercado Livre está autenticada
	$(PY) -m scripts.chrome_mercado_livre verificar

chrome-status: ## Mostra o Chrome e o perfil detectados
	$(PY) -m scripts.chrome_mercado_livre status

chrome-fechar: ## Fecha o Chrome do projeto
	$(PY) -m scripts.chrome_mercado_livre fechar

# ------------------------------------------- WhatsApp Web (não oficial)
whatsapp-login: ## Abre o Chrome do WhatsApp para ler o QR Code
	$(PY) -m scripts.whatsapp_web login

whatsapp-verificar: ## Confere se o WhatsApp Web está conectado
	$(PY) -m scripts.whatsapp_web verificar

whatsapp-status: ## Mostra perfil, porta e limites do WhatsApp
	$(PY) -m scripts.whatsapp_web status

whatsapp-fechar: ## Fecha o Chrome do WhatsApp
	$(PY) -m scripts.whatsapp_web fechar

whatsapp-teste: ## Prepara mensagem de teste SEM enviar: make whatsapp-teste GRUPO="Nome" [ENVIAR=1]
	@test -n "$(GRUPO)" || { echo 'Informe GRUPO="Nome exato do grupo"'; exit 1; }
	$(PY) -m scripts.whatsapp_web teste "$(GRUPO)" $(if $(ENVIAR),--enviar,)

# -------------------------------------------------------------- painel
usuario-admin: ## Cria o admin master do painel (pede a senha): make usuario-admin [LOGIN=admin]
	$(PY) -m scripts.usuarios admin $(or $(LOGIN),admin)

usuario-senha: ## Troca a senha de um usuário do painel: make usuario-senha LOGIN=admin
	@test -n "$(LOGIN)" || { echo 'Informe LOGIN=...'; exit 1; }
	$(PY) -m scripts.usuarios senha "$(LOGIN)"

painel-instalar: ## Instala as dependências do painel (frontend/)
	cd frontend && npm ci --no-audit --no-fund

painel: ## Painel em desenvolvimento em http://127.0.0.1:5173/painel/ (usa a API em :8000)
	cd frontend && npm run dev

painel-build: ## Compila o painel; a API passa a servi-lo em /painel
	cd frontend && npm run build

painel-tipos: ## Regenera os tipos TypeScript a partir das rotas da API
	$(PY) -c "import json, logging; logging.disable(logging.CRITICAL); from ofertas.main import app; json.dump(app.openapi(), open('frontend/openapi.json', 'w'), ensure_ascii=False, indent=1)"
	cd frontend && npm run tipos

# ----------------------------------------------------------- serviço systemd
servico-instalar: ## Instala a API como serviço (sobe junto com a sessão gráfica)
	@test -x $(VENV)/bin/uvicorn || { echo "Rode 'make instalar' antes."; exit 1; }
	@mkdir -p $(UNIT_DIR)
	sed -e 's|@RAIZ@|$(RAIZ)|g' -e 's|@HOST@|$(API_HOST)|g' -e 's|@PORTA@|$(API_PORTA)|g' \
		deploy/$(SERVICO).service > $(UNIT)
	systemctl --user daemon-reload
	systemctl --user enable $(SERVICO)
	@echo ">> Instalado. Inicie com: make servico-iniciar"

servico-iniciar: ## Inicia a API (liga as automações de coleta e publicação)
	@test -f $(UNIT) || { echo "Serviço não instalado. Rode 'make servico-instalar'."; exit 1; }
	systemctl --user start $(SERVICO)
	@systemctl --user --no-pager status $(SERVICO) | head -5

servico-parar: ## Para a API
	-systemctl --user stop $(SERVICO)

servico-reiniciar: ## Reinicia a API (use após atualizar o código)
	systemctl --user restart $(SERVICO)

servico-status: ## Mostra o estado do serviço
	-systemctl --user --no-pager status $(SERVICO)

servico-logs: ## Acompanha os logs da API
	journalctl --user -u $(SERVICO) -f -o cat

servico-desinstalar: ## Remove o serviço
	-systemctl --user disable --now $(SERVICO)
	rm -f $(UNIT)
	systemctl --user daemon-reload
