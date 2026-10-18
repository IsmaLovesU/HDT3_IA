# Agente de citas y FAQs - Parachute S.A. (HDT7: MCP y A2A)

Agente de terminal para el evento de paracaidismo de Parachute S.A. (Guatemala, 29 de septiembre de 2026).
Responde preguntas del corpus de FAQs (RAG con pgvector, HDT4) y agenda citas revisando el pronóstico
de Open-Meteo antes de guardar cada cita.

Este repositorio contiene **tres implementaciones del mismo problema**, cada una con una arquitectura de
orquestación distinta:

| Programa | Arquitectura | Conexión entre agentes |
|---|---|---|
| `python centralizada.py` | Centralizada | Un supervisor llama a los especialistas con `as_tool()` |
| `python jerarquica.py` | Jerárquica | Un supervisor general delega en dos gerentes, que a su vez usan `as_tool()` |
| `python descentralizada.py` | Descentralizada | Los agentes se transfieren la conversación con `handoff` |

Los diagramas están en [`docs/diagramas.md`](docs/diagramas.md) y las respuestas a las preguntas del
enunciado en [`docs/respuestas.pdf`](docs/respuestas.pdf) (fuente: [`docs/respuestas.md`](docs/respuestas.md)).

## Estructura

```
mcp_server.py           servidor MCP (Streamable HTTP) que expone consultar_faq, consultar_clima y agendar_cita
a2a_server.py           servidor A2A: envuelve la arquitectura jerárquica como un solo agente con skills
terminal.py             cliente de terminal que habla A2A con a2a_server.py
centralizada.py / jerarquica.py / descentralizada.py   programas de cada arquitectura (clientes MCP)
agentes_comunes.py      especialistas (FAQ, clima, citas), cliente del modelo, cliente MCP y bucle de terminal
herramientas/
  integraciones.py      FAQ, Open-Meteo y calendario; sin dependencia de las arquitecturas
  reglas_clima.py       criterio de seguridad para saltar (función pura)
base_datos.py, embeddings.py, faq_corpus.py, cargar_embeddings.py   RAG de HDT4
tests/                  pruebas sin red ni modelo
```

## Requisitos

- Python 3.12 (la versión usada para desarrollar).
- Una API key de [NVIDIA Build](https://build.nvidia.com) en `NVIDIA_API_KEY`.
- Para la búsqueda de FAQs: PostgreSQL con pgvector, levantado con Docker o Podman y cargado con `cargar_embeddings.py` (ver instrucciones de HDT4 abajo).
- Para cualquier arquitectura o el servidor A2A: el servidor MCP (`mcp_server.py`) corriendo (ver HDT7 abajo).

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install openai-agents
cp .env.example .env             # y pegar NVIDIA_API_KEY
```

## Base de datos de FAQs (HDT4)

```bash
docker compose up -d             # o: podman compose up -d
python cargar_embeddings.py      # carga las 120 fichas del corpus
```

En Windows, Docker Desktop requiere WSL2 (`wsl --install`, con reinicio). Ver el detalle en la sección de
infraestructura de HDT4 en el historial de este repositorio.

## Ejecutar

Primero levanta el servidor MCP (deja esa terminal abierta):

```bash
python mcp_server.py
```

Luego, en otra terminal, cualquiera de las tres arquitecturas (se conectan al MCP como clientes):

```bash
python centralizada.py
python jerarquica.py
python descentralizada.py
```

Escribe tu mensaje. Para salir, escribe `Bye` o presiona `Ctrl-C`.

Ejemplo de cita:

```
Tú: Quiero agendar una cita para mañana a las 09:00, servicio tándem, a nombre de Ana.
```

El agente consulta el clima de esa fecha. Si el día es prohibido, no agenda y explica los motivos. Si es
marginal, pregunta si el usuario acepta. Si es ideal, guarda la cita en `data/citas.json`.

## Criterio de clima

| Variable (Open-Meteo, `daily`) | Ideal | Marginal | Prohibido |
|---|---|---|---|
| `wind_speed_10m_max` (km/h) | < 20 | 20 – 28 | > 28 |
| `wind_gusts_10m_max` (km/h) | — | — | > 35 |
| `precipitation_sum` (mm) | — | — | > 0.0 |
| `cloud_cover_mean` (%) | < 30 | 30 – 75 | > 75 |

- Sólo se consulta un día entre hoy y 16 días. Una fecha fuera de ese rango se rechaza con una corrección.
- Coordenadas del lugar de aterrizaje: 14.013722, -90.771611.

## Pruebas

```bash
python -m pytest
```

Las pruebas cubren el parser del corpus y el criterio de clima (umbrales, rango de fechas y agendamiento),
con descargas simuladas. No requieren red ni API key.

## Notas

- Las tres arquitecturas usan los mismos especialistas y herramientas. Para un requerimiento nuevo se agrega
  una función a `herramientas/integraciones.py`, su envoltura como `@mcp.tool()` en `mcp_server.py` y se asigna a un especialista.
- El corpus contiene fichas con respuestas genéricas y respuestas repetidas en preguntas no relacionadas.
  El agente sólo responde con lo que aparece en el documento y, cuando no tiene el dato, lo dice.

## Evals (HDT6)

Evals con [promptfoo](https://www.promptfoo.dev/docs/getting-started/) para las tres arquitecturas. Cubren:

- **Determinísticos** (`contains`, `icontains`, `regex`, `not-icontains`).
- **Factuality**: respuestas comparadas con el texto literal del corpus (juez: el mismo modelo NIM).
- **Latencia**: umbral de 30 s por caso.
- **Tool execution**: herramientas invocadas (`tool-called.js`), su orden (`orden-herramientas.js`, el clima debe consultarse antes de agendar) y sus argumentos.

```bash
npm install                 # instala promptfoo 0.118.17 (requiere Node 22)
npm run eval                # ejecuta todos los casos con el agente real (requiere NVIDIA_API_KEY)
npm run view                # visor interactivo
```

Los reportes quedan en `evals/reports/report.html` y `evals/reports/results.json`.

Las fechas de los casos de cita (`2026-10-09`) deben caer dentro de los 16 días de pronóstico al ejecutar la eval.
Si el proveedor no encuentra Python de la venv, define `PROMPTFOO_PYTHON=.venv/Scripts/python.exe`.

`EVALS_MODO=simulado` valida el cableado del harness sin llamar al modelo ni a la red. Sus resultados no
evalúan al agente.

## MCP y A2A (HDT7)

Las herramientas (`consultar_faq`, `consultar_clima`, `agendar_cita`) ya no son `function_tool` locales:
viven en un servidor MCP y las tres arquitecturas se conectan a él como clientes, por transporte
Streamable HTTP. Además, el sistema multiagente se expone hacia afuera como un solo agente A2A.

```
mcp_server.py      servidor MCP: expone las herramientas (puerto 8765 por defecto)
a2a_server.py       servidor A2A: envuelve la arquitectura jerárquica y la publica como un agente
                     único con tres skills (faq, clima, citas) (puerto 9000 por defecto)
terminal.py          cliente de terminal que habla A2A con a2a_server.py (no ejecuta ningún agente
                     localmente, a diferencia de centralizada.py / jerarquica.py / descentralizada.py)
```

Variables de entorno (`.env.example`): `MCP_URL` (cliente MCP de las tres arquitecturas y de
`a2a_server.py`) y `A2A_URL` (cliente A2A de `terminal.py`); `MCP_HOST`/`MCP_PORT` y
`A2A_HOST`/`A2A_PORT` controlan dónde escuchan los servidores.

Para probar el flujo completo end-to-end, en tres terminales:

```bash
python mcp_server.py      # terminal 1: herramientas
python a2a_server.py      # terminal 2: agente único A2A (usa la arquitectura jerárquica)
python terminal.py        # terminal 3: cliente de conversación
```

El servidor A2A siempre corre la arquitectura jerárquica (supervisor general -> gerentes ->
especialistas) detrás de escena; las skills del Agent Card son metadatos de descubrimiento para el
cliente A2A, no un enrutador.
