# Plataformas de Ofertas

Plataforma para coletar ofertas de marketplaces (Mercado Livre, Shopee), gerar
links de afiliado e publicar em grupos (Telegram; WhatsApp planejado).
Backend quase finalizado; frontend (painel administrativo) ainda não iniciado.

## Stack

- Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL (psycopg), Pydantic Settings
- Playwright/Chrome (CDP) para gerar links afiliados do Mercado Livre
- Credenciais criptografadas com Fernet (`CREDENTIAL_ENCRYPTION_KEY`)

## Comandos

Use o Makefile (`make` lista tudo):

```bash
make instalar        # .venv + dependências (inclui pytest)
make db              # PostgreSQL 18 no Docker, porta 5434 (docker-compose.yml)
make migrar          # alembic upgrade head
make testes          # pytest (make testes-unit: sem banco)
make api             # uvicorn --reload (LIGA as automações)
make servico-logs    # logs da API rodando como serviço systemd de usuário
make chrome-status   # Chrome/perfil do Mercado Livre detectados
alembic revision --autogenerate -m "..."   # nova migração (revisar o arquivo gerado)
```

Infra: banco no Docker (`docker-compose.yml`, volume `dados_postgres`); a API roda
fora do Docker como serviço systemd de usuário (`deploy/plataformas-ofertas-api.service`,
instalado por `make servico-instalar`), preso à sessão gráfica porque abre o Chrome.
Um único processo uvicorn (sem `--workers`: as automações rodam no lifespan).
No encerramento, `AutomacaoService.encerrando` / `PublicacaoLoteService.encerrando`
(threading.Event) interrompem coletas e ciclos; `KillMode=process` mantém o Chrome aberto.

Testes de integração (`tests/integration/`) usam o PostgreSQL do `.env` dentro
de uma transação desfeita ao final (nada é gravado) e não executam o `lifespan`.
Não suba a API só para testar: os monitores disparam coletas e publicações reais
no Telegram. O usuário do banco não tem permissão `CREATEDB`.

Variáveis de ambiente: ver `.env.example` e `src/ofertas/core/config.py`.
Nunca versionar `.env` nem exibir credenciais/tokens.

## Painel (`frontend/`)

React 18 + Vite + TypeScript, TanStack Query e `openapi-fetch`. Tipos em
`frontend/src/api/schema.d.ts` gerados do OpenAPI (`make painel-tipos`): ao mudar
uma rota/schema da API, regenere e rode `npm run verificar` em `frontend/`.
Chamadas via `chamar(api.GET(...))` (lança `ErroApi` com o `detail` da API) e
`useAcao` (mutação com aviso e recarga). Dev: Vite em :5173 com proxy `/api` →
:8000. Produção: `make painel-build` e a API serve `frontend/dist` em `/painel`
(rotas internas caem no `index.html`).

## Arquitetura (`src/ofertas/`)

Camadas, sempre nesta direção: `api/` → `services/` → `repositories/` → `models/`.

- `api/`: routers FastAPI. Fazem `commit`/`rollback` e convertem exceções:
  `LookupError` → 404, `ValueError` (regra de negócio) → 409, `IntegrityError` → 409,
  falha no envio externo → 502. 422 fica só para validação do Pydantic; 400 só no
  callback OAuth. Todo erro devolvido deve constar em `responses=` da rota
  (há teste que exige 404 documentado em rotas com ID). Rotas antigas que têm
  substituta ficam com `deprecated=True`.
- `services/`: regras de negócio. Dependências injetáveis pelo `__init__`
  (padrão `x or X()`), o que permite testes com `Mock`.
- `repositories/`: acesso ao banco; usam `session.flush()`, nunca `commit`.
- `schemas/`: Pydantic. Updates parciais com `model_dump(exclude_unset=True)`
  e validação de "ao menos um campo" / "não nulo".
- `collectors/`, `affiliates/`, `publishers/`: integrações externas.
- `main.py`: o `lifespan` sobe os monitores internos (sinal de vida, coletas,
  publicações por destino) com `asyncio.to_thread`.

Rotas (nomes do domínio): `/lojas` (de onde vêm as ofertas), `/canais-divulgacao`
(Telegram, WhatsApp), `/grupos` (onde se publica; no código e no banco ainda se
chamam `destinos_divulgacao`/`destino_id`), `/grupos/{grupo_id}/configuracao`,
`/categorias/{id}/grupos`, `/coletas/mercado-livre` e `/coletas/shopee` (sem ID).
O router de configurações de divulgação é incluído antes do de grupos para
`/grupos/configuracoes` não ser lido como `/grupos/{grupo_id}`.

Pontos importantes:
- Categoria ↔ grupos só pela tabela `plataforma_categoria_destino` (vários grupos
  por categoria). Não existe mais "destino principal" nem seleção por categoria;
  o limite de produtos é o global.
- Republicação: o mesmo produto num grupo só volta em 24h com preço **menor** que o
  menor preço publicado. "Mesmo produto" = mesmo ID ou título equivalente de qualquer
  loja (`core/similaridade_produto.py`: ignora cor/marketing; separa por código de
  modelo, armazenamento, tela, variante Pro/Ultra e acessórios). Aplicado no envio
  (`PublicacaoService._validar_republicacao`) e na seleção do ciclo, que busca 4x o
  limite por categoria para repor os barrados e fica com o mais barato entre iguais.
- Categoria com `termo_busca`: coleta por termo dentro da categoria da loja
  (Shopee: keyword + productCatId; Mercado Livre: `/products/search`, pois
  `/sites/MLB/search` dá 403 — o catálogo traz produtos sem anúncio, descartados).
- Publishers em `publishers/`: `base.PublisherBase` (validações, registro, falhas)
  + `telegram.py` (Bot API) e `whatsapp.py` (WhatsApp Web via Playwright/CDP,
  `whatsapp_web.py`, NÃO oficial). O `PublicacaoService` escolhe pelo código do
  canal; cada canal liga/desliga por `publicacao_<canal>_ativa`
  (`publicacao_do_canal_ativa`). WhatsApp: grupo = nome exato, sem credencial;
  intervalo global e limite diário (settings `WHATSAPP_*`); `WhatsAppSessaoError`
  (QR/restrição) pausa o canal. Seletores da página só em `SELETORES`.
  Chrome dedicado genérico em `core/chrome_dedicado.py` (ML: 9222, WhatsApp: 9223).
- Fuso horário e normalização de datas: `core/tempo.py` (`FUSO_HORARIO`, `garantir_utc`).
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
- Publicação manual (`POST /publicacoes/produtos/{id}`): publica em todos os
  grupos da categoria do produto com canal e grupo ativos, aplicando todas as
  regras; commit por grupo; não obedece às janelas. 200 se publicou em ao menos
  um grupo, 502 se só houve falhas de envio, 409 se todos foram ignorados.
- O intervalo entre mensagens (20s, `PublicacaoLoteService`) é independente do
  intervalo entre ciclos de publicação (por destino, no banco).

## Erros das integrações

**Shopee** (`collectors/shopee_client.py`, API GraphQL de afiliados)
- `error [10000]: System Error`: intermitente, comum. Até 3 novas tentativas
  (2s, 4s, 8s). HTTP 429/5xx e falhas de rede seguem o mesmo retry
  (respeitando `Retry-After`).
- Outros erros GraphQL (ex.: `[10020]` assinatura inválida) não são retentados.
- Uma página com falha encerra só aquela ordenação da categoria (vira aviso);
  a categoria só falha se nenhuma consulta dela der certo.

**Mercado Livre — coleta** (`collectors/mercado_livre_client.py`, API REST)
- 429/5xx e falhas de rede: até 3 novas tentativas (2s, 4s, 8s ou `Retry-After`).
- 401: token recusado, sem retry. O token é renovado antes de expirar
  (`AutenticacaoOAuthService.obter_access_token`); 401 persistente exige refazer
  `GET /oauth/mercado-livre/autorizar`.
- 403/404 em um destaque: produto ignorado e registrado como aviso.
- Destaques `USER_PRODUCT` são ignorados (fluxo de User Products não implementado;
  `/products/{id}` devolve 403 para eles). Gera vários avisos por coleta.
- Falha em `/highlights` da categoria: a categoria falha (execução `parcial`/`falhou`).

**Mercado Livre — links afiliados** (`affiliates/`, via Chrome com CDP)
- Precisa do Chrome aberto com a sessão logada (`MERCADO_LIVRE_CHROME_*`);
  sem login: `MercadoLivreLoginRequiredError`.
- Erro de um lote marca todos os produtos do lote com `status_link_afiliado='erro'`
  e a mensagem em `erro_geracao_link_afiliado`. Produtos com `erro` são
  retentados a cada coleta, sem limite.
- `The condition is unknown`: recusa do gerador do ML para o produto; até hoje
  sempre se repete nas novas tentativas.

## Convenções

- Versão: `src/ofertas/__init__.py` (`__version__`) e `pyproject.toml` (iguais; há teste).
  Versão atual 0.9.0; 1.0.0 no merge de `develop` em `main` (Etapa 6). Marcar com tag git.
- Migrações: `0001_estrutura_inicial_v0_9_0` é a base (squash das 25 antigas, que
  ficam no histórico do git). Daqui em diante, uma migração por mudança; nunca
  editar uma migração já aplicada. Migrações vão para o git, nunca para o `.gitignore`.
- Logs: `httpx`/`httpcore` ficam em WARNING de propósito. A URL da API do Telegram
  contém o token do bot e o httpx a registra em INFO (há teste).

- Código, nomes e mensagens em português.
- Commits: Conventional Commits em português (`feat:`, `fix:`, `build:`, `docs:`).
- Trabalho na branch `develop`; integração em `main` via PR ao final.

## Roadmap

1. ~~Validar configurações globais e janelas~~ (concluída: testes em `tests/`).
2. Monitoramento: últimas execuções ML/Shopee, ciclos por destino, persistir o
   estado da publicação em andamento, decidir se execuções manuais obedecem às janelas.
3. ~~Documentação e infra~~ (concluída: README, Makefile, Docker Compose, systemd).
4. ~~Publisher WhatsApp~~ (WhatsApp Web; falta validar os seletores com a sessão real).
5. ~~Painel administrativo~~ (frontend/; servido em /painel).
6. Fechamento: auditoria, segurança, erros, dependências, merge develop → main.
