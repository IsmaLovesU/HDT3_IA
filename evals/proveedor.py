"""Proveedor de promptfoo que ejecuta el agente real de una arquitectura.

config.arquitectura: "centralizada", "jerarquica" o "descentralizada".

Variables de entorno:
    NVIDIA_API_KEY    obligatoria en modo real (llamadas al modelo).
    EVALS_MODO=simulado  NO llama al modelo ni a la red. Sólo valida el cableado del harness;
                         sus resultados no evalúan al agente.
"""

import asyncio
import importlib
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

ARQUITECTURAS = {"centralizada", "jerarquica", "descentralizada"}


def call_api(prompt: str, options: dict, context: dict) -> dict:
    config = (options or {}).get("config", {}) or {}
    arquitectura = config.get("arquitectura", "centralizada")
    if arquitectura not in ARQUITECTURAS:
        return {"error": f"Arquitectura desconocida: {arquitectura}"}

    if os.getenv("EVALS_MODO") == "simulado":
        return _respuesta_simulada(prompt, arquitectura)
    return _respuesta_real(prompt, arquitectura)


def _respuesta_real(mensaje: str, arquitectura: str) -> dict:
    from agents import Runner

    from agentes_comunes import configurar_modelo
    from herramientas.tools import REGISTRO_LLAMADAS

    try:
        configurar_modelo()  # Termina con SystemExit si falta NVIDIA_API_KEY.
    except SystemExit:
        return {"error": "Falta NVIDIA_API_KEY en el entorno o en .env."}
    modulo = importlib.import_module(arquitectura)
    agente = modulo.construir_agente_principal()

    REGISTRO_LLAMADAS.clear()
    resultado = asyncio.run(Runner.run(agente, mensaje))
    return {
        "output": resultado.final_output,
        "metadata": {
            "arquitectura": arquitectura,
            "toolCalls": list(REGISTRO_LLAMADAS),
        },
    }


def _respuesta_simulada(mensaje: str, arquitectura: str) -> dict:
    """Respuesta fija para validar el harness. No representa el comportamiento del agente."""
    llamadas = []
    fecha = re.search(r"\d{4}-\d{2}-\d{2}", mensaje)
    hora = re.search(r"\b(\d{1,2}:\d{2})\b", mensaje)

    if re.search(r"cita", mensaje, re.IGNORECASE):
        if fecha:
            llamadas.append({"name": "consultar_clima", "arguments": {"fecha": fecha.group(0)}})
            llamadas.append(
                {
                    "name": "agendar_cita",
                    "arguments": {"fecha": fecha.group(0), "hora": hora.group(1) if hora else None},
                }
            )
            texto = "[SIMULADO] Cita registrada."
        else:
            texto = "[SIMULADO] ¿Para qué fecha y hora deseas la cita?"
    else:
        llamadas.append({"name": "consultar_faq", "arguments": {"consulta": mensaje}})
        texto = "[SIMULADO] Respuesta de FAQ no generada por el modelo."

    return {
        "output": texto,
        "metadata": {"arquitectura": arquitectura, "toolCalls": llamadas, "modo": "simulado"},
    }
