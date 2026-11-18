# Plataformas de Ofertas

Coleta ofertas de lojas (Mercado Livre e Shopee), gera links de afiliado e
publica as melhores ofertas em grupos do Telegram e do WhatsApp, de forma
automática e com controle de horários, limites e regras de desconto.

## Como funciona

```
 Lojas (ML, Shopee) ──coleta──▶ Produtos ──link afiliado──▶ Produtos elegíveis
                                                                 │
                     regras do grupo (desconto, preço, 24h) ◀────┘
                                   │
                                   ▼
                          Grupos (Telegram / WhatsApp)
```

- **API e automações no mesmo processo.** Ao subir, a API inicia três
  monitores internos: sinal de vida, coletas e publicações por grupo.
- **Coleta:** a cada `intervalo_coleta_minutos`, cada loja ativa coleta as
  categorias ativas e gera os links de afiliado pendentes.
- **Publicação:** cada grupo tem o próprio intervalo entre ciclos. Um ciclo
  escolhe até `limite_produtos_por_categoria` produtos por categoria e envia uma
  mensagem a cada 20 segundos.
- **Sem repetição com preço maior:** o mesmo produto, reconhecido pelo título
  mesmo vindo de outra loja, só volta a um grupo em menos de 24h se o preço for
  menor que o já publicado. Quando um produto é barrado, o ciclo usa o próximo
  da lista.
- **Categorias por termo:** além dos destaques de uma categoria, dá para coletar
  por busca (`termo_busca`, ex.: "headset razer") dentro dela.
- **Janelas de execução:** quando há janelas ativas, as automações só rodam
  dentro delas (horário de Brasília). Sem janelas, rodam 24h. As execuções
  manuais não obedecem às janelas.
- **Mercado Livre:** os links de afiliado são gerados por um Chrome dedicado do
  projeto, logado na sua conta de afiliado (veja [Chrome](#chrome-do-mercado-livre)).

| Peça | Onde roda |
|---|---|
| PostgreSQL 18 | Docker Compose (`make db`) |
| API + automações | serviço systemd do usuário (`make servico-*`) ou `make api` |
| Chrome do Mercado Livre | na sua sessão gráfica, aberto pela API ou por `make chrome-login` |

A API não roda no Docker porque precisa abrir o Chrome na sua tela, e a porta
de depuração do Chrome só é aceita no próprio computador.

## Requisitos

- Linux com sessão gráfica (testado no Ubuntu com GNOME)
- Python 3.11+, `make`, Docker com Compose
- Google Chrome ou Chromium
- `pg_dump` (só para `make db-importar`)

## Primeira instalação

```bash
make instalar          # cria o .venv, instala as dependências e o .env
# edite o .env: POSTGRES_SENHA, DATABASE_URL e CREDENTIAL_ENCRYPTION_KEY
make db                # sobe o PostgreSQL no Docker
make migrar            # cria as tabelas
make chrome-login      # abre o Chrome do projeto: faça login no Mercado Livre
make chrome-verificar  # confere se a sessão ficou salva
make servico-instalar  # instala a API como serviço
make servico-iniciar   # liga a API e as automações
```

Documentação interativa da API: <http://127.0.0.1:8000/docs>

> **Atenção:** `make servico-iniciar`, `make subir` e `make api` ligam as
> automações. Se `automacoes_ativas` estiver ligado no banco, a API começa a
> coletar e a **publicar nos grupos**. Para subir sem publicar, pause antes:
> `POST /configuracoes-sistema/automacoes/pausar`.

### Já tinha um banco local?

```bash
make db
make db-importar ORIGEM=postgresql://usuario:senha@localhost:5433/plataformas_ofertas
# depois aponte a DATABASE_URL do .env para a porta do Docker (5434)
```

O banco do Docker precisa estar vazio. Para recomeçar do zero:
`docker compose down -v` (**apaga os dados do Docker**).

## Comandos do dia a dia

Rode `make` para ver todos. Os principais:

| Comando | O que faz |
|---|---|
| `make subir` | sobe o banco, aplica as migrações e inicia a API |
| `make parar` | para a API e o banco |
| `make status` | estado do banco, da API e do Chrome |
| `make servico-logs` | acompanha os logs da API (coletas, publicações, erros) |
| `make servico-reiniciar` | reinicia a API (use depois de atualizar o código) |
| `make api` | API em modo desenvolvimento, recarregando ao salvar |
| `make testes` | roda os testes; os de integração usam o banco, sem gravar nada |
| `make db-backup` | salva um backup em `backups/` |
| `make db-psql` | abre o `psql` no banco |

### Sobre o serviço

- É um serviço systemd **do usuário**, iniciado junto com a sessão gráfica
  (login no desktop) e parado no logout. Isso é necessário porque o Chrome do
  Mercado Livre precisa da tela.
- Roda **um único processo**. As automações vivem dentro da API, então não use
  `--workers`: cada worker rodaria as automações de novo.
- Ao parar, interrompe os ciclos de publicação entre um envio e outro. Uma
  coleta em andamento tem até 3 minutos para terminar. Ciclos cortados no meio
  ficam como `interrompido`.
- O Chrome do Mercado Livre continua aberto quando o serviço para ou reinicia
  (a sessão é preservada).

## Painel de administração

Interface web em `frontend/` (React + TypeScript), no mesmo repositório da API.
Cobre todas as rotas: status geral, coleta manual, produtos e publicação manual,
histórico de ciclos, categorias, grupos e suas regras, automações e janelas,
lojas, canais e credenciais.

```bash
make painel-instalar   # uma vez: instala as dependências (Node 20+)
make painel-build      # compila; a API passa a servir em http://127.0.0.1:8000/painel
make painel            # desenvolvimento: http://127.0.0.1:5173/painel/ (recarrega ao salvar)
make painel-tipos      # depois de mudar rotas da API: regenera os tipos TypeScript
```

### Login

O painel e a API exigem login; a página inicial é `/painel/login` e, depois de
entrar, abre o painel. Crie o administrador master uma vez (a senha é pedida no
terminal e guardada só como hash scrypt):

```bash
make usuario-admin                 # login "admin"; ou: make usuario-admin LOGIN=outro
make usuario-senha LOGIN=admin     # troca a senha (derruba as sessões abertas)
```

Os demais usuários são criados no próprio painel, em **Usuários** (só para
admin): perfil `admin` (tudo) ou `operador` (usa o painel, sem gerenciar
usuários). Cada um troca a própria senha em **Minha conta** (clique no nome, no
rodapé do menu).

A sessão é um token assinado com a `CREDENTIAL_ENCRYPTION_KEY` e vale
`SESSAO_DURACAO_HORAS` (padrão 12h). Sem login ficam só `/health`, `/painel`
(a tela de login) e o OAuth do Mercado Livre. Mesmo com login, mantenha a API
acessível só pela própria máquina até a revisão de segurança (Etapa 6).

## Backup

```bash
make db-backup        # agora: backups/AAAA-MM-DD_HHMM.sql.gz (guarda os 14 últimos)
make backup-agendar   # todo dia às 12:30; se o PC estava desligado, roda ao abrir a sessão
```

O backup traz as credenciais **criptografadas**: sem a `CREDENTIAL_ENCRYPTION_KEY`
do `.env` elas não podem ser lidas. Guarde uma cópia do `.env` fora do computador
(ex.: num gerenciador de senhas).

## Configuração (`.env`)

| Variável | Obrigatória | Padrão | Uso |
|---|---|---|---|
| `DATABASE_URL` | sim | — | conexão da API (`postgresql+psycopg://usuario:senha@localhost:5434/banco`) |
| `CREDENTIAL_ENCRYPTION_KEY` | sim | — | chave Fernet que criptografa as credenciais no banco. **Se for perdida, as credenciais salvas não podem mais ser lidas.** |
| `DESCONTO_MAXIMO_PERCENTUAL` | não | `90` | desconto acima disto é tratado como preço "de" inflado e o produto não é publicado |
| `SESSAO_DURACAO_HORAS` | não | `12` | duração do login no painel |
| `POSTGRES_USUARIO` | não | `ofertas_app` | usuário do PostgreSQL no Docker |
| `POSTGRES_SENHA` | sim (Docker) | — | senha do PostgreSQL no Docker |
| `POSTGRES_BANCO` | não | `plataformas_ofertas` | nome do banco no Docker |
| `POSTGRES_PORTA` | não | `5434` | porta local do PostgreSQL no Docker |
| `MERCADO_LIVRE_CHROME_PROFILE_DIR` | não | `data/chrome_profile` | perfil do Chrome do projeto (relativo à raiz) |
| `MERCADO_LIVRE_CHROME_PATH` | não | detectado | executável do Chrome |
| `MERCADO_LIVRE_CHROME_CDP_URL` | não | `http://127.0.0.1:9222` | porta de depuração do Chrome (só local) |
| `WHATSAPP_CHROME_PROFILE_DIR` | não | `data/whatsapp_profile` | perfil do Chrome do WhatsApp |
| `WHATSAPP_CHROME_CDP_URL` | não | `http://127.0.0.1:9223` | porta de depuração do Chrome do WhatsApp |
| `WHATSAPP_INTERVALO_MINIMO_SEGUNDOS` | não | `120` | intervalo entre mensagens no WhatsApp (mín. 60) |
| `WHATSAPP_LIMITE_DIARIO` | não | `30` | mensagens por dia no WhatsApp |
| `LOG_LEVEL` | não | `INFO` | nível dos logs |

Para gerar a chave de criptografia:
`.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

O host e a porta da API ficam no Makefile (`API_HOST=127.0.0.1`,
`API_PORTA=8000`). A API **não tem autenticação**: mantenha-a acessível só pela
própria máquina.

As configurações que mudam com o sistema rodando ficam no banco e são
alteradas pela API: intervalos, limite por categoria, janelas, regras por grupo
e ligar/pausar automações.

## Chrome do Mercado Livre

O projeto usa um **perfil próprio** do Chrome em `data/chrome_profile`
(fora do git), separado do seu Chrome pessoal. O login é feito uma vez:

```bash
make chrome-login      # abre o Chrome do projeto; faça login na conta de afiliado
make chrome-verificar  # "Sessão autenticada" = pronto
```

Se a pasta for apagada ou a sessão expirar, a geração de links do Mercado Livre
falha (`MercadoLivreLoginRequiredError`). Basta repetir o `make chrome-login`.
Não copie o perfil entre computadores: faça o login em cada um.

## WhatsApp (WhatsApp Web, não oficial)

> **Risco:** controlar o WhatsApp Web por automação viola os termos do
> WhatsApp e o número pode ser **restringido ou banido**. Use um número que
> você aceite perder e só em grupos seus, cujos participantes aceitaram
> receber ofertas.

Como o Mercado Livre, usa um Chrome com perfil próprio (`data/whatsapp_profile`,
porta 9223), logado uma vez por QR Code. O grupo é identificado pelo **nome
exato** do grupo no WhatsApp, e não precisa de credencial.

```bash
make whatsapp-login                      # abre o Chrome; leia o QR Code no celular
make whatsapp-verificar                  # "Sessão conectada" = pronto
make whatsapp-teste GRUPO="Nome do grupo"            # digita a mensagem SEM enviar
make whatsapp-teste GRUPO="Nome do grupo" ENVIAR=1   # envia uma mensagem de teste
```

Cadastre o grupo em `POST /grupos` (canal `whatsapp`, `identificador_destino` =
nome do grupo), crie a configuração em `POST /grupos/{id}/configuracao`, associe
as categorias em `POST /categorias/{id}/grupos/{grupo_id}` e ligue com
`POST /configuracoes-sistema/automacoes/publicacao_whatsapp/ativar`.

Proteções (comportamento conservador, sem disfarçar a automação):

| Proteção | Padrão |
|---|---|
| Intervalo mínimo entre quaisquer duas mensagens, somando todos os grupos | `WHATSAPP_INTERVALO_MINIMO_SEGUNDOS=120` (mínimo 60) |
| Limite diário, somando todos os grupos | `WHATSAPP_LIMITE_DIARIO=30` |
| Um envio por vez | sempre |
| Só dentro das janelas de execução | sempre |
| Confere o nome do grupo aberto antes de enviar | sempre |
| Pausa automática se a sessão cair (QR Code) ou a conta for restringida | `publicacao_whatsapp_ativa` vira `false` e o log mostra o motivo |

Recomendações: comece com um limite baixo (ex.: 10 por dia na primeira semana),
use um número com histórico de uso normal, seja administrador dos grupos, não
adicione pessoas sem consentimento e mantenha o celular conectado à internet.

## Rotas da API

Lista completa com exemplos em `/docs`. Visão geral:

| Recurso | Rotas |
|---|---|
| Lojas de origem | `GET/POST /lojas`, `GET /lojas/{codigo}`, `PATCH /lojas/{codigo}/status` |
| Credenciais das lojas | `/credenciais-plataforma` (uma ativa por tipo e loja) |
| Autorização do Mercado Livre | `GET /oauth/mercado-livre/autorizar` → `callback` |
| Categorias | `GET/POST /categorias`, `PATCH /categorias/{id}/status`, `/desconto-minimo`, `/etiqueta-afiliado` |
| Grupos da categoria | `GET /categorias/{id}/grupos`, `POST/DELETE /categorias/{id}/grupos/{grupo_id}` |
| Canais (Telegram, WhatsApp) | `GET/POST /canais-divulgacao`, `PATCH /canais-divulgacao/{codigo}/status` |
| Credenciais dos canais | `/credenciais-divulgacao` (ex.: token do bot) |
| Grupos | `GET/POST /grupos`, `GET /grupos/{grupo_id}`, `PATCH /grupos/{grupo_id}/status` |
| Regras do grupo | `GET /grupos/configuracoes`, `GET/POST/PATCH /grupos/{grupo_id}/configuracao` |
| Produtos | `GET/POST /produtos`, `GET/PATCH /produtos/{id}`, `PATCH /produtos/{id}/monitoramento` |
| Coleta manual | `POST /coletas/mercado-livre`, `POST /coletas/shopee` |
| Publicação manual | `POST /publicacoes/produtos/{id}` (todos os grupos da categoria), `POST /publicacoes/produtos/{id}/grupos/{grupo_id}` |
| Configurações globais | `GET/PATCH /configuracoes-sistema`, `POST /configuracoes-sistema/automacoes/{ativar\|pausar}`, `POST /configuracoes-sistema/automacoes/{automacao}/{ativar\|pausar}` |
| Janelas de execução | `GET/POST /janelas-execucao`, `GET/PATCH/DELETE /janelas-execucao/{id}` |
| Monitoramento | `GET /automacoes/status`, `GET /ciclos-publicacao` |
| Saúde | `GET /health` |

Códigos de erro: `404` recurso não encontrado, `409` regra de negócio violada,
`422` dados inválidos, `502` falha no envio ao Telegram ou na comunicação com a
loja.

## Problemas comuns

| Sintoma | Causa e solução |
|---|---|
| Coleta da Shopee como `parcial` | a Shopee devolve `error [10000]` de forma intermitente; o cliente tenta de novo 3 vezes. Se for frequente, aumente o intervalo de coleta. |
| Avisos `USER_PRODUCT` na coleta do Mercado Livre | esse tipo de anúncio ainda não é suportado e é ignorado. Não é um erro. |
| Links do Mercado Livre com `erro` | sessão do Chrome expirada: `make chrome-verificar` e, se preciso, `make chrome-login`. |
| `401` do Mercado Livre na coleta | autorização OAuth expirada: abra `/oauth/mercado-livre/autorizar`. |
| `monitor_offline` em `/automacoes/status` | a API não está rodando (`make servico-status`). |
| Nada é publicado | confira `/automacoes/status`: automações pausadas, `fora_da_janela` ou grupo sem configuração. |

## Desenvolvimento

- Camadas: `api/` → `services/` → `repositories/` → `models/`; integrações em
  `collectors/`, `affiliates/` e `publishers/`.
- Migrações com Alembic: `alembic revision --autogenerate -m "..."` e revise o
  arquivo gerado.
- Testes com pytest. Os de integração rodam no banco do `.env` dentro de uma
  transação desfeita ao final e não iniciam as automações.

## Licença

MIT. Veja [LICENSE](LICENSE).
