# Drogarias Max — Sistema de Gestão

Plataforma completa para a rede **Drogarias Max** (Rio de Janeiro): loja online para clientes, painel operacional para funcionários, painel admin completo e um swarm de agentes IA para leitura e análise do ERP.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontends                            │
│                                                             │
│  :5173 Loja Cliente   :5174 Gestor (Vite)  :3001 Admin MUI │
│  React + Tailwind      React + Tailwind     React + MUI v7  │
└──────────────────┬──────────────┬───────────────┬──────────┘
                   │              │               │
                   └──────────────┼───────────────┘
                                  │ /api/*
                      ┌───────────▼───────────┐
                      │   FastAPI  :8080       │
                      │   JWT · SQLite         │
                      │   src/api/             │
                      └───────────┬───────────┘
                                  │
                      ┌───────────▼───────────┐
                      │   Agentes IA (Python)  │
                      │   Relatórios · Chat    │
                      │   src/agents/          │
                      └───────────────────────┘
```

---

## Pré-requisitos

- Python 3.11+
- Node 18+
- `pip install -r requirements.txt`

---

## Início rápido

```bash
# 1. Criar banco demo
python scripts/seed_demo_db.py

# 2. Subir a API
uvicorn src.api.main:app --port 8080 --reload

# 3. Loja do cliente  (nova aba)
cd frontend/cliente && npm install && npm run dev        # :5173

# 4. Painel gestor    (nova aba)
cd frontend/gestor  && npm install && npm run dev        # :5174

# 5. Admin MUI        (nova aba)
cd farmacia-frontend && npm install && PORT=3001 npm start  # :3001
```

Acesse **http://localhost:5173** para a loja e **http://localhost:5174** para o painel.

---

## Serviços

| Serviço | URL | Descrição |
|---|---|---|
| API | http://localhost:8080/api/docs | FastAPI + Swagger UI |
| Loja cliente | http://localhost:5173 | E-commerce público |
| Painel gestor | http://localhost:5174 | Operacional (pedidos, estoque, chat) |
| Admin MUI | http://localhost:3001 | Painel completo com DataGrid |
| Chat webhook | http://localhost:8000/webhook | Integração WhatsApp |
| WebSocket | ws://localhost:8765 | Atualizações ao vivo do relatório |

---

## Credenciais demo

| Perfil | Usuário | Senha | Acesso |
|---|---|---|---|
| Gestor | `gestor` | `farmacia123` | Tudo |
| Funcionário | `funcionario` | `farmacia456` | Pedidos, produtos, atendimentos |

---

## Estrutura do projeto

```
farmacia-pedro/
├── src/
│   ├── api/               # FastAPI
│   │   ├── main.py        # App + CORS
│   │   ├── auth.py        # JWT (access + refresh)
│   │   ├── models.py      # Pydantic schemas
│   │   ├── deps.py        # Dependências (get_current_user)
│   │   └── routers/       # auth · products · orders · chat
│   │                      # customers · dashboard · reports · users
│   ├── agents/            # Swarm de leitura do ERP
│   │   ├── operational.py # Estoque baixo + pedidos recentes
│   │   ├── inbound_audit.py # Margens negativas em notas
│   │   ├── strategist.py  # Análise de concorrentes
│   │   ├── inventory.py   # Dead stock + sugestões de reposição
│   │   └── executor_stub.py # Escrita desabilitada (exige aprovação)
│   ├── chat/              # Atendimento via WhatsApp
│   │   ├── flow_atendimento.py # Máquina de estados do chat
│   │   ├── data.py        # DataGateway (SQLite / MySQL stub)
│   │   ├── state.py       # Sessões persistidas em JSONL
│   │   └── integration.py # LocalAdapter / WebhookAdapter
│   ├── automation/
│   │   └── flow.py        # Pipeline de automação (once / schedule)
│   ├── runner.py          # Orquestra os 5 agentes em sequência
│   └── core/
│       ├── config.py      # Settings (dataclass + .env)
│       └── db.py          # get_conn() — context manager SQLite
│
├── frontend/
│   ├── cliente/           # React 18 + Vite + Tailwind  (:5173)
│   │   └── src/
│   │       ├── pages/     # Home · Catalog · Chat · Login · Register · Profile
│   │       └── components/ # Navbar · Footer · ProductCard · Button · Badge
│   └── gestor/            # React 18 + Vite + Tailwind  (:5174)
│       └── src/
│           ├── pages/     # Dashboard · Orders · Products · Reports
│           │              # Users · ChatSessions · Login
│           └── components/ # Layout · ProtectedRoute
│
├── farmacia-frontend/     # React 19 + TypeScript + MUI v7  (:3001)
│   └── src/
│       ├── pages/         # Dashboard · Pedidos · Carrinhos · Clientes
│       │                  # Relatorios · Notificacoes · Configuracoes · Ajuda
│       ├── theme/
│       │   └── maxTheme.ts # Tema MUI com paleta Drogarias Max
│       └── Layout.tsx     # AppBar + Drawer lateral
│
├── scripts/
│   ├── seed_demo_db.py    # Cria e popula data/erp_demo.db
│   ├── run_demo.py        # Executa o swarm e grava out/report.*
│   ├── automation.py      # Modo once ou schedule (AUTOMATION_MODE)
│   ├── chat_cli.py        # Chat interativo no terminal
│   ├── chat_webhook.py    # Servidor HTTP do chat (:8000)
│   ├── ws_server.py       # WebSocket de relatórios ao vivo (:8765)
│   └── smoke_test.py      # Teste rápido de sanidade
│
├── data/
│   └── erp_demo.db        # SQLite (criado pelo seed)
├── out/                   # Saídas dos agentes
│   ├── report.json
│   ├── report.md
│   └── audit_log.jsonl
└── tests/                 # pytest
```

---

## API — Principais rotas

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/login` | Login (retorna JWT) |
| POST | `/api/auth/refresh` | Renovar token |
| GET | `/api/products` | Listar produtos (`?q=&category=`) |
| GET | `/api/orders` | Pedidos internos |
| PATCH | `/api/orders/{id}/status` | Atualizar status do pedido |
| POST | `/api/chat/message` | Enviar mensagem ao chat IA |
| GET | `/api/dashboard/stats` | KPIs do dashboard |
| GET | `/api/customers` | Clientes cadastrados |
| GET | `/api/reports` | Relatórios gerados |

Documentação interativa: **http://localhost:8080/api/docs**

---

## Swarm de agentes (leitura do ERP)

```bash
# Rodar uma vez
python scripts/run_demo.py

# Rodar em loop (a cada N minutos)
AUTOMATION_MODE=schedule AUTOMATION_INTERVAL_MIN=30 python scripts/automation.py
```

Os cinco agentes rodam em sequência sobre o SQLite e gravam `out/report.json` + `out/report.md`. A camada de escrita (`executor_stub`) está **desabilitada** — qualquer mutação exige aprovação explícita via WhatsApp.

---

## Chat IA (atendimento ao cliente)

Máquina de estados que guia o cliente do produto até a confirmação do pedido:

```
START → ASK_PRODUCT_CHOICE → ASK_VARIANT → ASK_QTY
      → OUT_OF_STOCK / ASK_FULFILLMENT
      → PICKUP_CONFIRM / DELIVERY_ADDRESS → DELIVERY_DETAILS
      → ASK_CLIENT_NAME → ASK_CONTACT_PERMISSION → DONE
```

```bash
# Terminal interativo
python scripts/chat_cli.py

# Via HTTP
python scripts/chat_webhook.py
curl -X POST http://localhost:8000/webhook \
     -H "Content-Type: application/json" \
     -d '{"from":"cliente1","text":"Tem dipirona?"}'
```

---

## Design system (Drogarias Max)

Tokens aplicados nos três frontends via Tailwind e MUI theme:

| Token | Cor | Uso |
|---|---|---|
| `primary-600` / `--max-blue` | `#0033A0` | Marca, header, botões secundários |
| `max-red` / `--max-red` | `#E30613` | Preços, CTAs de compra, ofertas |
| `max-yellow` / `--max-yellow` | `#FFD200` | Badges de desconto |
| `whatsapp` | `#25D366` | Botão WhatsApp |

Fonte: **Poppins** (400 / 600 / 700 / 800 / 900).

Arquivos de configuração:
- `frontend/cliente/tailwind.config.js`
- `frontend/gestor/tailwind.config.js`
- `farmacia-frontend/src/theme/maxTheme.ts`

---

## Variáveis de ambiente (`.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `ERP_DB_PATH` | `data/erp_demo.db` | Caminho do SQLite |
| `REPORT_DIR` | `out` | Pasta de saída dos relatórios |
| `AUTOMATION_MODE` | `once` | `once` ou `schedule` |
| `AUTOMATION_INTERVAL_MIN` | `60` | Intervalo em minutos (modo schedule) |
| `AUTOMATION_SEED_DEMO` | `false` | Criar banco demo automaticamente |
| `CHAT_LOJA_NOME` | `Drogarias Max - Barra Blue` | Nome da loja no chat |
| `CHAT_DELIVERY_RULES` | — | `Bairro:taxa:prazo;...` |
| `OPERATIONAL_SCOPES` | — | `stock,orders` (habilita escopos dos agentes) |
| `WHATSAPP_WEBHOOK_URL` | — | Envia relatório ao WhatsApp (vazio = desabilitado) |
| `INTEGRATION_ADAPTER` | `local` | `local`, `webhook` ou `modulo:Classe` |
| `GROQ_API_KEY` | — | Chave para o modelo de chat |
| `CHAT_MODEL` | — | Ex: `llama-3.3-70b-versatile` |

---

## Testes

```bash
pytest                                                 # todos
pytest tests/test_agents.py::test_operational_returns_expected_keys
```

---

## Docker

```bash
docker build -t drogarias-max .
docker run -p 8080:8080 drogarias-max
```

O Dockerfile semeia o banco demo em build time e executa `scripts/run_demo.py` por padrão.
