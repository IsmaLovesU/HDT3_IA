"""Cliente de terminal A2A para el agente de Parachute S.A.

A diferencia de centralizada.py / jerarquica.py / descentralizada.py (que corren el
agente localmente contra el servidor MCP, útil para pruebas rápidas), este cliente
no ejecuta ningún agente: habla el protocolo A2A con un servidor A2A ya corriendo
(ver a2a_server.py), que envuelve la arquitectura jerárquica como un solo agente.

Uso:
    python mcp_server.py     (en otra terminal)
    python a2a_server.py     (en otra terminal)
    python terminal.py

Variable de entorno: A2A_URL (default http://127.0.0.1:9000)
"""

import asyncio
import os
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    JSONRPCErrorResponse,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendMessageRequest,
    Task,
    TextPart,
)
from a2a.utils import get_message_text, get_text_parts


def _mensaje_usuario(texto: str, context_id: str | None) -> Message:
    return Message(
        role=Role.user,
        parts=[Part(root=TextPart(text=texto))],
        message_id=str(uuid4()),
        context_id=context_id,
    )


def _texto_de_respuesta(resultado: Message | Task) -> str:
    if isinstance(resultado, Message):
        return get_message_text(resultado) or "(el agente no devolvió texto)"
    if resultado.status.message:
        return get_message_text(resultado.status.message) or "(el agente no devolvió texto)"
    for artefacto in resultado.artifacts or []:
        textos = get_text_parts(artefacto.parts)
        if textos:
            return "\n".join(textos)
    return "(el agente no devolvió texto)"


async def _conversar() -> None:
    url = os.getenv("A2A_URL", "http://127.0.0.1:9000")
    # La arquitectura jerárquica puede encadenar varias llamadas al modelo (supervisor ->
    # gerente -> especialista) por cada turno; 60 s se queda corto y da falsos timeouts.
    async with httpx.AsyncClient(timeout=180) as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=url)
        try:
            agent_card = await resolver.get_agent_card()
        except Exception as error:
            print(
                f"No se pudo conectar al servidor A2A en {url} ({error}). "
                "¿Está corriendo 'python a2a_server.py'?"
            )
            return

        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)
        print(f"Cliente A2A de Parachute S.A. conectado a: {agent_card.name}")
        print(f"Skills del agente: {', '.join(skill.id for skill in agent_card.skills)}")
        print("Escribe tu mensaje. Escribe 'Bye' o presiona Ctrl-C para salir.\n")

        context_id: str | None = None
        try:
            while True:
                pregunta = input("Tú: ").strip()
                if pregunta.lower() == "bye":
                    print("Agente: ¡Gracias por tu visita! Hasta pronto.")
                    break
                if not pregunta:
                    continue

                mensaje = _mensaje_usuario(pregunta, context_id)
                request = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(message=mensaje))
                try:
                    respuesta = await client.send_message(request)
                except Exception as error:
                    print(f"Agente: Hubo un problema al contactar al servidor A2A ({error}). Intenta de nuevo.\n")
                    continue

                raiz = respuesta.root
                if isinstance(raiz, JSONRPCErrorResponse):
                    print(f"Agente: Error del servidor A2A: {raiz.error.message}\n")
                    continue

                resultado = raiz.result
                context_id = getattr(resultado, "context_id", None) or context_id
                print(f"Agente: {_texto_de_respuesta(resultado)}\n")
        except KeyboardInterrupt:
            print("\nAgente: ¡Hasta pronto!")


if __name__ == "__main__":
    asyncio.run(_conversar())
