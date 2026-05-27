# Sistema Logístico de Entregas — Design Spec
**Data:** 2026-05-27  
**Projeto:** Drogarias Max — farmacia-pedro  
**Escopo:** Monitoramento interno de entregadores + tracking estilo iFood para o cliente

---

## Visão Geral

Sistema logístico completo em três camadas:
1. **Painel interno** (`out/admin/delivery.html`) — equipe monitora entregadores em tempo real
2. **App do entregador** (`out/driver/index.html`) — web mobile para o entregador enviar GPS e confirmar entregas
3. **Tracking do cliente** (`out/track/index.html`) — página pública por pedido, estilo iFood, com mapa Leaflet

Toda comunicação em tempo real via WebSocket (porta 8766). Sem polling. Sem WhatsApp. Sem APIs externas pagas.

---

## 1. Modelo de Dados

Três novas tabelas SQLite, acessadas via `src/core/db.py:get_conn()`.

```sql
CREATE TABLE drivers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    pin_hash    TEXT NOT NULL,            -- bcrypt do PIN de 6 dígitos
    photo_path  TEXT,                     -- ex: out/uploads/drivers/3.jpg
    status      TEXT DEFAULT 'available', -- available | on_route | paused | offline
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE driver_locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id   INTEGER NOT NULL REFERENCES drivers(id),
    order_id    INTEGER,                  -- NULL se fora de entrega ativa
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    recorded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE delivery_assignments (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id         INTEGER NOT NULL REFERENCES drivers(id),
    order_id          INTEGER NOT NULL REFERENCES orders(id),
    status            TEXT DEFAULT 'assigned', -- assigned | in_progress | completed | cancelled
    tracking_token    TEXT NOT NULL UNIQUE,    -- UUID gerado na atribuição
    eta_minutes       INTEGER,                 -- calculado no momento da atribuição
    dest_lat          REAL,                    -- coordenadas do destino (informadas pelo operador)
    dest_lon          REAL,
    assigned_at       TEXT DEFAULT (datetime('now')),
    started_at        TEXT,
    completed_at      TEXT,
    stopped_alert_min INTEGER DEFAULT 5        -- limiar de alerta configurado pelo gestor
);

-- Configurações globais editáveis pelo gestor
CREATE TABLE delivery_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- Valores iniciais: avg_speed_kmh=30, stopped_alert_min=5
```

**Decisões:**
- `pin_hash` usa bcrypt (já em `requirements.txt`)
- `tracking_token` é UUID4 — o cliente acessa `/track/{order_id}?token=xxx`
- `driver_locations` acumula trail completo; posição atual = registro mais recente por `driver_id`
- `dest_lat`/`dest_lon` informados pelo operador ao atribuir (sem geocoding externo)
- `stopped_alert_min` na assignment permite ajuste por entrega; default vem de `delivery_settings`

---

## 2. Arquitetura do Backend

### `src/delivery/`

```
src/delivery/
├── models.py   — dataclasses: Driver, DriverLocation, DeliveryAssignment, TrackingState
├── tracker.py  — estado em memória: posições atuais, conexões WS, broadcast, detecção de parada
├── eta.py      — distância Haversine + ETA por velocidade média configurável
└── auth.py     — verificação de PIN (bcrypt), geração/validação de tracking token (UUID4)
```

### `scripts/delivery_server.py` — FastAPI, porta 8001

Processo único gerencia HTTP REST + WebSocket no mesmo loop asyncio.

**Rotas REST:**

| Método | Rota | Roles | Descrição |
|--------|------|-------|-----------|
| POST | `/api/drivers` | gestor | Cadastro com upload de foto (multipart) |
| GET | `/api/drivers` | gestor, funcionario | Lista entregadores com status atual |
| POST | `/api/drivers/{id}/assign/{order_id}` | gestor, funcionario | Atribui pedido ao entregador |
| POST | `/driver/login` | — | driver_id + PIN → JWT de curta duração |
| POST | `/driver/location` | driver JWT | `{driver_id, lat, lon, order_id}` → grava + broadcast |
| POST | `/driver/order/{order_id}/complete` | driver JWT | Marca entregue + broadcast estado final |
| GET | `/track/{order_id}` | — (token) | Estado atual do pedido (valida token por query param) |
| GET | `/driver/status/{driver_id}` | gestor, funcionario | Estado atual do entregador |
| GET | `/api/settings/delivery` | gestor | Lê configurações globais |
| PATCH | `/api/settings/delivery` | gestor | Salva configurações (alert_min, avg_speed_kmh) |

**WebSocket:**

| Endpoint | Quem conecta | Autenticação |
|----------|-------------|--------------|
| `ws://host:8766/ws/driver/{driver_id}` | Painel interno | JWT gestor/funcionario (header ou query param) |
| `ws://host:8766/ws/order/{order_id}` | Página de tracking do cliente | `?token=xxx` (tracking token) |

### `tracker.py` — núcleo do estado em memória

- `Dict[driver_id, DriverLocation]` — posição mais recente de cada entregador
- `Dict[channel, Set[WebSocket]]` — conexões abertas por canal
- `broadcast(channel, payload)` — envia JSON para todos os clientes do canal
- Detecção de parada: ao receber nova localização, compara `recorded_at` da anterior; se delta > `stopped_alert_min`, emite `driver_stopped_alert` no canal `driver:{id}`

---

## 3. Protocolo WebSocket

### Canal `ws/driver/{driver_id}` — painel interno

```jsonc
{ "type": "location_update", "driver_id": 3, "lat": -22.9068, "lon": -43.1729,
  "order_id": 1042, "eta_minutes": 7, "recorded_at": "2026-05-27T14:22:00" }

{ "type": "driver_stopped_alert", "driver_id": 3, "stopped_minutes": 6,
  "lat": -22.9068, "lon": -43.1729 }

{ "type": "delivery_completed", "driver_id": 3, "order_id": 1042,
  "completed_at": "2026-05-27T14:31:00" }

{ "type": "driver_status_changed", "driver_id": 3, "status": "available" }
```

### Canal `ws/order/{order_id}` — tracking do cliente

```jsonc
{ "type": "location_update", "lat": -22.9068, "lon": -43.1729,
  "eta_minutes": 7, "distance_km": 1.1 }

{ "type": "order_status_changed", "status": "out_for_delivery",
  "driver_name": "João Delivery", "driver_photo": "/uploads/drivers/3.jpg" }

{ "type": "delivery_completed", "completed_at": "2026-05-27T14:31:00" }
```

**Privacidade:** canal do cliente nunca expõe `driver_id` nem dados internos.

**Reconexão (cliente):** backoff exponencial 1s → 2s → 4s → max 30s.

---

## 4. Frontends Estáticos

HTML + CSS + JS vanilla + Leaflet.js (CDN). Sem build step.

### `out/track/index.html` — tracking do cliente

- Layout: timeline vertical de status (iFood) no topo, mapa Leaflet mini (≈30% da tela) abaixo
- Estados exibidos: `confirmed` → `preparing` → `out_for_delivery` → `delivered`
- Durante `out_for_delivery`: foto + nome do entregador, ETA dinâmico, pin móvel no mapa
- Web Notifications API: pede permissão no primeiro load; notifica a cada `order_status_changed`
- Reconexão WS automática com backoff

### `out/driver/index.html` — app do entregador

- Tema dark, botões grandes (fácil uso ao sol / luvas)
- Tela 1 — Login: `driver_id` + PIN 6 dígitos → JWT em `sessionStorage`
- Tela 2 — Em espera: mostra status `available`; botão "Iniciar Rota" habilitado só quando pedido atribuído
- Tela 3 — Entrega ativa: endereço, ETA, indicador GPS ativo; botão "CONFIRMAR ENTREGA" (grande, verde); botão "Encerrar Rota" (pequeno, vermelho)
- `navigator.geolocation.watchPosition()` com intervalo mínimo de 10s → POST `/driver/location`
- Sem service worker — intencionalmente simples

### `out/admin/delivery.html` — painel interno

- Layout: mapa Leaflet central (70%) + sidebar de entregadores (30%)
- Mapa: pin colorido por status (verde = on_route, amarelo = parado, vermelho = atrasado)
- Sidebar: cards por entregador com status, pedido ativo, ETA, alertas
- Campo configurável de alerta de parada (editável pelo gestor) → PATCH `/api/settings/delivery`
- Atribuição: dropdown de pedidos pendentes + dropdown de entregadores disponíveis (gestor e funcionário)
- Cadastro de entregador: formulário com upload de foto (multipart)

---

## 5. ETA

```python
# src/delivery/eta.py

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distância em km entre dois pontos via fórmula de Haversine."""
    ...

def calc_eta(driver_lat, driver_lon, dest_lat, dest_lon, avg_speed_kmh=30) -> tuple[float, int]:
    """Retorna (distance_km, eta_minutes)."""
    distance_km = haversine(driver_lat, driver_lon, dest_lat, dest_lon)
    eta_minutes = ceil((distance_km / avg_speed_kmh) * 60)
    return distance_km, eta_minutes
```

- `avg_speed_kmh` lido de `delivery_settings` (padrão 30 km/h), editável pelo gestor
- Recalculado a cada `POST /driver/location`
- ETA é estimativa em linha reta — sem routing externo, adequado para entregas urbanas locais

---

## 6. Testes — `tests/test_delivery.py`

Todos usam SQLite `:memory:` via `get_conn()` com fixture de setup. Sem mock.

| Teste | Verifica |
|-------|---------|
| `test_assign_order` | Atribuição cria registro em `delivery_assignments` + `tracking_token` único gerado |
| `test_location_update` | POST `/driver/location` grava em `driver_locations` + ETA recalculado + distância retornada |
| `test_status_change` | Completar entrega → assignment `completed` + driver volta a `available` |
| `test_eta_calculation` | `haversine()` retorna valor correto para par conhecido; ETA bate com velocidade padrão |

---

## 7. Entregáveis

```
src/delivery/
├── models.py
├── tracker.py
├── eta.py
└── auth.py

scripts/
├── delivery_server.py        — HTTP (8001) + WS (8766)
└── seed_delivery_demo.py     — 3 entregadores demo + 2 atribuições ativas

out/
├── track/index.html          — tracking do cliente
├── driver/index.html         — app do entregador
├── admin/delivery.html       — painel interno
└── uploads/drivers/          — fotos dos entregadores

tests/
└── test_delivery.py

CLAUDE.md                     — atualizado com novos comandos e env vars
```

---

## 8. Configuração

Novas variáveis de ambiente:

| Var | Padrão | Descrição |
|-----|--------|-----------|
| `DELIVERY_PORT` | `8001` | Porta do delivery_server |
| `DELIVERY_WS_PORT` | `8766` | Porta do WebSocket |
| `DELIVERY_AVG_SPEED_KMH` | `30` | Velocidade média para ETA (seed inicial do DB) |
| `DELIVERY_STOPPED_ALERT_MIN` | `5` | Limiar padrão de parada (seed inicial do DB) |
| `DELIVERY_UPLOAD_DIR` | `out/uploads/drivers` | Diretório de fotos dos entregadores |

---

## 9. Autenticação entre servidores

`delivery_server.py` (porta 8001) precisa validar JWTs emitidos pelo servidor principal (porta 8080) para as rotas acessadas por gestor/funcionário.

**Solução:** ambos os servidores leem a mesma variável `JWT_SECRET_KEY`. O `delivery_server.py` importa `src.api.auth.verify_token()` diretamente — sem duplicação de lógica JWT.

- Tokens de gestor/funcionário (emitidos pelo servidor 8080) são validados no servidor 8001 via `verify_token()`
- Tokens de driver são emitidos pelo próprio `delivery_server.py` com o mesmo secret, mas claim `role: driver` — distintos dos tokens de usuário
- `src/delivery/auth.py` expõe `verify_driver_token()` para as rotas do app do entregador

---

## 10. Compatibilidade

- Toda leitura/escrita no banco via `src/core/db.py:get_conn()` — sem acesso direto ao SQLite
- Nenhuma rota do servidor existente (porta 8080) é modificada
- `requirements.txt`: todas as dependências já presentes (`fastapi`, `uvicorn`, `passlib[bcrypt]`, `python-multipart`, `python-jose`)
