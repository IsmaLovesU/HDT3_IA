-- Se ejecuta una sola vez al crear el contenedor por primera vez.
CREATE EXTENSION IF NOT EXISTS vector;

-- 384 dimensiones = salida de sentence-transformers/all-MiniLM-L6-v2.
CREATE TABLE IF NOT EXISTS faq_chunks (
    id         TEXT PRIMARY KEY,
    categoria  TEXT  NOT NULL,
    pregunta   TEXT  NOT NULL,
    respuesta  TEXT  NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding  vector(384) NOT NULL
);

-- Índice HNSW para búsqueda por similitud coseno.
CREATE INDEX IF NOT EXISTS faq_chunks_embedding_idx
    ON faq_chunks USING hnsw (embedding vector_cosine_ops);
