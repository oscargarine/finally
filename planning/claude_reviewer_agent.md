# Revisión de `PLAN.md` — Claude Reviewer Agent

Fecha: 2026-08-14

## Alcance y método

Esta revisión sustituye por completo la versión anterior de este mismo archivo (misma fecha, ronda previa). Es independiente de `planning/codex-review.md` y de la ronda de revisión ya incorporada en la propia §13 de `PLAN.md` (aprobada e integrada). Para los hallazgos de `codex-review.md` no repito su argumentación completa — solo confirmo, releyendo el `PLAN.md` actual línea por línea, si cada uno sigue abierto, quedó resuelto, o quedó resuelto solo parcialmente, y en ese caso señalo exactamente qué falta. El grueso del esfuerzo se dedica a hallazgos nuevos, sobre todo en las partes aún no construidas (base de datos, cartera, LLM, frontend, Docker), donde una ambigüedad ahora es barata de resolver y cara de resolver a mitad de implementación.

Para el componente de datos de mercado (ya implementado) inspeccioné el código real en `backend/app/market_data/` (los 10 módulos: `types.py`, `base.py`, `cache.py`, `simulator_config.py`, `correlation.py`, `simulator.py`, `massive_config.py`, `massive_client.py`, `factory.py`, `wiring.py`), no solo `planning/market_data_design.md`, porque diseño e implementación ya han divergido en algún punto y el resto del sistema va a depender del código real. También confirmé el estado de `backend/pyproject.toml` (solo `httpx` como dependencia hoy — ni `fastapi`, `uvicorn`, `sse-starlette`, `pydantic`, `litellm` ni `python-dotenv` están declaradas todavía) y que no existe aún ningún `main.py`, módulo `db/` ni `routes/` en `backend/app/` — es decir, la integración descrita en `market_data_design.md` §8-9 (lifespan, endpoint SSE) sigue siendo solo diseño, no código.

---

## Parte A — Verificación de los hallazgos de `codex-review.md` contra el `PLAN.md` actual

| # Codex | Hallazgo | Estado en `PLAN.md` actual |
|---|---|---|
| 1 | Contratos de respuesta/error de la API | **Sigue abierto.** §8 solo enumera rutas; no hay códigos de estado, formas de error ni criterios de idempotencia para `POST`/`DELETE` repetidos. |
| 2 | Atomicidad y precio fresco en la ejecución de trades | **Sigue abierto.** §7/§8/§9 no definen transacción ni ventana de frescura de precio. |
| 3 | `REAL` para dinero (efectivo, coste, P&L) | **Sigue abierto.** §13 solo fijó el redondeo de `quantity` a 4 decimales; `cash_balance`, `avg_cost`, `price`, `total_value` continúan como `REAL` sin regla de redondeo/tolerancia documentada. |
| 4 | "% de cambio diario" no derivable de la caché | **Sigue abierto.** §6 sigue describiendo la caché solo con precio actual, precio anterior y timestamp; no hay `previous_close`/`session_open`. Ver hallazgo B.5 más abajo para una propuesta concreta. |
| 5 | Ciclo de vida de tickers (`ensure_ticker`, retirada del proveedor) | **Parcialmente resuelto.** §13 fijó la siembra de `watchlist ∪ positions` en el `lifespan` de arranque (resuelve el caso "reinicio de contenedor"). Sigue sin resolver el caso de **runtime**: qué hace exactamente `POST /api/watchlist` y `POST /api/portfolio/trade` cuando el ticker es nuevo para el proceso en marcha (¿llaman a `provider.add_ticker()` antes de responder? ¿esperan a tener precio?), y si un ticker retirado de la watchlist sin posición abierta se retira también del proveedor (`remove_ticker`) o queda simulándose indefinidamente sin que nadie lo lea. |
| 6 | Carrera en la inicialización lazy de SQLite | **Sigue abierto.** §7 mantiene la redacción "al arrancar (o en la primera solicitud)", que es exactamente la ambigüedad que Codex señala. Nota: el propio módulo de datos de mercado ya adoptó el patrón "todo en `lifespan` antes de aceptar tráfico" (`ensure_db_initialized()` en el fragmento de `market_data_design.md` §8) — es la respuesta natural y ya coherente con el precedente del código existente; falta solo declararlo como decisión en §7. |
| 7 | Eventos SSE operativos (heartbeat, id, forma exacta) | **Sigue abierto en `PLAN.md` como contrato**, aunque `market_data_design.md` §9 ya *implementa* heartbeat (evento `ping` cada 15s) en el ejemplo de código — pero ese archivo es un documento de diseño para el agente de mercado, no una decisión ratificada en el `PLAN.md` que el agente de Backend/API vaya a leer como fuente de verdad. `routes/stream.py` todavía no existe en `backend/app/`. |
| 8 | Falta `GET` para leer el historial de chat | **Sigue abierto.** §8 no lo incluye. |
| 9 | No determinismo de `ORDER BY created_at` | **Sigue abierto.** §9 mantiene literalmente `ORDER BY created_at DESC LIMIT 20` sin desempate. |
| 10 | Dependencia de la skill `cerebras-inference` no versionada / sin contrato de fallos | **Sigue abierto, y con un problema adicional concreto** — ver hallazgo C.1 más abajo: el nombre real de la skill instalada en el repo es `cerebras`, no `cerebras-inference` como dice `PLAN.md` §9. |

Conclusión de la Parte A: de los 10 hallazgos prioritarios de Codex, **9 siguen completamente abiertos** y **1 (ciclo de vida de tickers) está solo parcialmente resuelto**. Ninguno de los "ajustes menores" de Codex (paginación de `/api/portfolio/history`, timezone `Z`, límite de tamaño de mensajes/acciones de chat) fue incorporado tampoco. Esto no es un fallo de la ronda de revisión de §13 — esa ronda tenía un alcance distinto y ya cerrado — pero significa que estos puntos siguen siendo bloqueantes reales para los agentes de Backend/Cartera/LLM y deberían resolverse en el documento antes de que ese trabajo arranque en firme.

---

## Parte B — Hallazgos nuevos

### Bloque 1 — Interfaz de datos de mercado que el resto del sistema va a consumir

#### B.1 `add_ticker()` no entrega un precio de forma síncrona — y en modo Massive puede no entregarlo nunca

`MarketDataProvider` (`backend/app/market_data/base.py`) expone solo `start`, `stop`, `add_ticker`, `remove_ticker` y la propiedad `tickers`. Inspeccionando ambas implementaciones:

- **Simulador** (`simulator.py::add_ticker`): fija `self._prices[ticker]` de forma síncrona, pero **no** llama a `_emit()` ni escribe en `price_cache` — ese precio no es visible fuera del proceso hasta el siguiente `tick_once()` (hasta 500ms después, `TICK_INTERVAL_SECONDS`).
- **Massive** (`massive_client.py::add_ticker`): solo añade el ticker a `self._tickers` (un `set`); el precio no llega hasta el siguiente `poll_once()` del `_run_loop` (hasta `MASSIVE_POLL_INTERVAL_SECONDS`, 15s en el nivel gratuito).
- Ninguna de las dos implementaciones tiene un método síncrono en la interfaz abstracta para "dame el precio ahora o dime que no existe". `MarketSimulator.current_price()` existe pero **no está en `base.py`**, así que no es parte del contrato agnóstico a la fuente que la capa de Cartera podría usar.

Esto afecta directamente a `POST /api/watchlist` y `POST /api/portfolio/trade` (§8), ambos explícitamente abiertos a tickers no vistos antes (§13, "¿Se puede operar con tickers fuera de la watchlist?" → sí). Hay además un caso más grave que la mera latencia: en **modo Massive**, si el ticker no existe realmente en NYSE/NASDAQ (typo del usuario, o un ticker alucinado por el LLM pese a la instrucción del prompt de §9), la respuesta de snapshot de Massive simplemente nunca incluirá una entrada para él — `price_cache` nunca tendrá un precio para ese símbolo, **no es un retraso, es una ausencia permanente**. Sin un timeout/contrato explícito, un handler que espere "hasta que aparezca un precio" se colgaría indefinidamente.

**Recomendación:**
1. Añadir `get_last_price(ticker: str) -> float | None` a `MarketDataProvider` (interfaz abstracta), implementado en ambas clases sobre su estado interno (`self._prices` / `self._prev_prices` o consultando `price_cache` directamente).
2. Simulador: que `add_ticker()` llame a `_emit()` inmediatamente con el precio semilla recién asignado (cambio de una línea), eliminando la ventana de 500ms.
3. Massive: documentar y aplicar un **timeout explícito** (p. ej. 5-10s) al esperar el primer precio de un ticker recién añadido, tras el cual el endpoint responde `422`/`503` (ver B.4) con un mensaje claro ("símbolo no reconocido o sin datos disponibles"), en lugar de bloquear la petición o de aceptar silenciosamente una operación sin precio.

#### B.2 Convención de timestamp: el código real ya fija un formato que los documentos de diseño no siguen

`PriceTick.create()` (`backend/app/market_data/types.py:32`) usa `datetime.now(timezone.utc).isoformat()`, que produce sufijo `+00:00` y precisión de microsegundos (p. ej. `2026-08-14T10:15:30.512847+00:00`). El ejemplo de evento SSE en `market_data_design.md` §9 muestra en cambio `"timestamp":"2026-06-23T10:15:30.512Z"` (sufijo `Z`, milisegundos) — el propio documento de diseño ya diverge de la implementación que él mismo especificó. Esto importa ahora porque Codex recomienda (acertadamente, en abstracto) fijar `Z` como convención para las tablas nuevas — pero adoptar `Z` allí mientras el módulo de mercado ya en producción usa `+00:00` deja al proyecto con **dos convenciones de timestamp conviviendo sin necesidad**.

**Recomendación:** que `PLAN.md` fije explícitamente una única convención para todo el proyecto (backend nuevo incluido) igual a la que ya usa el código de mercado: `datetime.now(timezone.utc).isoformat()` (offset `+00:00`). Es funcionalmente equivalente a `Z` para cualquier parser ISO-8601, incluido `new Date(...)` en JS/TypeScript del frontend. Si se prefiere `Z` por legibilidad, hay que decidirlo ahora y actualizar `types.py` en consecuencia — pero la decisión debe tomarse una vez, no dejar que cada tabla nueva la reinvente.

---

### Bloque 2 — Base de datos y Cartera

#### B.3 Fórmula de `avg_cost` no especificada

El esquema de `positions` (§7) tiene `avg_cost`, y §7/§10 mencionan "reconstruir `avg_cost`" y "coste medio" respectivamente, pero en ningún punto se fija la fórmula. Coste medio ponderado, FIFO y LIFO dan resultados distintos para la misma secuencia de operaciones, y el esquema actual (una sola fila `avg_cost` por posición, sin tabla de lotes) solo es compatible con uno de los tres.

**Recomendación:** fijar explícitamente **coste medio ponderado**, el único método coherente con el esquema actual:

```
nueva_qty = qty_actual + qty_comprada
avg_cost_nuevo = (qty_actual * avg_cost_actual + qty_comprada * precio_ejecucion) / nueva_qty
```

Una venta no modifica `avg_cost` de la posición restante (solo reduce `quantity`); el P&L realizado de esa venta (`qty_vendida * (precio_ejecucion - avg_cost_actual)`) no necesita persistirse en un campo nuevo — es reconstruible desde `trades` si algún día se necesita. Documentar esto en §7 evita que dos agentes implementen dos matemáticas distintas.

#### B.4 Contrato de error para "no hay precio utilizable" no está definido en ningún punto

Relacionado con B.1 pero es un hallazgo de contrato de API, no de datos de mercado: ni §8 ni §9 dicen qué código HTTP / forma de error devuelve `POST /api/portfolio/trade` cuando el ticker pasa la validación de formato (`^[A-Z]{1,5}$`) pero no tiene un precio disponible en `price_cache` (ticker recién añadido en modo Massive, o símbolo inexistente). Codex ya señala la falta general de contratos de error (su hallazgo 1); esto es el caso concreto más importante porque **sin un código reservado para "precio no disponible"**, el agente de Backend tendrá que inventarlo (probablemente reutilizando `400` o `404`, que ya tendrían otro significado en el mismo endpoint).

**Recomendación:** reservar `503 Service Unavailable` específicamente para "el ticker es válido en formato pero no hay un precio actual utilizable" (coherente con la sugerencia de Codex en su hallazgo 1), distinto de `400` (formato inválido), `404` (recurso no encontrado, p. ej. `DELETE` de un ticker que no está en watchlist si se decide que eso es un error) y `409`/`422` (validación de negocio: fondos o acciones insuficientes). Documentar esta tabla completa en §8.

#### B.5 Propuesta concreta para el "% de cambio diario" (profundiza el hallazgo 4 de Codex, que sigue abierto)

Más allá de confirmar que el hallazgo de Codex sigue sin resolver (Parte A), aporto una propuesta concreta porque toca directamente el código ya construido en `cache.py`/`types.py`, no solo el `PLAN.md`:

- **Simulador:** no existe el concepto de "sesión de mercado" (GBM continuo, sin apertura/cierre). Recomendación: capturar el precio en el primer `tick_once()` tras el arranque del proceso (o en el momento de `add_ticker()` para tickers añadidos después) como `session_open`, y mantenerlo fijo durante toda la vida del proceso (o resetearlo con un temporizador de 24h simuladas si se quiere más realismo — innecesario para un curso). Es un `dict[str, float]` adicional junto a `self._prices` en `MarketSimulator`, trivial de añadir.
- **Massive:** el snapshot real de Polygon/Massive ya incluye `prevDay.c` (cierre del día anterior) — `massive_client.py::_parse_response` ya lo lee como *fallback de precio* (línea 114) pero no lo expone como referencia de "cambio diario". Recomendación: capturar `prevDay.c` por separado como `session_open` en el mismo parseo.
- Añadir `session_open: float` a `CachedPrice` (`cache.py`) y al payload `to_sse_dict()` (`types.py`), y documentar en §6/§10 que "% de cambio" en la UI se calcula como `(price - session_open) / session_open`, no como `(price - prev_price) / prev_price` (que sería el cambio del último tick, no el diario).

Esto es un cambio de código real en un módulo ya revisado y dado por completo (`market_data_review.md`) — vale la pena señalarlo explícitamente para que el agente que lo toque sepa que está extendiendo, no rehaciendo, un componente ya aprobado.

#### B.6 Ejecución de varios trades del LLM en una misma respuesta: validar contra estado vivo, no contra el snapshot de contexto

§9 carga el contexto de cartera en el paso 1 y ejecuta las operaciones de `trades` en el paso 6. Cuando `trades` trae más de un elemento (p. ej. vender AAPL y comprar TSLA en la misma respuesta), no está especificado si la validación de "efectivo suficiente" para la segunda operación usa el `cash_balance` cargado en el paso 1 (antes de aplicar la primera) o el estado real tras aplicar la primera. Con el snapshot del paso 1, una compra que ya no tiene fondos suficientes (porque la venta previa del mismo lote aún no se había contabilizado en ese snapshot) podría validarse incorrectamente. Esto es un caso más específico que el hallazgo general de atomicidad de Codex (su #2): no es solo "todo o nada vs. por elemento", sino **qué dato de partida usa cada validación individual dentro del lote**.

**Recomendación:** cada trade (manual o del LLM) se valida y ejecuta contra el estado leído de la base de datos **en el instante de ejecutar ese trade concreto**, nunca contra el contexto cargado al inicio del turno de chat (que es solo contexto para el LLM). Combinado con "una transacción SQLite por trade, ejecutada en orden, cada una leyendo el estado más reciente" (ya sugerido por Codex), esto resuelve el problema de forma natural sin necesitar lógica especial de lote.

#### B.7 Base de normalización del peso en el treemap

§10 dice que el treemap dimensiona los rectángulos "por peso en la cartera" sin decir sobre qué base se normaliza: ¿`cash + posiciones` o solo `suma de posiciones`? Con la cartera semilla (10.000 $ en efectivo, sin posiciones) es indiferente, pero en cuanto haya inversión parcial, la primera interpretación deja "espacio vacío" no representable (el cash no tiene rectángulo propio) y la segunda siempre llena el área visible.

**Recomendación:** normalizar sobre la suma de valores de mercado de las posiciones abiertas únicamente (excluyendo cash del denominador) — comportamiento estándar de un treemap de cartera. Documentar el caso trivial: sin posiciones abiertas, el treemap está vacío por diseño (no es un bug del primer lanzamiento).

#### B.8 Falta la regla explícita `quantity > 0`

§13 fijó el redondeo a 4 decimales para `quantity` pero no una cota inferior ni la regla `quantity > 0` de forma explícita (se infiere, pero es exactamente el tipo de regla que un agente de Backend y uno de Frontend podrían implementar de forma distinta si no está escrita).

**Recomendación:** añadir a §8 y §9 la regla: `quantity` estrictamente positiva tras redondear a 4 decimales; `quantity <= 0` se rechaza con el código de error de B.4/validación de negocio, tanto en `POST /api/portfolio/trade` como en cada elemento de `trades` del LLM.

#### B.9 Concurrencia de escritura SQLite en estado estable (no solo en la inicialización)

Codex señala la carrera en la inicialización lazy (su #6, confirmado abierto en Parte A). Hay un problema relacionado pero distinto en **estado estable**: una vez arrancada la app conviven la tarea periódica de `portfolio_snapshots` (cada 30s, §7), el handler de `POST /api/portfolio/trade` (que escribe `users_profile`, `positions`, `trades` y un snapshot en la misma operación) y posibles peticiones concurrentes (doble clic, o el LLM ejecutando varios trades). SQLite en modo `journal` por defecto serializa escritores y puede devolver `database is locked` bajo esta concurrencia incluso dentro de un único proceso si las conexiones no se coordinan.

**Recomendación:** activar `PRAGMA journal_mode=WAL` al inicializar la base de datos, y usar una única conexión de escritura (o una cola/lock a nivel de aplicación) para las operaciones que mutan estado, de forma que la tarea de snapshot y los handlers de trade nunca compitan sin coordinación. Barato de fijar ahora como convención en §7.

---

### Bloque 3 — Integración con el LLM

#### C.1 El nombre de la skill en `PLAN.md` no coincide con la skill instalada — riesgo concreto de bloqueo para el agente de LLM

§9 instruye: *"usa la skill cerebras-inference para utilizar LiteLLM a través de OpenRouter..."*. Verifiqué la skill realmente disponible en el repo (`.claude/skills/cerebras/`, invocable como `cerebras`): **se llama `cerebras`, no `cerebras-inference`**. Es una discrepancia de nombre exacta y accionable, no una cuestión de interpretación — un agente que busque literalmente "cerebras-inference" en el listado de skills no la encontrará por ese nombre.

Adicionalmente, revisando el contenido real de la skill:
- El modelo fijado es `openrouter/openai/gpt-oss-120b` (coincide con §9).
- La preferencia de proveedor se pasa como `extra_body = {"provider": {"order": ["cerebras"]}}` — esto es un **orden de preferencia**, no una restricción exclusiva. Por defecto, OpenRouter puede recurrir a otro proveedor si Cerebras no está disponible en ese momento, salvo que se añada `"allow_fallbacks": false` dentro de `"provider"`. Si el objetivo (§3: "Cerebras para inferencia rápida") es una decisión de rendimiento importante para la demo, vale la pena decidir explícitamente si el fallback silencioso a otro proveedor es aceptable o no.
- La salida estructurada se invoca con `response_format=MyBaseModelSubclass` (una clase Pydantic), lo que encaja bien con la recomendación de usar `Literal["buy","sell"]` / `Literal["add","remove"]` / cantidades positivas directamente en el modelo Pydantic del esquema de §9, reforzando la validación en el propio proveedor además de en el backend.

**Recomendación:**
1. Corregir en `PLAN.md` §9 el nombre de la skill a `cerebras` (el nombre real), o renombrar la skill si `cerebras-inference` era el nombre pretendido — pero deben coincidir.
2. Decidir explícitamente si se añade `"allow_fallbacks": false` al `extra_body` para garantizar que solo Cerebras sirve la inferencia, o si se acepta el fallback automático de OpenRouter como comportamiento de resiliencia deseado; documentarlo en §9.
3. Añadir `litellm` y `pydantic` a `backend/pyproject.toml` (hoy solo tiene `httpx`) junto con el resto de dependencias nuevas del backend (`fastapi`, `uvicorn[standard]`, `sse-starlette`, `python-dotenv`) — ninguna está declarada todavía.
4. Definir el modelo Pydantic de la respuesta estructurada (`message`, `trades[]`, `watchlist_changes[]`) con restricciones de tipo (`Literal` para `side`/`action`, cantidad positiva) directamente en §9, reutilizando el ejemplo de la skill.

#### C.2 Contrato de fallos del LLM no definido (confirma y concreta el hallazgo 10 de Codex)

Ni §9 ni ningún otro punto de `PLAN.md` especifican qué responde `POST /api/chat` si la llamada a OpenRouter/Cerebras falla (timeout, error de red, clave inválida) o si la respuesta no es JSON válido / no cumple el esquema Pydantic.

**Recomendación:** definir explícitamente: timeout de la llamada (p. ej. 30s), cero reintentos automáticos (mantiene la demo simple y predecible), y en caso de fallo devolver un `message` de error conversacional seguro al usuario ("No pude procesar tu solicitud, inténtalo de nuevo") sin ejecutar ninguna acción (`trades`/`watchlist_changes` vacíos), persistiendo igualmente el mensaje del usuario en `chat_messages` pero con la respuesta de error en vez de contenido del LLM.

#### C.3 Regla de mapeo mensaje→respuesta en `LLM_MOCK=true` no definida

§9 dice que en modo mock el backend "devuelve respuestas simuladas deterministas", pero no especifica cómo se determina qué respuesta corresponde a qué mensaje de usuario. El escenario E2E de §12 ("Chat de IA (simulado): enviar un mensaje, recibir una respuesta, la ejecución de la operación aparece en línea") solo es escribible si el test conoce ese mapeo de antemano.

**Recomendación:** fijar en §9 una regla simple por palabras clave (case-insensitive), por ejemplo: mensaje que contiene "compra"/"buy" + un ticker reconocible → `trades` con una compra fija de 1 acción de ese ticker; "vende"/"sell" + ticker → venta análoga; "añade"/"add" + ticker → `watchlist_changes` con `add`; cualquier otro mensaje → respuesta conversacional sin acciones. No requiere sofisticación, solo ser documentado y estable.

---

### Bloque 4 — Frontend

#### D.1 Normalización de mayúsculas en el input de ticker no especificada

§8 fija el formato de ticker como `^[A-Z]{1,5}$` (solo mayúsculas) para `POST /api/watchlist` y `POST /api/portfolio/trade`. §10 no dice si el campo de texto del frontend (barra de operaciones, formulario de watchlist) normaliza a mayúsculas antes de enviar, o si un usuario que escribe "aapl" recibe un `400` confuso sin explicación visible de por qué.

**Recomendación:** el frontend debe convertir el input a mayúsculas en tiempo real (o al menos antes de enviar la petición) para los campos de ticker, de forma que la regex del backend nunca sea la causa visible de un error evitable. Documentar esto como nota de UX en §10.

#### D.2 Estado inicial del área de gráfico principal

§10 dice que el gráfico principal "arranca vacío" y se llena al hacer clic en un ticker — pero no dice qué se ve entre la carga de la página y el primer clic: ¿un placeholder, ejes vacíos, o el primer ticker de la watchlist ya seleccionado? Dado que §2 describe el primer lanzamiento como una experiencia cuidada ("visualmente espectacular"), dejarlo sin definir es el tipo de vacío que un agente de Frontend llenaría de forma arbitraria.

**Recomendación:** seleccionar automáticamente el primer ticker de la watchlist (p. ej. AAPL en el estado semilla) al cargar la página, coherente con "inmediatamente ve... precios actualizándose en vivo" (§2).

---

### Bloque 5 — Docker y despliegue

#### E.1 `/api/health` sin contrato real y sin `HEALTHCHECK` en el Dockerfile

§8 define `GET /api/health` como "comprobación de estado" y §11 menciona el Dockerfile multi-etapa, pero no hay instrucción `HEALTHCHECK` en el esqueleto ni se especifica qué debe comprobar el endpoint más allá de existir. Un `/api/health` que devuelve `200` incondicionalmente no detecta el fallo más probable del proyecto: el contenedor arranca pero el proveedor de datos de mercado nunca llegó a iniciarse (excepción en `lifespan`), y el usuario ve una watchlist sin precios sin que Docker lo marque como `unhealthy`.

**Recomendación:** `/api/health` debe comprobar como mínimo que SQLite responde (`SELECT 1`) y que `app.state.market_data_provider` existe y está corriendo; devolver `503` si algo falla. Añadir `HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1` al Dockerfile en §11 (evita depender de `curl`, que `python:3.12-slim` no trae por defecto).

#### E.2 Orden de registro de rutas: `/api/*` frente al montaje estático

§3/§11 sirven `/api/*` y los archivos estáticos del export de Next.js bajo el mismo puerto y proceso, pero no se especifica el orden de registro. Si `StaticFiles` se monta antes que los routers de `/api/*` (o con un patrón demasiado amplio), una ruta de API mal registrada podría quedar "tapada" y devolver un 404 de archivo estático en lugar de llegar al handler real.

**Recomendación:** documentar en §11 que los `APIRouter` de `/api/*` se registran antes que el montaje de `StaticFiles`, y que este último se monta en `/` después de incluir todos los routers. Al ser un export estático de una sola página sin rutas de cliente adicionales, un 404 real para cualquier ruta no reconocida fuera de `/api/*` es aceptable — no hace falta un fallback tipo "todo sirve `index.html`".

#### E.3 Sin mecanismo ni documentación de reinicio de la demo

El volumen `db/` persiste entre reinicios (decisión correcta para uso normal), pero el proyecto es explícitamente material de demo de un curso (§1). No hay mención de cómo volver a un estado limpio ($10.000, sin posiciones, watchlist por defecto) antes de una demo.

**Recomendación:** no construir un endpoint de reset en la v1. Basta documentar en §11 una línea: "para reiniciar el estado a los valores por defecto, detener el contenedor y borrar `db/finally.db`; la inicialización lazy (§7) lo regenerará limpio en el siguiente arranque." Opcional (no bloqueante): un flag `--reset` en los scripts de inicio.

---

### Bloque 6 — Testing

#### F.1 El escenario E2E "desconectar y verificar la reconexión" depende de un contrato SSE que aún no está en `PLAN.md`

§12 incluye el escenario "Resiliencia del SSE: desconectar y verificar la reconexión", pero como se confirma en la Parte A (ítem 7), `PLAN.md` no define heartbeat, `id` de evento, ni una forma simulable de "cortar" la conexión desde un test E2E sin depender de fallos de red reales.

**Recomendación:** promover a `PLAN.md` §6 el contrato de heartbeat que ya existe como ejemplo en `market_data_design.md` §9 (evento `ping` cada `HEARTBEAT_SECONDS`), y definir explícitamente cómo el test E2E provoca la desconexión de forma determinista — por ejemplo, cerrando la conexión HTTP subyacente desde Playwright (`page.route` con abort, o cerrando el contexto de red) en vez de depender de un corte real de red.

---

## Resumen priorizado

| # | Hallazgo | Bloque | Urgencia |
|---|---|---|---|
| A.1–A.10 | 9 de los 10 hallazgos de `codex-review.md` siguen completamente abiertos en `PLAN.md` (contratos de error, atomicidad/precio fresco, `REAL` para dinero, % diario, init lazy, SSE operativo, GET de chat history, orden no determinista, dependencia LLM sin versionar) | Transversal | **Alta** — bloquean el arranque serio de Backend/Cartera/LLM |
| B.1 | `add_ticker()` sin precio síncrono; en Massive puede ser ausencia *permanente*, no solo retraso | Datos de mercado / Cartera | Alta |
| B.4 | Falta código de error reservado para "sin precio disponible" en trade | Cartera / API | Alta |
| B.3 | Fórmula de `avg_cost` no especificada | Base de datos | Alta |
| B.6 | Validar cada trade del LLM contra estado vivo, no snapshot de contexto, en lotes multi-acción | Cartera / LLM | Alta |
| C.1 | Nombre de skill `cerebras-inference` no coincide con la skill real `cerebras`; dependencias LLM ausentes de `pyproject.toml` | LLM | Alta — bloqueo literal si un agente busca la skill por el nombre del `PLAN.md` |
| B.9 | Concurrencia de escritura SQLite en estado estable (WAL, conexión única de escritura) | Base de datos | Media |
| B.5 | Propuesta concreta de `session_open` para "% de cambio diario" (toca código ya construido) | Datos de mercado / Frontend | Media |
| C.2 | Contrato de fallos del LLM (timeout, error de red, JSON inválido) no definido | LLM | Media |
| C.3 | Mapeo mensaje→respuesta en `LLM_MOCK` no definido | LLM / Testing | Media |
| B.7 | Base de normalización del peso del treemap | Frontend / Cartera | Media |
| B.8 | Falta regla explícita `quantity > 0` | Cartera / LLM | Media |
| E.1 | `/api/health` sin contrato real + falta `HEALTHCHECK` en Dockerfile | Docker | Media |
| F.1 | Escenario E2E de reconexión SSE sin contrato de heartbeat/desconexión simulable | Testing | Media |
| B.2 | Convención de timestamp: reutilizar la ya implementada (`+00:00`), no introducir `Z` en paralelo | Base de datos | Media |
| D.1 | Normalización de mayúsculas del ticker en el input del frontend | Frontend | Baja |
| D.2 | Estado inicial del gráfico principal sin definir | Frontend | Baja |
| E.2 | Orden de registro de rutas API vs. estáticos sin documentar | Docker | Baja |
| E.3 | Sin mecanismo/documentación de reinicio de la demo | Docker / Operación | Baja |
