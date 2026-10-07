# Agente de citas y FAQs - Parachute S.A. (HDT5: sistemas multiagente)

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
centralizada.py / jerarquica.py / descentralizada.py   programas de cada arquitectura
agentes_comunes.py      especialistas (FAQ, clima, citas), cliente del modelo y bucle de terminal
herramientas/
  tools.py              herramientas del SDK (function_tool) que usan las tres arquitecturas
  integraciones.py      FAQ, Open-Meteo y calendario; sin dependencia de las arquitecturas
  reglas_clima.py       criterio de seguridad para saltar (función pura)
base_datos.py, embeddings.py, faq_corpus.py, cargar_embeddings.py   RAG de HDT4
tests/                  pruebas sin red ni modelo
```

## Requisitos

- Python 3.12 (la versión usada para desarrollar).
- Una API key de [NVIDIA Build](https://build.nvidia.com) en `NVIDIA_API_KEY`.
- Para la búsqueda de FAQs: PostgreSQL con pgvector, levantado con Docker o Podman y cargado con `cargar_embeddings.py` (ver instrucciones de HDT4 abajo).

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
  una función a `herramientas/integraciones.py`, su envoltura en `herramientas/tools.py` y se asigna a un especialista.
- El corpus contiene fichas con respuestas genéricas y respuestas repetidas en preguntas no relacionadas.
  El agente sólo responde con lo que aparece en el documento y, cuando no tiene el dato, lo dice.
