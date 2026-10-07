# Agente de FAQs - Parachute S.A. (HDT4: RAG con pgvector)

Agente de línea de comandos que responde preguntas sobre el evento de
paracaidismo de Parachute S.A. (Guatemala, 29 de septiembre de 2026).

Esta versión reemplaza la inyección completa del FAQ por **RAG**: las 120 fichas
del corpus se vectorizan, se guardan en PostgreSQL con pgvector y el agente
consulta esa base mediante la herramienta `buscar_faq`.

## Arquitectura

```
data/Corpus_FAQs_...txt --> cargar_embeddings.py --> PostgreSQL + pgvector (faq_chunks)
                                                          ^
Usuario --> agente_faq.py --(function call buscar_faq)----+
              ^                                           |
              +------ resultados (top 5 fichas) ----------+
```

| Archivo | Responsabilidad |
|---|---|
| `faq_corpus.py` | Parsea el TXT del corpus en registros (ID, categoría, pregunta, respuesta, metadata). |
| `embeddings.py` | Genera vectores de 384 dimensiones con `sentence-transformers/all-MiniLM-L6-v2`. |
| `base_datos.py` | Conexión a PostgreSQL y búsqueda por similitud coseno. |
| `cargar_embeddings.py` | **Script 1 (carga):** llena la tabla `faq_chunks`. Es idempotente. |
| `agente_faq.py` | **Script 2 (agente):** chat en terminal con la herramienta `buscar_faq`. |
| `infra/init.sql` | Crea la extensión `vector`, la tabla y el índice HNSW. |
| `docker-compose.yml` | Levanta PostgreSQL 16 + pgvector. |

## 1. Infraestructura (base de datos)

Requisitos: Docker Desktop o Podman. En Windows, Docker Desktop necesita WSL2
(`wsl --install`, con reinicio).

```bash
# Docker
docker compose up -d

# Podman
podman compose up -d
```

El contenedor expone PostgreSQL en `localhost:5432` (usuario `faq`, contraseña `faq`,
base `faq`). El script `infra/init.sql` se ejecuta solo la primera vez que se crea el
volumen. Para reiniciar la base desde cero:

```bash
docker compose down -v && docker compose up -d
```

Verificar que pgvector está disponible:

```bash
docker exec -it faq-pgvector psql -U faq -d faq -c "\dx"
```

## 2. Entorno de Python

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # y pegar NVIDIA_API_KEY
```

La primera ejecución descarga el modelo de embeddings (~90 MB).

## 3. Cargar el corpus

```bash
python cargar_embeddings.py
```

Salida esperada: `Registros leídos: 120` y `Filas en faq_chunks: 120`.

## 4. Ejecutar el agente

```bash
python agente_faq.py
```

Escribe tu pregunta. Para salir, escribe `Bye` o presiona `Ctrl-C`.

```
Tú: ¿Cuál es el límite de peso para el salto?
Agente: El límite de peso máximo es de 100 kg. Si el peso está entre 90 kg y 100 kg, ...
```

El modelo de chat se configura en `MODELO` dentro de `agente_faq.py`
(por defecto `meta/llama-3.1-70b-instruct` en NVIDIA Build, que soporta function calling).

## Pruebas

```bash
pytest
```

Las pruebas cubren el parser del corpus; no requieren base de datos ni API key.

## Notas sobre el corpus

Parte del corpus contiene fichas con respuestas genéricas (plantilla) y respuestas
repetidas en preguntas que no corresponden. El agente solo puede responder con lo que
aparece en el documento, así que en esos casos indicará que no tiene el detalle y
sugerirá contactar a soporte@parachutesa.gt.

## Seguridad

`.env` está en `.gitignore`. Usa `.env.example` como plantilla.
