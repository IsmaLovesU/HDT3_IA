"""Servidor MCP que expone las herramientas del agente de Parachute S.A.

Las tres arquitecturas (y el servidor A2A) ya no usan `function_tool` local: se
conectan a este servidor como clientes MCP (transporte Streamable HTTP), así que
las herramientas quedan en un solo lugar sin depender del framework de agentes.

Uso:  python mcp_server.py
Variables de entorno: MCP_HOST (default 127.0.0.1), MCP_PORT (default 8765).
"""

import json
import logging
import os

from mcp.server.mcpserver import MCPServer

from herramientas import integraciones

logging.basicConfig(level=logging.INFO, format="%(asctime)s [mcp] %(message)s")
logger = logging.getLogger("mcp_parachute")

mcp = MCPServer("parachute-herramientas")

# Llamadas reales a herramientas, en orden. Lo usan las evals de HDT6 (ver
# obtener_registro_llamadas) para verificar qué herramientas se invocaron y con qué argumentos.
REGISTRO_LLAMADAS: list[dict] = []


def _resultado(funcion, **kwargs) -> str:
    try:
        return json.dumps(funcion(**kwargs), ensure_ascii=False)
    except ValueError as error:
        return json.dumps({"error": str(error)}, ensure_ascii=False)


def _registrar(nombre: str, **argumentos) -> None:
    REGISTRO_LLAMADAS.append({"name": nombre, "arguments": argumentos})
    logger.info("herramienta=%s argumentos=%s", nombre, argumentos)


@mcp.tool()
def consultar_faq(consulta: str) -> str:
    """Busca en la base de FAQs del evento. Úsala para cualquier pregunta informativa."""
    _registrar("consultar_faq", consulta=consulta)
    return _resultado(integraciones.consultar_faq, consulta=consulta)


@mcp.tool()
def consultar_clima(fecha: str) -> str:
    """Consulta el pronóstico de Open-Meteo para el lugar de aterrizaje en una fecha (AAAA-MM-DD).
    Devuelve el nivel del día (ideal, marginal o prohibido) y los motivos. Sólo hay pronóstico hasta 16 días."""
    _registrar("consultar_clima", fecha=fecha)
    return _resultado(integraciones.consultar_clima, fecha_iso=fecha)


@mcp.tool()
def agendar_cita(
    nombre: str,
    fecha: str,
    hora: str,
    servicio: str,
    confirmar_marginal: bool = False,
) -> str:
    """Agenda una cita para saltar. Revisa el clima antes: un día prohibido nunca se agenda.
    Un día marginal sólo se agenda si confirmar_marginal es true (el usuario lo aceptó).
    fecha es AAAA-MM-DD y hora es HH:MM en 24 horas."""
    _registrar(
        "agendar_cita",
        nombre=nombre,
        fecha=fecha,
        hora=hora,
        servicio=servicio,
        confirmar_marginal=confirmar_marginal,
    )
    return _resultado(
        integraciones.agendar_cita,
        nombre=nombre,
        fecha_iso=fecha,
        hora=hora,
        servicio=servicio,
        confirmar_marginal=confirmar_marginal,
    )


@mcp.tool()
def obtener_registro_llamadas() -> str:
    """Uso interno de las evals (HDT6): devuelve las llamadas a herramientas registradas desde
    el último limpiar_registro_llamadas. No la uses para responder al usuario."""
    return json.dumps(REGISTRO_LLAMADAS, ensure_ascii=False)


@mcp.tool()
def limpiar_registro_llamadas() -> str:
    """Uso interno de las evals (HDT6): vacía el registro de llamadas a herramientas.
    No la uses para responder al usuario."""
    REGISTRO_LLAMADAS.clear()
    return json.dumps({"ok": True}, ensure_ascii=False)


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8765"))
    logger.info("Servidor MCP de Parachute S.A. escuchando en http://%s:%s/mcp", host, port)
    mcp.run(transport="streamable-http", host=host, port=port)
