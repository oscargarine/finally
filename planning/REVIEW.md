# Revisión de cambios desde `HEAD`

Fecha: 2026-08-14

## Hallazgos

### Alta — el timeout de 8 s hace fallar sistemáticamente los tickers nuevos con Massive

`PLAN.md` §6 dice que Massive puede tardar hasta el intervalo completo de sondeo (15 s por defecto) para obtener el primer precio, pero fija un timeout de solo 8 s en `ensure_ticker()`. `MassiveMarketDataProvider` sondea inmediatamente al arrancar y después duerme `MASSIVE_POLL_INTERVAL_SECONDS`; un ticker añadido durante esa espera no se incluirá hasta el siguiente sondeo. Por tanto, con la configuración predeterminada, un ticker válido añadido en runtime puede recibir siempre `503` aunque Massive esté sano.

Definir una de estas semánticas antes de implementar: disparar un sondeo inmediato y coordinado al añadir el ticker; usar un timeout mayor o igual al intervalo de sondeo más el tiempo de red; o separar el timeout de alta de watchlist del de ejecución de órdenes. Además, el límite debe configurarse de forma coherente con `MASSIVE_POLL_INTERVAL_SECONDS`.

### Alta — el contrato nuevo de datos de mercado contradice el documento de diseño y el código existente

El nuevo `PLAN.md` exige `MarketDataProvider.get_last_price()`, emisión inmediata al hacer `add_ticker()` en el simulador y `session_open` en `CachedPrice` y en cada evento SSE. Sin embargo, `planning/market_data_design.md` conserva la interfaz sin `get_last_price`, la estructura de caché sin `session_open` y los fragmentos de `PriceTick`/SSE sin ese campo. El código actual bajo `backend/app/market_data/` coincide con el diseño antiguo: `MarketSimulator.add_ticker()` no emite un tick, `MassiveMarketDataProvider` no expone el último precio, y `CachedPrice`/`PriceTick` no contienen `session_open`.

Actualizar conjuntamente `market_data_design.md`, los módulos de mercado y sus tests, o etiquetar de forma inequívoca los fragmentos antiguos como obsoletos. De otro modo, el documento que se presenta como contrato compartido permite dos implementaciones incompatibles.

### Media — siguen coexistiendo dos reglas opuestas para la inicialización de SQLite

La sección de límites clave de `PLAN.md` mantiene que `backend/db/` se inicializa de forma lazy "en la primera solicitud", mientras que §7 ahora prescribe correctamente hacerlo una vez en el `lifespan`, antes de aceptar tráfico. Ambas son instrucciones normativas para el mismo componente y la sección 14 afirma que la carrera ya fue resuelta.

Eliminar o reescribir la frase de la sección de límites clave para que solo quede el ciclo de vida en `lifespan`.

### Media — el contrato de API todavía deja decisiones incompatibles a criterio del implementador

La nueva tabla de errores dice que los endpoints de escritura usan códigos "de forma consistente", pero permite indistintamente `409 / 422` para efectivo o acciones insuficientes. El frontend y los tests no pueden depender de un resultado único. Tampoco se definen cuerpos de éxito para las rutas que se añadieron/refinaron, ni un límite para el número de acciones que el LLM puede devolver.

Elegir un único código para cada regla de negocio (por ejemplo, `409`), documentar los esquemas de éxito mínimos y fijar un máximo de `trades` y `watchlist_changes` por respuesta. Así se evita que una respuesta estructuralmente válida pero enorme monopolice el lock de escritura.

### Media — la regla del mock LLM no determina de forma fiable el ticker

La regla propone detectar el ticker con `[A-Z]{1,5}` en cualquier mensaje que contenga "buy"/"compra". En mensajes como `BUY 1 AAPL`, el primer texto que satisface el patrón puede ser `BUY`, no `AAPL`; además, se declara una comparación case-insensitive mientras el patrón indicado solo describe mayúsculas. Esto hace que el supuesto mapeo determinista de los E2E sea ambiguo.

Especificar una gramática inequívoca para el mock (por ejemplo, `buy|compra <TICKER>`), normalizar primero a mayúsculas y extraer el grupo capturado; incluir casos de prueba para comandos, palabras comunes y ticker ausente.

### Baja — la precisión de precios/dinero queda poco consistente

§7 indica redondear todos los valores monetarios a dos decimales al persistirlos, mientras que el proveedor ya crea precios a cuatro decimales y el esquema de `trades.price` no establece su precisión. Redondear el precio de ejecución a dos decimales pero mostrar/circular un precio de cuatro puede alterar el coste medio y el P&L de forma visible.

Definir explícitamente la precisión de precio de ejecución, `avg_cost`, P&L y snapshots, y usar esa misma regla tanto en el cálculo como en la persistencia. Si se conserva el precio a cuatro decimales, la regla general de dos decimales debe excluirlo expresamente.

### Baja — metadatos de agentes con nombre y responsabilidad incorrectos

`.claude/agents/gemini-reviewer.md` declara `name: Codex_Reviewer` y una descripción de Codex aunque ejecuta `gemini`. Además, los agentes de revisión escriben directamente documentos de `planning/` sin indicar qué hacer si la CLI externa no está disponible.

Corregir el nombre/descripción de Gemini y definir un fallo explícito o un fallback de revisión. Esto reduce confusión al invocar agentes y evita resultados parcialmente actualizados.

## Observaciones positivas

Los cambios aclaran de forma útil la inicialización de base de datos, la serialización de escrituras, el coste medio ponderado, el historial de chat, la normalización de tickers, el healthcheck y la recuperación del SSE. `planning/market_data_design.md` también corrige la base URL de Massive y la siembra inicial con posiciones abiertas.

No se detectaron errores de espacios en blanco aparte de una línea en blanco final adicional en `PLAN.md` (`git diff --check`). No se ejecutaron tests: los cambios son principalmente especificación y configuración de agentes, y los requisitos nuevos aún no están implementados en el código.
