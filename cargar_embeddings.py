"""Script de carga: lee el corpus de FAQs, genera embeddings y los guarda en pgvector.

Uso:
    python cargar_embeddings.py [ruta_al_corpus]

Es idempotente: si se vuelve a ejecutar, actualiza las filas existentes por ID.
"""

import json
import sys

from base_datos import conectar
from embeddings import DIMENSION, vectorizar
from faq_corpus import parsear_corpus

RUTA_CORPUS_POR_DEFECTO = "data/Corpus_FAQs_Parachute_SA_2026.txt"
TAMANO_LOTE = 32

SQL_UPSERT = """
INSERT INTO faq_chunks (id, categoria, pregunta, respuesta, metadata, embedding)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (id) DO UPDATE SET
    categoria = EXCLUDED.categoria,
    pregunta = EXCLUDED.pregunta,
    respuesta = EXCLUDED.respuesta,
    metadata = EXCLUDED.metadata,
    embedding = EXCLUDED.embedding
"""


def main() -> None:
    ruta = sys.argv[1] if len(sys.argv) > 1 else RUTA_CORPUS_POR_DEFECTO
    registros = parsear_corpus(ruta)
    print(f"Registros leídos: {len(registros)}")

    cargados = 0
    with conectar() as conexion:
        for inicio in range(0, len(registros), TAMANO_LOTE):
            lote = registros[inicio : inicio + TAMANO_LOTE]
            vectores = vectorizar([r.texto_para_embedding() for r in lote])
            filas = [
                (r.id, r.categoria, r.pregunta, r.respuesta, json.dumps(r.metadata, ensure_ascii=False), vector)
                for r, vector in zip(lote, vectores)
            ]
            with conexion.cursor() as cursor:
                cursor.executemany(SQL_UPSERT, filas)
            cargados += len(lote)
            print(f"  cargados {cargados}/{len(registros)}")

        total = conexion.execute("SELECT COUNT(*) FROM faq_chunks").fetchone()[0]

    print(f"Listo. Filas en faq_chunks: {total} (dimensión {DIMENSION}).")


if __name__ == "__main__":
    main()
