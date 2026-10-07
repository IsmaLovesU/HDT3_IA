"""Lectura del corpus de FAQs de Parachute S.A. en registros estructurados.

El corpus es un TXT con bloques separados por líneas de guiones. Cada bloque
tiene los campos ID, CATEGORÍA, PREGUNTA, RESPUESTA y METADATA, una línea por campo.
"""

from dataclasses import dataclass
import json
from pathlib import Path

SEPARADOR = "-" * 10
CAMPOS_REQUERIDOS = ("ID", "CATEGORÍA", "PREGUNTA", "RESPUESTA")


@dataclass(frozen=True)
class FaqRegistro:
    id: str
    categoria: str
    pregunta: str
    respuesta: str
    metadata: dict

    def texto_para_embedding(self) -> str:
        """Texto que se vectoriza: incluye la categoría para mejorar la recuperación."""
        return f"{self.categoria}. {self.pregunta} {self.respuesta}"


def _crear_registro(bloque: dict) -> FaqRegistro:
    faltantes = [campo for campo in CAMPOS_REQUERIDOS if campo not in bloque]
    if faltantes:
        raise ValueError(f"Bloque {bloque.get('ID', '?')} sin campos: {', '.join(faltantes)}")

    metadata = json.loads(bloque["METADATA"]) if "METADATA" in bloque else {}
    return FaqRegistro(
        id=bloque["ID"],
        categoria=bloque["CATEGORÍA"],
        pregunta=bloque["PREGUNTA"],
        respuesta=bloque["RESPUESTA"],
        metadata=metadata,
    )


def parsear_corpus(ruta: str | Path) -> list[FaqRegistro]:
    """Devuelve todos los registros del corpus en el orden del archivo."""
    registros: list[FaqRegistro] = []
    bloque: dict[str, str] = {}

    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        if linea.startswith(SEPARADOR):
            if bloque:
                registros.append(_crear_registro(bloque))
                bloque = {}
            continue

        clave, sep, valor = linea.partition(": ")
        if sep and clave in ("ID", "CATEGORÍA", "PREGUNTA", "RESPUESTA", "METADATA"):
            bloque[clave] = valor.strip()

    if bloque:
        registros.append(_crear_registro(bloque))

    return registros
