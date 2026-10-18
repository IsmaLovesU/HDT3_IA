"""Piezas compartidas por las tres arquitecturas de orquestación.

- Configura el cliente del modelo (NVIDIA Build, API compatible con OpenAI).
- Se conecta como cliente MCP al servidor de herramientas (ver mcp_server.py).
- Define los agentes especialistas (FAQ, clima, citas), que reciben las herramientas
  vía MCP en vez de function_tool local.
- Ofrece el bucle de terminal que conversa con cualquier agente principal.

Cada arquitectura sólo decide cómo conectar estos especialistas (as_tool o handoffs).
"""

import asyncio
import os
import sys
from typing import Callable

from agents import (
    Agent,
    RunConfig,
    Runner,
    Tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from agents.mcp import MCPServerStreamableHttp
from agents.models.multi_provider import MultiProvider
from dotenv import load_dotenv
from openai import AsyncOpenAI

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODELO = "openai/gpt-oss-20b"  # Soporta function calling en NVIDIA Build.

# Se completa en configurar_modelo(), una vez que existe el cliente de NVIDIA.
RUN_CONFIG: RunConfig | None = None


def configurar_modelo() -> None:
    global RUN_CONFIG

    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("No se encontró NVIDIA_API_KEY. Revisa tu archivo .env")
        sys.exit(1)
    cliente = AsyncOpenAI(base_url=BASE_URL, api_key=api_key)
    set_default_openai_client(cliente)
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)

    # El modelo de NVIDIA Build tiene un "/" en su nombre (p. ej. "openai/gpt-oss-20b"), así que
    # el MultiProvider por defecto lo interpreta como "prefijo/modelo" (como litellm): con prefijo
    # "openai" recorta el prefijo (modo "alias") y NVIDIA responde 404 porque el modelo real se
    # llama "openai/gpt-oss-20b", no "gpt-oss-20b"; con cualquier otro prefijo (p. ej. "meta")
    # directamente falla con "Unknown prefix". openai_prefix_mode="model_id" y
    # unknown_prefix_mode="model_id" mandan el nombre completo tal cual al cliente de NVIDIA.
    # Se construye con el cliente y la API explícitos (no el estado global) para no depender
    # del orden de llamadas.
    RUN_CONFIG = RunConfig(
        model_provider=MultiProvider(
            openai_client=cliente,
            openai_use_responses=False,
            openai_prefix_mode="model_id",
            unknown_prefix_mode="model_id",
        )
    )


def crear_mcp_server() -> MCPServerStreamableHttp:
    """Cliente MCP (Streamable HTTP) hacia el servidor de herramientas (mcp_server.py)."""
    url = os.getenv("MCP_URL", "http://127.0.0.1:8765/mcp")
    return MCPServerStreamableHttp(
        params={"url": url},
        name="parachute-herramientas",
        cache_tools_list=True,
    )


def crear_agente(
    nombre: str,
    instrucciones: str,
    tools: list[Tool] | None = None,
    mcp_server: MCPServerStreamableHttp | None = None,
) -> Agent:
    return Agent(
        name=nombre,
        instructions=instrucciones,
        model=MODELO,
        tools=tools or [],
        mcp_servers=[mcp_server] if mcp_server else [],
    )


def agente_faq(mcp_server: MCPServerStreamableHttp) -> Agent:
    return crear_agente(
        "agente_faq",
        "Respondes preguntas informativas sobre el evento de Parachute S.A. usando consultar_faq. "
        "Responde solo con lo que devuelva la búsqueda. Si no está, dilo y sugiere soporte@parachutesa.gt. "
        "Responde en español.",
        mcp_server=mcp_server,
    )


def agente_clima(mcp_server: MCPServerStreamableHttp) -> Agent:
    return crear_agente(
        "agente_clima",
        "Consultas el pronóstico con consultar_clima y explicas el nivel del día (ideal, marginal o prohibido) "
        "con sus motivos. Sólo hay pronóstico hasta 16 días; si la fecha está fuera de rango, corrígelo. "
        "Responde en español.",
        mcp_server=mcp_server,
    )


def agente_citas(mcp_server: MCPServerStreamableHttp) -> Agent:
    return crear_agente(
        "agente_citas",
        "Agendas citas para saltar. Antes de agendar, consulta el clima de la fecha con consultar_clima. "
        "Nunca agendes un día prohibido. Un día marginal sólo se agenda si el usuario lo confirma "
        "explícitamente (confirmar_marginal=true). Pide nombre, fecha (AAAA-MM-DD), hora (HH:MM) y servicio "
        "si faltan. Responde en español.",
        mcp_server=mcp_server,
    )


def ejecutar_terminal(construir_agente_principal: Callable[[MCPServerStreamableHttp], Agent], titulo: str) -> None:
    """Conversación multi-turno en terminal, contra el servidor MCP local. Sale con 'Bye' o Ctrl-C.

    `construir_agente_principal` recibe el cliente MCP ya conectado y devuelve el agente principal
    de la arquitectura (centralizada, jerárquica o descentralizada).
    """
    configurar_modelo()
    try:
        asyncio.run(_sesion_terminal(construir_agente_principal, titulo))
    except Exception as error:
        print(f"No se pudo conectar al servidor MCP ({error}). ¿Está corriendo 'python mcp_server.py'?")


async def _sesion_terminal(
    construir_agente_principal: Callable[[MCPServerStreamableHttp], Agent], titulo: str
) -> None:
    print(f"Agente de Parachute S.A. - Arquitectura {titulo}")
    print("Escribe tu mensaje. Escribe 'Bye' o presiona Ctrl-C para salir.\n")

    async with crear_mcp_server() as mcp_server:
        agente_principal = construir_agente_principal(mcp_server)
        historial: list = []
        try:
            while True:
                pregunta = input("Tú: ").strip()
                if pregunta.lower() == "bye":
                    print("Agente: ¡Gracias por tu visita! Hasta pronto.")
                    break
                if not pregunta:
                    continue

                historial.append({"role": "user", "content": pregunta})
                try:
                    resultado = await Runner.run(agente_principal, historial, run_config=RUN_CONFIG)
                    historial = resultado.to_input_list()
                    print(f"Agente: {resultado.final_output}\n")
                except Exception as error:
                    historial.pop()
                    print(f"Agente: Hubo un problema al procesar tu mensaje ({error}). Intenta de nuevo.\n")
        except KeyboardInterrupt:
            print("\nAgente: ¡Hasta pronto!")
