"""Proveedor de promptfoo que ejecuta el agente real de una arquitectura.

config.arquitectura: "centralizada", "jerarquica" o "descentralizada".

Variables de entorno:
    NVIDIA_API_KEY    obligatoria en modo real (llamadas al modelo).
    EVALS_MODO=simulado  NO llama al modelo ni a la red. Sólo valida el cableado del harness;
                         sus resultados no evalúan al agente.
"""

import asyncio
import importlib
import json
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
    from agentes_comunes import configurar_modelo

    try:
        configurar_modelo()  # Termina con SystemExit si falta NVIDIA_API_KEY.
    except SystemExit:
        return {"error": "Falta NVIDIA_API_KEY en el entorno o en .env."}
    try:
        return asyncio.run(_ejecutar_real(mensaje, arquitectura))
    except Exception as error:
        return {"error": f"No se pudo conectar al servidor MCP ({error}). ¿Está corriendo 'python mcp_server.py'?"}


async def _ejecutar_real(mensaje: str, arquitectura: str) -> dict:
    from agents import Runner

    from agentes_comunes import RUN_CONFIG, crear_mcp_server

    modulo = importlib.import_module(arquitectura)

    async with crear_mcp_server() as mcp_server:
        # El registro de llamadas vive en el servidor MCP (proceso separado); se limpia antes
        # de cada caso y se lee después, para que las evals sigan viendo qué herramientas se usaron.
        await mcp_server.call_tool("limpiar_registro_llamadas", {})
        agente = modulo.construir_agente_principal(mcp_server)
        resultado = await Runner.run(agente, mensaje, run_config=RUN_CONFIG)
        registro = await mcp_server.call_tool("obtener_registro_llamadas", {})
        tool_calls = json.loads(registro.content[0].text)

    return {
        "output": resultado.final_output,
        "metadata": {
            "arquitectura": arquitectura,
            "toolCalls": tool_calls,
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
