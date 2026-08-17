# FinAlly — AI Trading Workstation

## Especificación del Proyecto

## 1. Visión

FinAlly (Finance Ally) es una estación de trabajo de trading impulsada por IA, visualmente espectacular, que transmite datos de mercado en tiempo real, permite a los usuarios operar con una cartera simulada e integra un asistente de chat con LLM capaz de analizar posiciones y ejecutar operaciones en nombre del usuario. Tiene el aspecto y la sensación de una terminal Bloomberg moderna con un copiloto de IA.

Este es el proyecto final de un curso de programación con IA agéntica. Está construido íntegramente por Agentes de Programación, demostrando cómo unos agentes de IA orquestados pueden producir una aplicación full-stack de calidad de producción. Los agentes interactúan a través de archivos en `planning/`.

## 2. Experiencia de Usuario

### Primer Lanzamiento

El usuario ejecuta un único comando Docker (o un script de inicio proporcionado). Se abre un navegador en `http://localhost:8000`. Sin inicio de sesión, sin registro. Inmediatamente ve:

- Una watchlist de 10 tickers predeterminados con precios actualizándose en vivo en una cuadrícula
- $10,000 en efectivo virtual
- Una estética de terminal de trading oscura y rica en datos
- Un panel de chat de IA listo para ayudar

### Qué Puede Hacer el Usuario

- **Ver el flujo de precios en directo** — los precios destellan en verde (subida) o rojo (bajada) con sutiles animaciones CSS que se desvanecen
- **Ver mini-gráficos de tipo sparkline** — la evolución del precio junto a cada ticker en la watchlist, acumulada en el frontend a partir del stream SSE desde la carga de la página (los sparklines se completan progresivamente)
- **Hacer clic en un ticker** para ver un gráfico más grande y detallado en el área principal de gráficos
- **Comprar y vender acciones** — solo órdenes de mercado, ejecución instantánea al precio actual, sin comisiones, sin diálogo de confirmación
- **Monitorizar su cartera** — un mapa de calor (treemap) que muestra las posiciones dimensionadas por peso y coloreadas por P&L, además de un gráfico de P&L que sigue el valor total de la cartera a lo largo del tiempo
- **Ver una tabla de posiciones** — ticker, cantidad, coste medio, precio actual, P&L no realizado, % de cambio
- **Chatear con el asistente de IA** — preguntar sobre su cartera, obtener análisis y hacer que la IA ejecute operaciones y gestione la watchlist mediante lenguaje natural
- **Gestionar la watchlist** — añadir/eliminar tickers manualmente o a través del chat de IA

### Diseño Visual

- **Tema oscuro**: fondos en torno a `#0d1117` o `#1a1a2e`, bordes grises apagados, sin negro puro
- **Animaciones de destello de precio**: breve resalte de fondo verde/rojo al cambiar el precio, desapareciendo en ~500ms mediante transiciones CSS
- **Indicador de estado de conexión**: un pequeño punto de color (verde = conectado, amarillo = reconectando, rojo = desconectado) visible en el encabezado
- **Diseño profesional y denso en datos**: inspirado en terminales Bloomberg/de trading — cada píxel cumple una función
- **Pensado primero para escritorio**: optimizado para pantallas anchas; no es objetivo dar soporte a tablet/móvil en esta fase

### Esquema de Colores
- Amarillo de Acento: `#ecad0a`
- Azul Primario: `#209dd7`
- Púrpura Secundario: `#753991` (botones de envío)
- Verde (subida de precio / beneficio): `#16c784`
- Rojo (bajada de precio / pérdida): `#ea3943`

## 3. Visión General de la Arquitectura

### Contenedor Único, Puerto Único

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js con TypeScript, compilado como exportación estática (`output: 'export'`), servido por FastAPI como archivos estáticos
- **Backend**: FastAPI (Python), gestionado como un proyecto `uv`
- **Base de datos**: SQLite, un único archivo en `db/finally.db`, montado como volumen para persistencia
- **Datos en tiempo real**: Server-Sent Events (SSE) — más sencillo que WebSockets, envío unidireccional servidor→cliente, funciona en cualquier entorno
- **Integración de IA**: LiteLLM → OpenRouter (Cerebras para inferencia rápida), con salidas estructuradas para la ejecución de operaciones
- **Datos de mercado**: controlados por variables de entorno — simulador por defecto, datos reales mediante la API de Massive si se proporciona una clave

### Por Qué Estas Decisiones

| Decisión | Justificación |
|---|---|
| SSE en lugar de WebSockets | Solo necesitamos envío unidireccional; más simple, sin complejidad bidireccional, soporte universal en navegadores |
| Exportación estática de Next.js | Mismo origen, sin problemas de CORS, un solo puerto, un solo contenedor, despliegue simple |
| SQLite en lugar de Postgres | Sin autenticación = sin multiusuario = sin necesidad de un servidor de base de datos; autocontenido, configuración cero |
| Contenedor Docker único | Los estudiantes ejecutan un solo comando; sin docker-compose en producción, sin orquestación de servicios |
| uv para Python | Gestión de proyectos Python rápida y moderna; lockfile reproducible; lo que los estudiantes deben aprender |
| Solo órdenes de mercado | Elimina el libro de órdenes, la lógica de órdenes limitadas y las ejecuciones parciales — matemática de cartera drásticamente más simple |

---

## 4. Estructura de Directorios

```
finally/
├── frontend/                 # Proyecto Next.js TypeScript (exportación estática)
├── backend/                  # Proyecto FastAPI uv (Python)
│   └── db/                   # Definiciones de esquema, datos semilla, lógica de migración
├── planning/                 # Documentación del proyecto para los agentes
│   ├── PLAN.md               # Este documento
│   └── ...                   # Documentos de referencia adicionales para agentes
├── scripts/
│   ├── start_mac.sh          # Inicia el contenedor Docker (macOS/Linux)
│   ├── stop_mac.sh           # Detiene el contenedor Docker (macOS/Linux)
│   ├── start_windows.ps1     # Inicia el contenedor Docker (Windows PowerShell)
│   └── stop_windows.ps1      # Detiene el contenedor Docker (Windows PowerShell)
├── test/                     # Tests E2E con Playwright + docker-compose.test.yml
├── db/                       # Bind mount del volumen (el archivo SQLite vive aquí en tiempo de ejecución)
│   └── .gitkeep              # El directorio existe en el repo; finally.db está en .gitignore
├── Dockerfile                # Build multi-etapa (Node → Python)
├── .env                      # Variables de entorno (en .gitignore, se versiona .env.example)
└── .gitignore
```

### Límites Clave

- **`frontend/`** es un proyecto Next.js autocontenido. No sabe nada de Python. Se comunica con el backend a través de los endpoints `/api/*` y los endpoints SSE `/api/stream/*`. La estructura interna queda a criterio del agente Ingeniero de Frontend.
- **`backend/`** es un proyecto uv autocontenido con su propio `pyproject.toml`. Es responsable de toda la lógica del servidor, incluyendo la inicialización de la base de datos, el esquema, los datos semilla, las rutas de la API, el streaming SSE, los datos de mercado y la integración con el LLM. La estructura interna queda a criterio de los agentes de Backend/Datos de Mercado.
- **`backend/db/`** contiene las definiciones SQL del esquema y la lógica de datos semilla. El backend inicializa la base de datos de forma diferida (lazy) — no hay paso de migración independiente ni configuración manual — pero la inicialización ocurre una única vez dentro del `lifespan` de FastAPI, antes de aceptar tráfico (no "en la primera solicitud"; ver §7 para el porqué). Crea las tablas y puebla los datos predeterminados si el archivo SQLite no existe o está vacío.
- **`db/`** en el nivel superior es el punto de montaje del volumen en tiempo de ejecución. El archivo SQLite (`db/finally.db`) es creado aquí por el backend y persiste entre reinicios del contenedor gracias al volumen Docker.
- **`planning/`** contiene la documentación de todo el proyecto, incluido este plan. Todos los agentes usan los archivos de aquí como contrato compartido.
- **`test/`** contiene los tests E2E con Playwright e infraestructura de soporte (por ejemplo, `docker-compose.test.yml`). Los tests unitarios viven dentro de `frontend/` y `backend/` respectivamente, siguiendo las convenciones de cada framework.
- **`scripts/`** contiene los scripts de inicio/parada que envuelven comandos Docker.

---

## 5. Variables de Entorno

```bash
# Obligatoria salvo que LLM_MOCK=true: clave de API de OpenRouter para la funcionalidad de chat con LLM
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Opcional: clave de API de Massive (Polygon.io) para datos de mercado reales
# Si no se establece, se usa el simulador de mercado integrado (recomendado para la mayoría de usuarios)
MASSIVE_API_KEY=

# Opcional: establecer en "true" para respuestas de LLM simuladas y deterministas (pruebas)
LLM_MOCK=false
```

### Comportamiento

- Si `MASSIVE_API_KEY` está establecida y no está vacía → el backend usa la API REST de Massive para los datos de mercado
- Si `MASSIVE_API_KEY` está ausente o vacía → el backend usa el simulador de mercado integrado
- Si `LLM_MOCK=true` → el backend devuelve respuestas de LLM simuladas y deterministas (para tests E2E), y no requiere `OPENROUTER_API_KEY`
- Si `LLM_MOCK=false` (o no está definida) → `OPENROUTER_API_KEY` es obligatoria para que el chat funcione
- El backend lee el `.env` desde la raíz del proyecto (montado en el contenedor o leído mediante `--env-file` de docker)
- El backend usa `python-dotenv` (`load_dotenv()` al inicio de `main.py`, antes de leer cualquier variable) para soportar también un flujo de desarrollo local sin Docker (`uv run uvicorn ...`). `load_dotenv()` no sobreescribe variables ya presentes en el entorno, por lo que es un no-op seguro cuando las variables ya llegan inyectadas vía `--env-file` de Docker

### Dependencias del Backend

`backend/pyproject.toml` solo declara `httpx` hoy (usado por el cliente de Massive). El resto del backend (aún por construir) debe añadir explícitamente: `fastapi`, `uvicorn[standard]`, `sse-starlette` (o el streaming SSE nativo de FastAPI), `pydantic` (≥2, para los modelos de salida estructurada del LLM, §9), `litellm` (integración con OpenRouter, §9) y `python-dotenv` (ver arriba). Ninguna de estas es opcional para que el proyecto arranque.

---

## 6. Datos de Mercado

### Dos Implementaciones, Una Interfaz

Tanto el simulador como el cliente de Massive implementan la misma interfaz abstracta. El backend selecciona cuál usar en función de la variable de entorno. Todo el código posterior (streaming SSE, caché de precios, frontend) es agnóstico respecto a la fuente.

### Simulador (Predeterminado)

- Genera precios utilizando movimiento browniano geométrico (GBM) con deriva (drift) y volatilidad configurables por ticker
- Se actualiza en intervalos de ~500ms
- Movimientos correlacionados entre tickers (por ejemplo, las acciones tecnológicas se mueven juntas)
- "Eventos" aleatorios ocasionales — movimientos súbitos del 2-5% en un ticker para dar dramatismo
- Comienza desde precios semilla realistas (por ejemplo, AAPL ~$190, GOOGL ~$175, etc.)
- Cuando se añade un ticker nuevo (no predefinido) a la watchlist, el simulador le asigna también un precio semilla realista (generado de forma plausible) y empieza a simularlo igual que a los demás
- Se ejecuta como una tarea en segundo plano dentro del propio proceso — sin dependencias externas

### API de Massive (Opcional)

- Sondeo (polling) mediante API REST (no WebSocket) — más simple, funciona en todos los niveles de suscripción
- Sondea la unión de todos los tickers vigilados en un intervalo configurable
- Nivel gratuito (5 llamadas/min): sondeo cada 15 segundos
- Niveles de pago: sondeo cada 2-15 segundos según el nivel
- Parsea la respuesta REST al mismo formato que el simulador

### Caché de Precios Compartida

- Una única tarea en segundo plano (el simulador o el poller de Massive) escribe en una caché de precios en memoria
- La caché guarda el último precio, el precio anterior y la marca de tiempo de cada ticker
- Los streams SSE leen de esta caché y envían actualizaciones a los clientes conectados
- Esta arquitectura permite futuros escenarios multiusuario sin cambios en la capa de datos

### Streaming SSE

- Endpoint: `GET /api/stream/prices`
- Conexión SSE de larga duración; el cliente usa la API nativa `EventSource`
- El servidor envía actualizaciones de precio a un ritmo regular (~500ms) para la **unión** de los tickers de la watchlist del usuario y los tickers con una posición abierta (aunque ya no estén en la watchlist) — así el P&L no realizado y el mapa de calor siempre tienen precios actualizados
- Al arrancar (`lifespan` de FastAPI), el proveedor de datos de mercado debe sembrarse con `watchlist_tickers ∪ position_tickers` (no solo la watchlist) — de lo contrario, tras un reinicio del contenedor, un ticker que solo tiene posición abierta (sin estar en watchlist) no recibiría precios hasta que algo lo vuelva a tocar
- Cada evento SSE contiene ticker, precio, precio anterior, marca de tiempo y dirección del cambio
- El cliente gestiona la reconexión automáticamente (EventSource tiene reintento incorporado)
- **Heartbeat**: el servidor envía un evento `ping` cada `HEARTBEAT_SECONDS` (15s) por la misma conexión SSE, aunque no haya cambios de precio que enviar. Permite detectar conexiones muertas y da a los tests E2E un evento predecible sobre el que verificar actividad de la conexión (§12)

### Interfaz Síncrona y Ciclo de Vida de Tickers en Tiempo de Ejecución

La interfaz abstracta `MarketDataProvider` (además de `start`, `stop`, `add_ticker`, `remove_ticker`, `tickers`) debe exponer un método síncrono `get_last_price(ticker: str) -> float | None` para poder comprobar de forma inmediata si ya existe un precio utilizable para un ticker, sin esperar al próximo ciclo del bucle en segundo plano:

- **Simulador**: `add_ticker()` debe escribir inmediatamente en la caché de precios (emitir un tick con el precio semilla recién asignado) en el mismo momento en que se registra el ticker, en vez de esperar al siguiente ciclo de ~500ms.
- **Massive**: si `add_ticker()` esperase al próximo ciclo periódico normal, un ticker nuevo podría tardar hasta el intervalo de sondeo completo (15s+ en el nivel gratuito) en tener un primer precio, lo que haría fallar sistemáticamente cualquier timeout corto en `ensure_ticker`. Para evitarlo, `MassiveMarketDataProvider.add_ticker()` dispara, además de registrar el ticker en el conjunto vigilado, un sondeo dedicado inmediato (fuera del ciclo periódico, como una tarea en segundo plano) que consulta solo ese ticker y escribe su primer precio (y `session_open`) en cuanto la API responde. Gracias a esto, la operación que registra un ticker nuevo (ver `ensure_ticker` abajo) solo necesita cubrir la latencia de esa llamada de red puntual — no el intervalo de sondeo completo — por lo que un timeout explícito de 8 segundos es realista. Si expira sin resultado (símbolo inexistente, API caída), la petición que lo originó falla con `503` (ver §8), no se bloquea indefinidamente ni se acepta silenciosamente sin precio.

**`ensure_ticker(ticker)`** es la operación de dominio (a implementar en el backend, no en el proveedor) que usan tanto `POST /api/watchlist` como `POST /api/portfolio/trade` antes de responder: registra el ticker en el proveedor si aún no lo conoce (`add_ticker`), espera (con el timeout anterior) a que `get_last_price` devuelva un valor, y solo entonces continúa. El proveedor debe mantener en todo momento como conjunto vigilado `watchlist ∪ position_tickers`; cuando un ticker se elimina de la watchlist y no tiene una posición abierta, el backend llama a `provider.remove_ticker(ticker)` para que deje de simularse/sondearse sin necesidad.

### Convención de Timestamp

Todas las marcas de tiempo del proyecto (backend nuevo incluido: `trades.executed_at`, `chat_messages.created_at`, `portfolio_snapshots.recorded_at`, etc.) usan el mismo formato que ya implementa `PriceTick.create()` en el módulo de datos de mercado: `datetime.now(timezone.utc).isoformat()`, con sufijo de offset `+00:00` y precisión de microsegundos — no el sufijo `Z`. Es funcionalmente equivalente a `Z` para cualquier parser ISO-8601 (incluido `Date()` en JS/TS), y evita que convivan dos convenciones distintas en la misma base de código.

### `session_open` — Base para el "% de Cambio Diario"

La caché de precios (`CachedPrice`) y el payload de cada evento SSE incluyen, además de precio actual/anterior/timestamp, un campo `session_open: float`:

- **Simulador**: se fija en el primer tick tras el arranque del proceso (o en el momento de `add_ticker()` para tickers añadidos después) y permanece constante durante toda la vida del proceso — no hay concepto de apertura/cierre de sesión en un GBM continuo.
- **Massive**: se toma de `prevDay.c` (cierre del día anterior), ya presente en la respuesta de snapshot que el cliente parsea hoy solo como fallback de precio.
- La UI calcula "% de cambio" como `(price - session_open) / session_open` (§10) — no como `(price - previous_price) / previous_price`, que sería el cambio del último tick, no el diario.

---

## 7. Base de Datos

### SQLite con Inicialización Diferida (Lazy)

La inicialización ocurre una única vez, dentro del `lifespan` de FastAPI, **antes** de que el proceso empiece a aceptar tráfico — el mismo patrón que ya usa el módulo de datos de mercado (`ensure_db_initialized()` en `market_data_design.md` §8). No se inicializa "en la primera solicitud": dos peticiones concurrentes nada más arrancar (por ejemplo, la carga inicial de la página y la conexión SSE) nunca compiten por crear el esquema, porque el esquema ya existe cuando el servidor empieza a escuchar. Si el archivo no existe o faltan tablas, se crea el esquema y se pueblan los datos predeterminados dentro de una única transacción, con restricciones `UNIQUE`/`PRIMARY KEY` que hacen la operación idempotente si se repitiera. Esto significa:

- Sin paso de migración independiente
- Sin configuración manual de la base de datos
- Los volúmenes Docker nuevos arrancan automáticamente con una base de datos limpia y poblada

### Concurrencia de Escritura

La base de datos se abre con `PRAGMA journal_mode=WAL` (permite lectores concurrentes sin bloquear al escritor). Además de la inicialización, en estado estable conviven varias fuentes de escritura en el mismo proceso: la tarea periódica de `portfolio_snapshots` (cada 30s), los handlers de `POST /api/portfolio/trade` (que escriben `users_profile`, `positions`, `trades` y un snapshot en la misma operación) y posibles peticiones concurrentes del usuario o del LLM ejecutando varios trades. Todas las escrituras pasan por una única conexión de escritura (o una cola/lock a nivel de aplicación), de forma que nunca compitan sin coordinación y el proceso no dependa de reintentos ante `database is locked`.

### Esquema

Todas las tablas incluyen una columna `user_id` con valor predeterminado `"default"`. Esto está fijado por ahora (usuario único) pero permite un futuro soporte multiusuario sin migración de esquema.

**Precisión monetaria**: `cash_balance`, `avg_cost`, `price` y `total_value` se mantienen como `REAL` (se descarta introducir `Decimal`/enteros de escala fija — no justificado por la simplicidad didáctica del proyecto, igual criterio que llevó a elegir SQLite sobre Postgres, §3). Para evitar que los errores de redondeo binario produzcan validaciones o totales inconsistentes entre la cabecera, la tabla de posiciones y los snapshots: todo valor monetario se redondea a 2 decimales en el momento de escribirse (misma idea que el redondeo a 4 decimales ya fijado para `quantity`), y toda comparación con cero (p. ej. detectar cash insuficiente) usa una tolerancia de `1e-6`, igual que la ya definida para el cierre de posiciones. Esto incluye explícitamente el precio de ejecución que se persiste en `trades.price` y que alimenta el cálculo de `avg_cost`: aunque el proveedor de datos de mercado emite precios con 4 decimales (`PriceTick.price`, §6), el precio leído de la caché en el momento de ejecutar una operación se redondea a 2 decimales *antes* de usarse tanto para actualizar `cash_balance`/`avg_cost` como para la fila insertada en `trades` — una única regla de redondeo para todo el pipeline de una operación, no dos valores distintos (uno de 4 decimales para mostrar el precio en vivo, otro de 2 para la cartera).

**users_profile** — Estado del usuario (saldo de efectivo)
- `id` TEXT PRIMARY KEY (predeterminado: `"default"`)
- `cash_balance` REAL (predeterminado: `10000.0`)
- `created_at` TEXT (marca de tiempo ISO)

**watchlist** — Tickers que el usuario está vigilando
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (predeterminado: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (marca de tiempo ISO)
- Restricción UNIQUE en `(user_id, ticker)`

**positions** — Posiciones actuales (una fila por ticker por usuario)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (predeterminado: `"default"`)
- `ticker` TEXT
- `quantity` REAL (se admiten acciones fraccionarias, redondeadas a 4 decimales en el backend)
- `avg_cost` REAL
- `updated_at` TEXT (marca de tiempo ISO)
- Restricción UNIQUE en `(user_id, ticker)`
- Cuando una venta deja `quantity` en 0 (con tolerancia de redondeo, `abs(quantity) < 1e-6`), la fila se **elimina** en vez de conservarse en 0 — una posición cerrada no tiene `avg_cost` significativo, y el P&L realizado ya queda registrado en `trades`
- **Fórmula de `avg_cost`**: coste medio ponderado — el único método coherente con guardar una sola fila `avg_cost` por posición (FIFO/LIFO exigirían una tabla de lotes que el esquema no tiene). En una compra: `avg_cost_nuevo = (qty_actual * avg_cost_actual + qty_comprada * precio_ejecucion) / (qty_actual + qty_comprada)`. Una venta **no** cambia el `avg_cost` de la posición restante, solo reduce `quantity`; el P&L realizado de esa venta (`qty_vendida * (precio_ejecucion - avg_cost_actual)`) no se persiste en un campo nuevo — es reconstruible desde `trades` si hiciera falta

**trades** — Historial de operaciones (registro de solo adición)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (predeterminado: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` o `"sell"`)
- `quantity` REAL (se admiten acciones fraccionarias, redondeadas a 4 decimales en el backend — misma precisión que los precios en `PriceTick.create()`)
- `price` REAL
- `executed_at` TEXT (marca de tiempo ISO)
- No se expone un endpoint `GET` para esta tabla en la v1 (se usa internamente para reconstruir `avg_cost` y para el contexto del LLM); es trivial añadir `GET /api/portfolio/trades` más adelante si se necesita una vista de historial

**portfolio_snapshots** — Valor de la cartera a lo largo del tiempo (para el gráfico de P&L). Se registra cada 30 segundos mediante una tarea en segundo plano, e inmediatamente después de cada ejecución de operación.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (predeterminado: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (marca de tiempo ISO)

**chat_messages** — Historial de conversación con el LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (predeterminado: `"default"`)
- `role` TEXT (`"user"` o `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON; null para mensajes del usuario). Para mensajes del asistente, reutiliza el esquema de salida estructurada del §9 (`trades`, `watchlist_changes`) añadiendo el resultado de la ejecución a cada elemento:
  ```json
  {
    "trades": [
      {"ticker": "AAPL", "side": "buy", "quantity": 10, "executed": true, "error": null}
    ],
    "watchlist_changes": [
      {"ticker": "PYPL", "action": "add", "executed": true, "error": null}
    ]
  }
  ```
  Esto da una única forma de datos entre lo que pidió el LLM y lo que se persistió/renderizó como confirmación en el chat (§10)
- `created_at` TEXT (marca de tiempo ISO)

### Datos Semilla Predeterminados

- Un perfil de usuario: `id="default"`, `cash_balance=10000.0`
- Diez entradas en la watchlist: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. Endpoints de la API

### Datos de Mercado
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/stream/prices` | Stream SSE de actualizaciones de precios en vivo |

### Cartera
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/portfolio` | Posiciones actuales, saldo de efectivo, valor total, P&L no realizado |
| POST | `/api/portfolio/trade` | Ejecuta una operación: `{ticker, quantity, side}`. El ticker no necesita existir en la watchlist — se acepta cualquier símbolo con formato válido (`^[A-Z]{1,5}$`), coherente con que el simulador ya soporta tickers dinámicos. `quantity` debe ser estrictamente positiva (`> 0`) tras redondear a 4 decimales; con 4 decimales, `0.0001` ya es el mínimo positivo representable |
| GET | `/api/portfolio/history` | Capturas del valor de la cartera a lo largo del tiempo (para el gráfico de P&L). Admite `?limit=` (por defecto 200, máximo 1000) y devuelve siempre en orden cronológico ascendente por `recorded_at` |

### Watchlist
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/watchlist` | Tickers actuales de la watchlist con sus últimos precios |
| POST | `/api/watchlist` | Añade un ticker: `{ticker}`. Idempotente: añadir un ticker ya presente devuelve `200` sin duplicar la fila (la restricción `UNIQUE (user_id, ticker)` de §7 ya lo garantiza a nivel de datos) |
| DELETE | `/api/watchlist/{ticker}` | Elimina un ticker. `404` si el ticker no está en la watchlist del usuario |

### Chat
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/chat` | Envía un mensaje, recibe una respuesta JSON completa (mensaje + acciones ejecutadas). El campo `message` del usuario está limitado a 4000 caracteres (`400` si se excede) |
| GET | `/api/chat/messages` | Historial de conversación persistido, para reconstruirlo tras recargar la página. Admite `?limit=` (por defecto 50), devuelto en orden cronológico ascendente |

### Sistema
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Comprobación de estado (para Docker/despliegue). Ver contrato detallado en §11 |

### Contratos de Respuesta y Errores

Todos los endpoints de escritura (`POST`/`DELETE`) usan estos códigos de forma consistente:

| Código | Significado | Ejemplos |
|---|---|---|
| `400` | Payload o formato inválido | Ticker que no cumple `^[A-Z]{1,5}$`, `quantity <= 0`, mensaje de chat > 4000 caracteres |
| `404` | Recurso no encontrado | `DELETE /api/watchlist/{ticker}` para un ticker que no está en la watchlist |
| `409` | La operación es válida en forma pero no se puede ejecutar (regla de negocio) | Efectivo insuficiente para comprar, acciones insuficientes para vender |
| `503` | No hay un precio actual utilizable para el ticker | Ticker recién añadido en modo Massive sin precio tras el timeout de `ensure_ticker` (§6), o símbolo sin datos reales |

El cuerpo de error sigue siempre la forma `{"error": "mensaje legible", "code": "SNAKE_CASE_CODE"}`.

### Cuerpos de Éxito (esquema mínimo)

| Ruta | `200`/`201` body |
|---|---|
| `GET /api/portfolio` | `{cash_balance, total_value, positions: [{ticker, quantity, avg_cost, current_price, unrealized_pnl, unrealized_pnl_pct}]}` |
| `POST /api/portfolio/trade` | `{ticker, side, quantity, price, cash_balance, position: {quantity, avg_cost} \| null}` (`position: null` si la venta cerró la posición) |
| `GET /api/portfolio/history` | `{snapshots: [{total_value, recorded_at}]}` |
| `GET /api/watchlist` | `{tickers: [{ticker, price, prev_price, session_open, added_at}]}` |
| `POST /api/watchlist` | `{ticker, added_at}` |
| `DELETE /api/watchlist/{ticker}` | `204` sin cuerpo |
| `POST /api/chat` | `{message, trades: [...], watchlist_changes: [...]}` — mismo esquema que `chat_messages.actions` (§7) |
| `GET /api/chat/messages` | `{messages: [{id, role, content, actions, created_at}]}` |
| `GET /api/health` | `{status: "ok"}` (o `503` con `{status: "unhealthy", ...}`, ver §11) |

### Límite de acciones del LLM por respuesta

Para que una única respuesta del LLM estructuralmente válida no pueda monopolizar el lock de escritura de SQLite (§7) ejecutando decenas de operaciones en cadena, `trades` y `watchlist_changes` (§9) se limitan cada uno a **10 elementos por respuesta**. Este límite se declara en el modelo Pydantic del `response_format` (p. ej. `Field(max_length=10)`), no solo en el prompt — igual criterio que las restricciones `Literal`/`> 0` ya fijadas en §9. Si el LLM devuelve más, la respuesta no cumple el esquema y se trata como fallo de parseo (§9, "Contrato de Fallos del LLM").

---

## 9. Integración con el LLM

Al escribir código que realice llamadas a LLMs, usa la skill `cerebras` (nombre real de la skill instalada en el repo — no `cerebras-inference`) para utilizar LiteLLM a través de OpenRouter hacia el modelo `openrouter/openai/gpt-oss-120b`, con Cerebras como proveedor de inferencia. Se deben usar Salidas Estructuradas (Structured Outputs) para interpretar los resultados.

La skill pasa la preferencia de proveedor como `extra_body = {"provider": {"order": ["cerebras"]}}`, que por defecto es solo un **orden** de preferencia: OpenRouter puede recurrir a otro proveedor si Cerebras no está disponible. Dado que la elección de Cerebras está justificada explícitamente por velocidad de inferencia (§3), se añade `"allow_fallbacks": false` dentro de `"provider"` para garantizar que la demo siempre corre sobre Cerebras y nunca degrada silenciosamente a un proveedor más lento.

Existe una OPENROUTER_API_KEY en el archivo .env en la raíz del proyecto.

### Cómo Funciona

Cuando el usuario envía un mensaje de chat, el backend:

1. Carga el contexto actual de la cartera del usuario (efectivo, posiciones con P&L, watchlist con precios en vivo, valor total de la cartera)
2. Carga el historial de conversación reciente desde la tabla `chat_messages` (máximo los últimos 20 mensajes — 20 filas literales vía `ORDER BY created_at DESC, rowid DESC LIMIT 20`, no 20 turnos; el desempate por `rowid` — la columna implícita de SQLite, siempre monótonamente creciente en inserción — evita que dos mensajes con el mismo `created_at` textual, aunque `created_at` ya tiene precisión de microsegundos, se reordenen de forma no determinista). Al construir el prompt, invertir los 20 resultados para enviarlos en orden cronológico
3. Construye un prompt con un mensaje de sistema, el contexto de la cartera, el historial de conversación y el nuevo mensaje del usuario
4. Llama al LLM a través de LiteLLM → OpenRouter, solicitando salida estructurada, usando la skill `cerebras`, con un timeout de 30 segundos y sin reintentos automáticos
5. Parsea la respuesta JSON estructurada completa
6. Ejecuta automáticamente cualquier operación o cambio de watchlist especificado en la respuesta — cada trade se valida y ejecuta contra el estado de la base de datos leído **en el instante de ejecutar ese trade concreto**, nunca contra el contexto de cartera cargado en el paso 1. Esto importa cuando `trades` trae más de un elemento en la misma respuesta (p. ej. vender AAPL y comprar TSLA): la validación de la segunda operación debe ver el efectivo ya actualizado por la primera, no el snapshot inicial. Cada trade corre en su propia transacción SQLite (§7), ejecutadas en orden
7. Almacena el mensaje y las acciones ejecutadas en `chat_messages`
8. Devuelve la respuesta JSON completa al frontend (sin streaming token a token — la inferencia de Cerebras es suficientemente rápida como para que un indicador de carga sea suficiente)

### Esquema de Salida Estructurada

Se instruye al LLM para que responda con un JSON que coincida con este esquema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"},
    {"ticker": "NFLX", "action": "remove"}
  ]
}
```

- `message` (obligatorio): el texto conversacional mostrado al usuario
- `trades` (opcional): array de operaciones a ejecutar automáticamente. Cada operación pasa por la misma validación que las operaciones manuales (efectivo suficiente para compras, acciones suficientes para ventas, `quantity > 0`)
- `watchlist_changes` (opcional): array de modificaciones de la watchlist. `action` admite `"add"` o `"remove"`

El modelo Pydantic pasado como `response_format` a la skill `cerebras` restringe estos campos a nivel de tipo — no solo mediante instrucciones de prompt — para que OpenRouter descarte en origen una clase entera de respuestas inválidas: `side: Literal["buy", "sell"]`, `action: Literal["add", "remove"]`, `quantity: float` con restricción `> 0`. Esto no sustituye la validación de backend (que sigue siendo necesaria porque el LLM puede alucinar cantidades sintácticamente válidas pero semánticamente imposibles, como comprar más de lo que el efectivo permite), pero reduce la superficie de "JSON válido con campos basura" que el código de ejecución tendría que filtrar.

### Ejecución Automática

Las operaciones especificadas por el LLM se ejecutan automáticamente — sin diálogo de confirmación. Esta es una decisión de diseño deliberada:
- Es un entorno simulado con dinero ficticio, por lo que el riesgo es nulo
- Crea una experiencia de demostración impresionante y fluida
- Demuestra capacidades de IA agéntica — el tema central del curso

Si una operación no pasa la validación (por ejemplo, efectivo insuficiente), el error se incluye en la respuesta del chat para que el LLM pueda informar al usuario.

### Contrato de Fallos del LLM

Si la llamada a OpenRouter/Cerebras falla (timeout tras 30s, error de red, clave inválida) o la respuesta no es JSON válido / no cumple el esquema Pydantic: no se ejecuta ninguna acción (`trades`/`watchlist_changes` vacíos), no hay reintentos automáticos, y `POST /api/chat` devuelve igualmente `200` con un `message` de error conversacional seguro para el usuario (p. ej. "No pude procesar tu solicitud, inténtalo de nuevo"). El mensaje del usuario se persiste en `chat_messages` de todas formas, junto con esta respuesta de error del asistente en lugar del contenido real del LLM.

### Orientación del Prompt de Sistema

Se debe indicar al LLM que actúe como "FinAlly, un asistente de trading con IA", con instrucciones para:
- Analizar la composición de la cartera, la concentración de riesgo y el P&L
- Sugerir operaciones con su razonamiento
- Ejecutar operaciones cuando el usuario lo solicite o esté de acuerdo
- Incluir una operación en `trades` únicamente si el usuario la pidió explícitamente o aceptó una sugerencia previa en su último mensaje; si solo está sugiriendo, no incluirla todavía (no hay paso intermedio de confirmación — el LLM actúa en el mismo turno en el que decide ejecutar)
- Operar solo con tickers de empresas reales que coticen en NYSE/NASDAQ (no hay validación dura de esto en el backend más allá del formato del símbolo, así que esta instrucción es la principal salvaguarda contra tickers inventados)
- Gestionar la watchlist de forma proactiva
- Ser conciso y basarse en datos en sus respuestas
- Responder siempre con un JSON estructurado válido

### Modo Simulado del LLM

Cuando `LLM_MOCK=true`, el backend devuelve respuestas simuladas deterministas en lugar de llamar a OpenRouter. Esto permite:
- Tests E2E rápidos, gratuitos y reproducibles
- Desarrollo sin una clave de API
- Pipelines de CI/CD

**Regla de mapeo mensaje→respuesta** (necesaria para que los tests E2E de §12 sean escribibles): el mock primero normaliza todo el mensaje a mayúsculas, y luego aplica, en este orden, la primera expresión regular que coincida (evita que la propia palabra clave — p. ej. `BUY` — se confunda con el ticker capturado en `[A-Z]{1,5}`, que sí podría matchear la palabra clave si no se la excluye explícitamente de la búsqueda del ticker):

1. `\b(?:BUY|COMPRA)\b.*?\b(?!BUY\b|COMPRA\b|SELL\b|VENDE\b|ADD\b|AÑADE\b)([A-Z]{1,5})\b` → `trades: [{"ticker": <grupo 1>, "side": "buy", "quantity": 1}]`
2. `\b(?:SELL|VENDE)\b.*?\b(?!BUY\b|COMPRA\b|SELL\b|VENDE\b|ADD\b|AÑADE\b)([A-Z]{1,5})\b` → `trades: [{"ticker": <grupo 1>, "side": "sell", "quantity": 1}]`
3. `\b(?:ADD|AÑADE)\b.*?\b(?!BUY\b|COMPRA\b|SELL\b|VENDE\b|ADD\b|AÑADE\b)([A-Z]{1,5})\b` → `watchlist_changes: [{"ticker": <grupo 1>, "action": "add"}]`
4. Si la palabra clave (`BUY`/`COMPRA`/`SELL`/`VENDE`/`ADD`/`AÑADE`) está presente pero ninguna de las reglas anteriores captura un ticker (p. ej. `"compra algo"`, sin símbolo reconocible) → respuesta puramente conversacional, igual que el caso 5; no se inventa un ticker
5. Cualquier otro mensaje → respuesta puramente conversacional (`message` fijo o basado en eco del contexto de cartera cargado en el paso 1 de §9), sin `trades` ni `watchlist_changes`

Esta gramática cubre de forma determinista tanto comandos (`"BUY AAPL"`, `"compra 5 TSLA"`) como frases naturales (`"quiero comprar NVDA"`), y el caso sin ticker. Los tests unitarios del mock (backend) deben incluir casos para cada regla, incluyendo un mensaje con palabra clave pero sin ticker.

---

## 10. Diseño del Frontend

### Disposición (Layout)

El frontend es una aplicación de una sola página con una disposición densa, inspirada en una terminal. La arquitectura de componentes específica y el sistema de disposición quedan a criterio del Ingeniero de Frontend, pero la interfaz debe incluir estos elementos:

- **Panel de watchlist** — cuadrícula/tabla de tickers vigilados con: símbolo del ticker, precio actual (destellando en verde/rojo al cambiar), % de cambio diario, y un mini-gráfico tipo sparkline (acumulado desde el SSE desde la carga de la página, con un buffer circular de tamaño fijo por ticker — p. ej. últimos 150 ticks ≈ 75s a 500ms/tick — para no acumular memoria sin límite en sesiones largas)
- **Área principal de gráficos** — gráfico más grande para el ticker actualmente seleccionado, mostrando como mínimo el precio a lo largo del tiempo. Al cargar la página se selecciona automáticamente el primer ticker de la watchlist (p. ej. AAPL en el estado semilla) — coherente con "inmediatamente ve... precios actualizándose en vivo" (§2) y evita un panel central vacío en la primera impresión. Al hacer clic en otro ticker de la watchlist cambia la selección. Igual que los sparklines, el gráfico se llena en vivo desde el SSE a partir del momento en que se selecciona — no hay backfill histórico en la v1 (ni con el simulador ni con Massive), para mantener el mismo comportamiento en ambas fuentes de datos.
- **Mapa de calor de la cartera** — visualización treemap donde cada rectángulo es una posición, dimensionado por peso en la cartera y coloreado por P&L (verde = beneficio, rojo = pérdida)
- **Gráfico de P&L** — gráfico de líneas que muestra el valor total de la cartera a lo largo del tiempo, usando datos de `portfolio_snapshots`
- **Tabla de posiciones** — vista tabular de todas las posiciones: ticker, cantidad, coste medio, precio actual, P&L no realizado, % de cambio
- **Barra de operaciones** — área de entrada sencilla: campo de ticker, campo de cantidad, botón de compra, botón de venta. Órdenes de mercado, ejecución instantánea.
- **Panel de chat de IA** — barra lateral acoplada/colapsable. Entrada de mensajes, historial de conversación con desplazamiento, indicador de carga mientras se espera la respuesta del LLM. Las ejecuciones de operaciones y los cambios de watchlist se muestran en línea como confirmaciones.
- **Encabezado** — valor total de la cartera (actualizándose en vivo), indicador de estado de conexión, saldo de efectivo

### Notas Técnicas

- Usar `EventSource` para la conexión SSE a `/api/stream/prices`
- Se prefiere una librería de gráficos basada en canvas (Lightweight Charts o Recharts) por rendimiento
- Efecto de destello de precio: al recibir un nuevo precio, aplicar brevemente una clase CSS con transición de color de fondo, y luego eliminarla
- El "% de cambio diario" del panel de watchlist se calcula como `(price - session_open) / session_open` usando el campo `session_open` de cada evento SSE (§6), no el cambio respecto al tick anterior
- Los campos de ticker (barra de operaciones, formulario de watchlist) normalizan el texto a mayúsculas en tiempo real, antes de enviar la petición — así la regex `^[A-Z]{1,5}$` del backend (§8) nunca es la causa visible de un error evitable si el usuario escribe en minúsculas
- Todas las llamadas a la API van al mismo origen (`/api/*`) — no se necesita configuración de CORS
- Tailwind CSS para los estilos, con un tema oscuro personalizado

---

## 11. Docker y Despliegue

### Dockerfile Multi-Etapa

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1
  - CMD: uvicorn serving FastAPI app
```

FastAPI sirve los archivos estáticos del frontend y todas las rutas de la API en el puerto 8000. Los `APIRouter` de `/api/*` se registran **antes** que el montaje de `StaticFiles`, y este último se monta en `/` después de incluir todos los routers — así una ruta de API mal registrada nunca queda "tapada" por el mount de estáticos y devuelve un 404 de archivo en lugar de llegar al handler real. Al ser un export estático de una sola página sin rutas de cliente adicionales, un 404 real para cualquier ruta no reconocida fuera de `/api/*` es aceptable — no hace falta un fallback tipo "todo sirve `index.html`".

`GET /api/health` no se limita a devolver `200` incondicionalmente: comprueba que SQLite responde (`SELECT 1`) y que el proveedor de datos de mercado (`app.state.market_data_provider`) existe y está corriendo, devolviendo `503` si alguna falla. Esto detecta el fallo más probable del proyecto — el contenedor arranca pero el proveedor de mercado nunca llegó a iniciarse por una excepción en `lifespan` — como `unhealthy` en Docker, en vez de dejar al usuario con una watchlist sin precios y ninguna señal visible del problema.

### Volumen Docker

La base de datos SQLite persiste mediante un bind mount del directorio `db/` de la raíz del proyecto:

```bash
docker run -v $(pwd)/db:/app/db -p 8000:8000 --env-file .env finally
```

> Nota: el ejemplo anterior usa sintaxis bash (`$(pwd)`), solo ilustrativa. `scripts/start_windows.ps1` debe usar el equivalente de PowerShell (`${PWD}` o `(Get-Location).Path`) en vez de traducir el comando literalmente.

El directorio `db/` en la raíz del proyecto se mapea a `/app/db` en el contenedor. El backend escribe `finally.db` en esta ruta, por lo que el archivo es directamente inspeccionable/respaldable desde el host.

### Scripts de Inicio/Parada

**`scripts/start_mac.sh`** (macOS/Linux):
- Construye la imagen Docker si aún no está construida (o si se pasa el flag `--build`)
- Ejecuta el contenedor con el montaje del volumen, el mapeo de puertos y el archivo `.env`
- Imprime la URL para acceder a la aplicación
- Opcionalmente abre el navegador

**`scripts/stop_mac.sh`** (macOS/Linux):
- Detiene y elimina el contenedor en ejecución
- NO elimina el volumen (los datos persisten)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: equivalentes en PowerShell para Windows.

Todos los scripts deben ser idempotentes — seguros de ejecutar varias veces.

**Reinicio del estado de demo**: no hay endpoint de reset en la v1. Para volver a los valores por defecto ($10.000, sin posiciones, watchlist por defecto), basta con detener el contenedor y borrar `db/finally.db` — la inicialización lazy (§7) lo regenera limpio en el siguiente arranque. No es necesario documentar esto como un flujo soportado con tooling propio salvo que se quiera pulir aún más la experiencia de demo (stretch goal: flag `--reset` en los scripts de inicio).

### Despliegue en la Nube (Opcional)

El contenedor está diseñado para desplegarse en AWS App Runner, Render o cualquier plataforma de contenedores. Como objetivo adicional (stretch goal) podría proporcionarse una configuración de Terraform para App Runner en un directorio `deploy/`, pero no forma parte de la construcción principal.

---

## 12. Estrategia de Pruebas

### Tests Unitarios (dentro de `frontend/` y `backend/`)

**Backend (pytest)**:
- Datos de mercado: el simulador genera precios válidos, la matemática del GBM es correcta, el parseo de la respuesta de la API de Massive funciona, ambas implementaciones cumplen con la interfaz abstracta
- Cartera: lógica de ejecución de operaciones, cálculos de P&L, casos límite (vender más de lo que se posee, comprar con efectivo insuficiente, vender con pérdidas)
- LLM: el parseo de la salida estructurada maneja todos los esquemas válidos, manejo correcto de respuestas malformadas, validación de operaciones dentro del flujo de chat
- Rutas de la API: códigos de estado correctos, formas de respuesta, manejo de errores

**Frontend (React Testing Library o similar)**:
- Renderizado de componentes con datos simulados
- La animación de destello de precio se activa correctamente ante cambios de precio
- Operaciones CRUD de la watchlist
- Cálculos de visualización de la cartera
- Renderizado de mensajes de chat y estado de carga

### Tests E2E (en `test/`)

**Infraestructura**: un `docker-compose.test.yml` independiente en `test/` que levanta el contenedor de la aplicación junto con un contenedor de Playwright. Esto mantiene las dependencias del navegador fuera de la imagen de producción.

**Entorno**: los tests se ejecutan con `LLM_MOCK=true` por defecto, para mayor velocidad y determinismo.

**Escenarios Clave**:
- Inicio limpio: aparece la watchlist predeterminada, se muestra el saldo de $10k, los precios se están transmitiendo
- Añadir y eliminar un ticker de la watchlist
- Comprar acciones: el efectivo disminuye, aparece la posición, la cartera se actualiza
- Vender acciones: el efectivo aumenta, la posición se actualiza o desaparece
- Visualización de la cartera: el mapa de calor se renderiza con los colores correctos, el gráfico de P&L tiene puntos de datos (el test se apoya en la captura inmediata de `portfolio_snapshots` "después de cada ejecución de operación" prevista en §7 — p. ej. ejecutar 2-3 compras/ventas seguidas y verificar que aparecen 2-3 puntos — sin esperar al temporizador de 30s)
- Chat de IA (simulado): enviar un mensaje, recibir una respuesta, la ejecución de la operación aparece en línea (la regla de mapeo mensaje→respuesta del modo mock está fijada en §9, para que el test conozca de antemano qué mensaje produce qué respuesta)
- Resiliencia del SSE: desconectar y verificar la reconexión. La desconexión se provoca de forma determinista desde Playwright (p. ej. abortando la petición de red de la conexión SSE con `page.route(...).abort()`, o cerrando el contexto de red), no dependiendo de un corte de red real. El heartbeat `ping` cada 15s (§6) da al test una señal de actividad verificable sin esperar a un cambio de precio real

---

## 13. Revisión del Documento — Preguntas, Aclaraciones y Simplificaciones

> Añadido por revisión de documentación (2026-08-14, actualizado con recomendaciones). El componente de datos de mercado (§6) ya está implementado y revisado (`planning/market_data_review.md`); los puntos siguientes se centran sobre todo en las partes aún por construir (base de datos, cartera, LLM, frontend, Docker), donde una ambigüedad ahora es barata de resolver y cara de resolver a mitad de implementación. Cada punto incluye una recomendación para no bloquear el trabajo de los agentes siguientes.
>
> **Estado (2026-08-14): todas las recomendaciones fueron aprobadas ("Proceder con la recomendación") y ya están incorporadas como decisiones en las secciones correspondientes (§5, §6, §7, §8, §9, §10, §11, §12, y `market_data_design.md`). Esta sección se conserva como registro/historial de la revisión, no como fuente de verdad — para el detalle de cada decisión, consultar la sección referenciada.

### Datos de mercado (ya implementado — notas menores)

- **Placeholder de URL obsoleto**: `planning/market_data_design.md` §6.1 usa `https://api.massive.io/v2` como base URL de ejemplo. La investigación posterior (`planning/massive_api.md`) confirmó que la URL real es `https://api.massive.com` con rutas `/v2/snapshot/locale/us/markets/stocks/tickers`, y `market_data_review.md` confirma que la implementación real ya usa la URL correcta.
  - **Recomendación**: actualizar el placeholder en `market_data_design.md` a `https://api.massive.com` para que el documento de diseño no diverja del código ya implementado. Cambio cosmético, sin riesgo.
RESPUESTA: Proceder con lo recomendado.

- **Siembra de tickers al arrancar**: el fragmento de `lifespan` en `market_data_design.md` §8 solo llama a `provider.add_ticker(...)` para los tickers de la `watchlist` persistida, pero §6 de este plan exige que el stream cubra la **unión** de watchlist + tickers con posición abierta.
  - **Recomendación**: al implementar el módulo de cartera, sembrar el proveedor con `watchlist_tickers ∪ position_tickers` (una consulta `SELECT DISTINCT ticker FROM positions` además de la watchlist) en el mismo bloque de `lifespan`. Es un cambio de una línea y evita el caso borde de "posición huérfana sin precio" tras un reinicio del contenedor.
  RESPUESTA: Proceder con la recomendación.

### Base de datos y cartera

- **¿Qué pasa cuando una posición llega a `quantity = 0`?** El escenario de test en §12 dice "la posición se actualiza o desaparece" — la disyuntiva sugiere que aún no está decidido.
  - **Recomendación**: eliminar la fila de `positions` cuando `quantity` llega a 0 (con tolerancia de redondeo, p. ej. `abs(quantity) < 1e-6`). Es la opción más simple: `avg_cost` no tiene significado en una posición cerrada, el mapa de calor y la tabla de posiciones no necesitan filtrar filas "vacías", y el historial de P&L realizado ya vive en `trades`, no en `positions`. Alternativa (no recomendada salvo que se quiera mostrar "posiciones cerradas" en la UI): conservar la fila con `quantity=0` y filtrarla en las consultas de lectura — añade complejidad sin un requisito claro en §10 que la justifique.
RESPUESTA: Proceder con la recomendación.

- **Precisión de `quantity`**: el esquema admite `REAL` para acciones fraccionarias, pero no se especifica ninguna precisión máxima.
  - **Recomendación**: redondear a 4 decimales en el backend (igual criterio que `PriceTick.create()` ya usa para precios, ver `market_data_design.md` §2), validando ahí y solo ahí. El frontend usa un `<input type="number" step="any">` sin lógica de redondeo propia — una sola fuente de verdad.
RESPUESTA: Proceder con la recomendación.

- **Historial de operaciones**: `trades` es una tabla de solo-inserción, pero no hay ningún endpoint `GET` para ella en §8.
  - **Recomendación**: dejarlo fuera del alcance de la v1 — el diseño visual de §10 no incluye una vista de historial de operaciones, y `trades` ya cumple su propósito interno (reconstruir `avg_cost`, alimentar el LLM). Si en el futuro se quiere mostrar un historial, añadir `GET /api/portfolio/trades` es trivial sobre el esquema ya existente; no vale la pena construirlo por adelantado sin un requisito de UI.
RESPUESTA: Proceder con la recomendación.

- **Forma de `chat_messages.actions`**: no está definido el esquema exacto de este campo JSON. §10 dice que "las ejecuciones de operaciones... se muestran en línea como confirmaciones", lo cual implica que se necesita el *resultado* de la ejecución, no solo la intención cruda del LLM.
  - **Recomendación**: reutilizar el mismo esquema de §9 (`trades`, `watchlist_changes`) pero añadiendo `executed: bool` y `error: string | null` a cada elemento del array, por ejemplo `{"ticker": "AAPL", "side": "buy", "quantity": 10, "executed": true, "error": null}`. Así hay una única forma de datos entre "lo que pidió el LLM" y "lo que se persistió/renderizó", sin inventar un esquema paralelo.
RESPUESTA: Proceder con la recomendación.

- **¿Se puede operar con tickers fuera de la watchlist?** El simulador ya asigna precio a cualquier ticker desconocido (§6), lo que sugiere que sí.
  - **Recomendación**: permitir operar con cualquier símbolo con formato válido (p. ej. regex `^[A-Z]{1,5}$`) sin exigir que esté en la watchlist primero — es coherente con que el simulador ya soporta tickers dinámicos, y evita una validación cruzada watchlist↔trade que añadiría complejidad innecesaria. Alternativa más restrictiva (más simple de razonar pero menos flexible): exigir que el ticker exista en la watchlist antes de poder operar con él; solo recomendable si se prefiere priorizar la sencillez conceptual sobre la flexibilidad del usuario/LLM.
  RESPUESTA: Proceder con la recomendación.

### Integración con el LLM

- **"Últimos 20 mensajes"** (§9): ¿20 mensajes en total (mezclando `user` y `assistant`) o 20 turnos completos (40 filas)?
  - **Recomendación**: interpretarlo literalmente — `SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 20` (20 filas, no 20 turnos). Es la lectura más simple del texto y evita mantener lógica de "turnos" separada de "mensajes".
- **Tickers inventados por el LLM**: un LLM que alucine un símbolo inexistente (p. ej. `"MOON"`) podría ejecutar una compra "válida" sobre un activo ficticio sin que nada lo impida.
  - **Recomendación**: no añadir una validación especial distinta de la ya sugerida para trades manuales (formato de símbolo). Tratar esto como una consecuencia aceptada del diseño "sin riesgo real" (§9 ya lo justifica explícitamente), y opcionalmente reforzar en el prompt de sistema una instrucción del tipo "solo opera con tickers de empresas reales que existan en NYSE/NASDAQ"; el LLM lo respetará en la mayoría de casos aunque no haya una validación dura en el backend. Alternativa más estricta (si se prefiere cero riesgo de "tickers fantasma" en la demo): restringir `trades`/`watchlist_changes` del LLM a los tickers ya presentes en la watchlist del usuario — más simple de validar, pero limita que el LLM proponga nuevas ideas de inversión no vigiladas todavía.
RESPUESTA: Proceder con la recomendación.

- **Ejecución automática de un solo turno**: §9 dice que se ejecutan operaciones "cuando el usuario lo solicite o esté de acuerdo", pero el flujo real (una respuesta JSON completa por mensaje) significa que el LLM decide unilateralmente incluir un trade en la misma respuesta donde lo "sugiere".
  - **Recomendación**: confirmar que esta lectura es la intencionada (el LLM actúa en el turno donde el usuario ya pidió o confirmó algo, nunca hay un paso de "propongo → espero sí/no → ejecuto" dentro de la misma respuesta) y reforzarlo en la guía del prompt de sistema (§9) con una línea explícita: *"Incluye una operación en `trades` únicamente si el usuario la pidió explícitamente o aceptó una sugerencia previa en su último mensaje; si solo estás sugiriendo, no la incluyas todavía."* Esto es una aclaración de redacción, no un cambio de arquitectura — barato de aplicar ahora.
  RESPUESTA: Proceder con la recomendación.

### Frontend

- **Crecimiento no acotado de los sparklines**: no se menciona ningún límite de puntos retenidos por sparkline; en una sesión de demo larga, cada uno crecería sin límite en memoria del navegador.
  - **Recomendación**: fijar un buffer circular de tamaño fijo por ticker (p. ej. últimos 150 ticks ≈ 75s a 500ms/tick, suficiente para ver tendencia reciente sin acumular memoria). Definir la constante una vez en el frontend, no como decisión ad-hoc del componente.
RESPUESTA: Proceder con la recomendación.

- **Gráfico principal también arranca vacío**: igual que los sparklines, no hay backend de histórico por ticker (solo `portfolio_snapshots` para el valor total de cartera); con el simulador no hay velas históricas reales que mostrar, con Massive sí existirían pero no está en el alcance de §8.
  - **Recomendación**: mantener el mismo comportamiento "vacío al cargar, se llena en vivo desde SSE" para ambas fuentes de datos, por simplicidad y consistencia visual entre modo simulador y modo Massive. No implementar backfill histórico vía Massive `aggs` en la v1 — es un stretch goal claro si sobra tiempo, no un requisito de §8.
  RESPUESTA: Proceder con la recomendación.

### Docker y entorno

- **`.env` en desarrollo local sin Docker**: si se usa `--env-file` de Docker, el proceso Python nunca necesita parsear el archivo; pero un flujo de desarrollo local sin Docker (`uv run uvicorn ...`) sí lo necesitaría, y `python-dotenv` no aparece hoy en `backend/pyproject.toml`.
  - **Recomendación**: añadir `python-dotenv` como dependencia del backend y cargar `.env` al arrancar (`load_dotenv()` al inicio de `main.py`, antes de leer cualquier variable) — es un no-op seguro cuando las variables ya vienen inyectadas por Docker (`load_dotenv` no sobreescribe variables ya presentes en el entorno por defecto), y desbloquea tanto el flujo Docker como el flujo `uv run` local con una sola línea.
RESPUESTA: Proceder con la recomendación.

- **Ejemplo de comando con sintaxis bash**: `docker run -v $(pwd)/db:/app/db ...` (§11) usa sustitución de comandos de bash; no se traduce directo a PowerShell.
  - **Recomendación**: añadir una nota al pie del bloque de código aclarando que es ilustrativo, y que `scripts/start_windows.ps1` debe usar `${PWD}` o `(Get-Location).Path` en su lugar. Cambio puramente documental.
  RESPUESTA: Proceder con la recomendación.

### Testing

- El intervalo de 30s para `portfolio_snapshots` (§7) probablemente sea demasiado lento para que un test E2E acumule varios puntos dentro de su tiempo de ejecución.
  - **Recomendación**: confirmar explícitamente en §7 o §12 que la estrategia de test para "el gráfico de P&L tiene puntos de datos" se apoya en la captura inmediata "después de cada ejecución de operación" (ya prevista en §7) — por ejemplo, el test E2E ejecuta 2-3 compras/ventas seguidas y verifica que aparecen 2-3 puntos, sin esperar al temporizador de 30s. Evita que quien escriba el test intente un `sleep(30)+` innecesario o, peor, marque el test como flaky por falta de puntos.
  RESPUESTA: Proceder con la recomendación.

## 14. Revisión del Documento — Ronda 2 (Codex Reviewer + Claude Reviewer)

> Añadido 2026-08-14. Dos revisiones independientes del `PLAN.md` resultante de la Ronda 1 (§13): `planning/codex-review.md` (hecha con Codex, 10 hallazgos + ajustes menores) y `planning/claude_reviewer_agent.md` (hecha con Claude, que además verificó punto por punto cuáles de los 10 hallazgos de Codex seguían abiertos y aportó 19 hallazgos nuevos). Todas las recomendaciones de ambas revisiones fueron aceptadas y ya están incorporadas como decisiones en las secciones correspondientes (§5, §6, §7, §8, §9, §10, §11, §12). Esta sección es un registro/índice de esa ronda, no la fuente de verdad — para el detalle de cada decisión, consultar la sección referenciada; para el razonamiento completo de cada hallazgo, consultar los dos documentos originales.

### De `codex-review.md` (9 de 10 estaban completamente abiertos, 1 parcial — confirmado por Claude Reviewer antes de esta ronda)

| # | Hallazgo | Resuelto en |
|---|---|---|
| 1 | Contratos de respuesta y error de la API, idempotencia | §8 (tabla de códigos, idempotencia de `POST`/`DELETE` watchlist) |
| 2 | Atomicidad y precio fresco en trades; validación de lotes del LLM contra estado vivo | §9 (paso 6), §7 (concurrencia de escritura) |
| 3 | `REAL` no apropiado como fuente de verdad para dinero | §7 (redondeo a 2 decimales + tolerancia `1e-6`, se descarta `Decimal`/enteros de escala fija por simplicidad didáctica) |
| 4 | "% de cambio diario" no derivable de la caché descrita | §6 (`session_open`), §10 (fórmula en la UI) |
| 5 | Ciclo de vida de tickers añadidos/retirados en runtime | §6 (`ensure_ticker`, `get_last_price`, `remove_ticker` al retirar de watchlist sin posición) |
| 6 | Carrera en la inicialización lazy de SQLite | §7 (inicialización en `lifespan`, antes de aceptar tráfico) |
| 7 | Contrato SSE incompleto (heartbeat, forma, reconexión) | §6 (evento `ping` cada 15s), §12 (mecanismo determinista de desconexión en el test E2E) |
| 8 | Sin endpoint de lectura del historial de chat | §8 (`GET /api/chat/messages`) |
| 9 | Orden no determinista por `created_at` | §9 (desempate por `rowid`) |
| 10 | Dependencia LLM sin versionar / sin contrato de fallos | §5 (dependencias del backend), §9 (contrato de fallos, timeout, `allow_fallbacks`) |

Ajustes menores de Codex también incorporados: paginación de `GET /api/portfolio/history` (§8), límite de tamaño de mensaje de chat (§8), y timezone/formato de timestamp — resuelto fijando `+00:00`/microsegundos (la convención que ya usa el código de mercado) en vez del sufijo `Z` sugerido por Codex, para no introducir una segunda convención (§6).

### De `planning/claude_reviewer_agent.md` (19 hallazgos nuevos)

| Bloque | Hallazgos | Resuelto en |
|---|---|---|
| Datos de mercado | Interfaz síncrona `get_last_price`, timeout de Massive para tickers nuevos, convención de timestamp | §6 |
| Base de datos / Cartera | Fórmula de `avg_cost` (coste medio ponderado), concurrencia SQLite en estado estable (WAL), base de normalización del treemap, regla `quantity > 0`, código de error para "sin precio disponible" | §7, §8, §10 |
| LLM | Nombre real de la skill (`cerebras` en vez de `cerebras-inference`), `allow_fallbacks: false`, dependencias `litellm`/`pydantic`, restricciones Pydantic (`Literal`, cantidad positiva) en el esquema estructurado, contrato de fallos del LLM, regla de mapeo mensaje→respuesta en `LLM_MOCK` | §5, §9 |
| Frontend | Normalización a mayúsculas del input de ticker, selección automática del primer ticker de la watchlist al cargar | §10 |
| Docker | Contrato real de `/api/health` + `HEALTHCHECK`, orden de registro de rutas API vs. estáticos, documentación de reinicio de la demo | §11 |
| Testing | Mecanismo determinista de desconexión SSE para el test E2E de reconexión | §12 |

RESPUESTA: Proceder con todas las recomendaciones de ambos documentos.

