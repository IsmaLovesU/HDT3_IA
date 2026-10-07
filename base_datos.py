"""Conexión a PostgreSQL con pgvector y búsqueda semántica de FAQs."""

import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from embeddings import vectorizar

DATABASE_URL_POR_DEFECTO = "postgresql://faq:faq@localhost:5432/faq"


def conectar() -> psycopg.Connection:
    """Abre una conexión con el vector registrado. Lee DATABASE_URL desde .env."""
    load_dotenv()
    url = os.getenv("DATABASE_URL", DATABASE_URL_POR_DEFECTO)
    conexion = psycopg.connect(url, autocommit=True)
    register_vector(conexion)
    return conexion


def buscar_faq(consulta: str, k: int = 5) -> list[dict]:
    """Devuelve las k FAQs más parecidas a la consulta, ordenadas por similitud."""
    vector = vectorizar([consulta])[0]
    with conectar() as conexion:
        filas = conexion.execute(
            """
            SELECT id, categoria, pregunta, respuesta,
                   1 - (embedding <=> %s) AS similitud
            FROM faq_chunks
            ORDER BY embedding <=> %s
            LIMIT %s
            """,
            (vector, vector, k),
        ).fetchall()

    return [
        {
            "id": fila[0],
            "categoria": fila[1],
            "pregunta": fila[2],
            "respuesta": fila[3],
            "similitud": round(float(fila[4]), 3),
        }
        for fila in filas
    ]
