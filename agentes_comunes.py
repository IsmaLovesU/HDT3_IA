"""Piezas compartidas por las tres arquitecturas de orquestación.

- Configura el cliente del modelo (NVIDIA Build, API compatible con OpenAI).
- Define los agentes especialistas (FAQ, clima, citas) con sus herramientas.
- Ofrece el bucle de terminal que conversa con cualquier agente principal.

Cada arquitectura sólo decide cómo conectar estos especialistas (as_tool o handoffs).
"""

import asyncio
import os
import sys

from agents import (
    Agent,
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from dotenv import load_dotenv
from openai import AsyncOpenAI

from herramientas.tools import agendar_cita, consultar_clima, consultar_faq

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODELO = "meta/llama-3.1-70b-instruct"  # Soporta function calling en NVIDIA Build.


def configurar_modelo() -> None:
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("No se encontró NVIDIA_API_KEY. Revisa tu archivo .env")
        sys.exit(1)
    set_default_openai_client(AsyncOpenAI(base_url=BASE_URL, api_key=api_key))
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)


def crear_agente(nombre: str, instrucciones: str, herramientas: list) -> Agent:
    return Agent(name=nombre, instructions=instrucciones, model=MODELO, tools=herramientas)


def agente_faq() -> Agent:
    return crear_agente(
        "agente_faq",
        "Respondes preguntas informativas sobre el evento de Parachute S.A. usando consultar_faq. "
        "Responde solo con lo que devuelva la búsqueda. Si no está, dilo y sugiere soporte@parachutesa.gt. "
        "Responde en español.",
        [consultar_faq],
    )


def agente_clima() -> Agent:
    return crear_agente(
        "agente_clima",
        "Consultas el pronóstico con consultar_clima y explicas el nivel del día (ideal, marginal o prohibido) "
        "con sus motivos. Sólo hay pronóstico hasta 16 días; si la fecha está fuera de rango, corrígelo. "
        "Responde en español.",
        [consultar_clima],
    )


def agente_citas() -> Agent:
    return crear_agente(
        "agente_citas",
        "Agendas citas para saltar. Antes de agendar, consulta el clima de la fecha con consultar_clima. "
        "Nunca agendes un día prohibido. Un día marginal sólo se agenda si el usuario lo confirma "
        "explícitamente (confirmar_marginal=true). Pide nombre, fecha (AAAA-MM-DD), hora (HH:MM) y servicio "
        "si faltan. Responde en español.",
        [consultar_clima, agendar_cita],
    )


def ejecutar_terminal(agente_principal: Agent, titulo: str) -> None:
    """Conversación multi-turno en terminal. Sale con 'Bye' o Ctrl-C."""
    configurar_modelo()
    print(f"Agente de Parachute S.A. - Arquitectura {titulo}")
    print("Escribe tu mensaje. Escribe 'Bye' o presiona Ctrl-C para salir.\n")

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
                resultado = asyncio.run(Runner.run(agente_principal, historial))
                historial = resultado.to_input_list()
                print(f"Agente: {resultado.final_output}\n")
            except Exception as error:
                historial.pop()
                print(f"Agente: Hubo un problema al procesar tu mensaje ({error}). Intenta de nuevo.\n")
    except KeyboardInterrupt:
        print("\nAgente: ¡Hasta pronto!")
