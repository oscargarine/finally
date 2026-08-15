# Revisión de `plan.md`

Fecha: 2026-08-14

El plan define bien la experiencia objetivo y ya incorpora varias aclaraciones útiles. Antes de continuar con la implementación de cartera, API y UI, quedan las siguientes decisiones de contrato. Se recomienda resolverlas en el documento fuente y no dejar que cada agente las infiera de forma distinta.

## Hallazgos prioritarios

### 1. Falta especificar los contratos de respuesta y errores de la API

La sección 8 enumera rutas, pero no define cuerpos de respuesta, códigos de estado ni el formato uniforme de error. Esto bloquea el desacoplamiento frontend/backend y hace que los tests de rutas sean ambiguos.

**Recomendación:** para cada endpoint, añadir ejemplos o esquemas de éxito y error, y fijar como mínimo: `400` para payload/formato inválido, `404` para recursos inexistentes, `409` o `422` para una operación que no puede ejecutarse (saldo/acciones insuficientes), y `503` si no hay un precio actual utilizable. Definir también si `POST /api/watchlist` repetido y `DELETE` de un ticker inexistente son idempotentes o devuelven error.

### 2. La ejecución de operaciones necesita semántica transaccional y de precio fresco

Una operación modifica efectivo, posición, historial, y genera un snapshot. El plan no determina la unidad atómica ni qué ocurre cuando el LLM devuelve varias acciones y una de ellas falla. Tampoco define cuánto tiempo puede tener el precio de caché al ejecutar una orden, especialmente con Massive sondeando cada 15 segundos.

**Recomendación:** ejecutar cada trade en una única transacción SQLite que lea un precio con timestamp, valide, actualice `users_profile` y `positions`, inserte `trades` y cree el snapshot. Rechazar precios ausentes o más antiguos que un límite documentado. Para acciones múltiples del chat, definir explícitamente ejecución independiente en orden (con resultado por acción, la opción que mejor encaja con `actions`) o ejecución todo-o-nada; no dejarlo implícito.

### 3. `REAL` no es apropiado como fuente de verdad para efectivo, coste y P&L

El redondeo a cuatro decimales de cantidades es una buena decisión, pero efectivo, precio, coste medio, valor y P&L continúan definidos como `REAL`. Los errores binarios pueden provocar validaciones de saldo inconsistentes y diferencias visibles entre tabla, cabecera y snapshot.

**Recomendación:** usar `Decimal` en la lógica de dominio y persistir importes como enteros de escala fija (por ejemplo, microdólares) o como texto decimal canónico. Si se conserva `REAL` por simplicidad didáctica, documentar una regla única de redondeo y tolerancia para cada cálculo y validación.

### 4. El “% de cambio diario” no puede obtenerse de la caché descrita

La caché sólo conserva precio actual, precio anterior y timestamp. Eso permite indicar la dirección del último tick, pero no calcular un cambio diario. Mostrar el último cambio como si fuese diario sería incorrecto, y Massive/simulador no tendrían el mismo contrato.

**Recomendación:** añadir `previous_close` (o un `session_open` explícitamente simulado) al modelo de precio y al evento SSE; o cambiar el requisito de UI a “cambio desde el último tick/sesión”. Definir cómo se inicializa dicho valor para tickers añadidos dinámicamente.

### 5. Faltan reglas de ciclo de vida para tickers añadidos y retirados

El plan indica que un ticker con posición debe seguir recibiendo precios, pero no concreta el flujo en `POST /api/watchlist` y `POST /api/portfolio/trade`: deben crear/obtener un precio antes de responder, registrar el ticker en el proveedor y evitar una carrera con el stream. Tampoco define si un ticker eliminado sin posición se elimina de la simulación/caché.

**Recomendación:** establecer una operación de dominio `ensure_ticker(ticker)` usada tanto por watchlist como por trade, que garantice precio inicial antes de exponer o ejecutar la operación. Mantener en el proveedor los tickers de `watchlist ∪ positions`; retirar los demás de forma explícita (o documentar una caché con TTL).

## Hallazgos importantes

### 6. Hay una carrera potencial en la inicialización “lazy” de SQLite

El plan permite inicializar al arranque *o* en la primera solicitud. Dos primeras solicitudes concurrentes (por ejemplo, carga inicial y SSE) pueden intentar crear/escribir semillas a la vez.

**Recomendación:** preferir inicialización durante el `lifespan` antes de aceptar tráfico; hacer el esquema y las semillas idempotentes mediante una transacción y restricciones únicas. Si se conserva el modo lazy, protegerlo con un lock del proceso y una transacción de inicialización.

### 7. El contrato SSE necesita eventos operativos, no sólo ticks

Para una conexión de larga duración faltan heartbeat/keepalive, `id` de evento o estrategia de reanudación, forma JSON exacta, y el comportamiento cuando un ticker entra o sale de la unión atendida. Esto también vuelve poco definido el escenario E2E de “desconectar y verificar reconexión”.

**Recomendación:** documentar eventos `price` con un esquema JSON versionado, heartbeat periódico, intervalo/reintento SSE y el estado que recibe un cliente recién conectado. Incluir una forma verificable de simular el corte en E2E, sin depender de fallos de red reales.

### 8. El historial de chat carece de endpoint de lectura

La interfaz requiere “historial de conversación con desplazamiento”, pero sólo existe `POST /api/chat`. Tras recargar la página no hay contrato para reconstruirlo desde `chat_messages`.

**Recomendación:** añadir `GET /api/chat/messages` (con límite y orden definidos) o declarar que el historial sólo vive en memoria del navegador. Dado que ya se persiste la tabla, el endpoint de lectura es la opción consistente.

### 9. El orden por `created_at` puede no ser determinista

El contexto LLM se carga con `ORDER BY created_at DESC LIMIT 20`; varias inserciones dentro del mismo instante pueden compartir timestamp textual y alterar el orden de conversación.

**Recomendación:** usar timestamps UTC de precisión suficiente y un desempate estable (`ORDER BY created_at DESC, id DESC`), o una columna de secuencia. Al reconstruir el prompt, invertir los 20 resultados para enviarlos en orden cronológico.

### 10. La dependencia indicada para LLM no aparece como parte del contrato del repositorio

El plan exige la skill `cerebras-inference`, pero no está descrita en la estructura del proyecto ni se define el comportamiento si LiteLLM/OpenRouter no está disponible (clave ausente, timeout, salida no válida).

**Recomendación:** sustituir esa referencia por dependencias versionadas en `backend/pyproject.toml` y un contrato de fallos: timeout, reintentos si aplica, mensaje seguro para el usuario y ninguna acción ejecutada cuando el parseo/validación de la respuesta falle. Mantener `LLM_MOCK=true` como ruta de pruebas determinista.

## Ajustes menores

- Aclarar una única capitalización para el documento: el árbol dice `planning/PLAN.md`, mientras que el archivo existente es `planning/plan.md`; en sistemas sensibles a mayúsculas la referencia actual falla.
- Definir paginación/límite y orden de `GET /api/portfolio/history`, para que el gráfico no cargue snapshots sin límite en una base persistente de larga vida.
- Fijar el timezone y formato de todos los timestamps como UTC ISO-8601 con sufijo `Z`.
- Considerar una política de límite para el tamaño de mensajes de chat y el número de acciones permitidas por respuesta del LLM, para impedir que una respuesta válida pero excesiva bloquee la transacción o la UI.

## Conclusión

La base funcional está bien delimitada. Las decisiones más urgentes son los contratos API, la atomicidad/precio de las operaciones, la precisión monetaria y la definición real del cambio diario. Resolverlas antes de implementar evita discrepancias visibles y pruebas frágiles.
