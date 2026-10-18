"""Servidor A2A que envuelve el sistema multiagente de Parachute S.A. como un solo
agente con tres skills (faq, clima, citas).

Detrás de escena siempre corre la arquitectura jerárquica (supervisor_general ->
gerentes -> especialistas): las skills del Agent Card son metadatos de descubrimiento
para el cliente A2A, no un enrutador — el propio supervisor decide a qué especialista
delegar cada mensaje, igual que si se usara `python jerarquica.py` localmente.

Uso:  python a2a_server.py
Variables de entorno: A2A_HOST (default 127.0.0.1), A2A_PORT (default 9000).
"""

import logging
import os

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from agents import Runner

import agentes_comunes
import jerarquica

logging.basicConfig(level=logging.INFO, format="%(asctime)s [a2a] %(message)s")
logger = logging.getLogger("a2a_parachute")


class ParachuteExecutor(AgentExecutor):
    """Ejecuta el supervisor jerárquico de Parachute S.A. por cada mensaje A2A,
    manteniendo el historial de conversación por contextId."""

    def __init__(self) -> None:
        self._historiales: dict[str, list] = {}

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        texto = context.get_user_input()
        context_id = context.context_id or "sin-contexto"
        logger.info("mensaje recibido (context=%s): %s", context_id, texto)

        historial = self._historiales.setdefault(context_id, [])
        historial.append({"role": "user", "content": texto})

        async with agentes_comunes.crear_mcp_server() as mcp_server:
            agente = jerarquica.construir_agente_principal(mcp_server)
            resultado = await Runner.run(agente, historial, run_config=agentes_comunes.RUN_CONFIG)

        historial[:] = resultado.to_input_list()
        logger.info("respuesta (context=%s): %s", context_id, resultado.final_output)
        await event_queue.enqueue_event(
            new_agent_text_message(
                resultado.final_output,
                context_id=context.context_id,
                task_id=context.task_id,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        logger.info("cancelación solicitada (context=%s); no soportada", context.context_id)


def construir_agent_card(url: str) -> AgentCard:
    return AgentCard(
        name="parachute_sa",
        description="Agente único de Parachute S.A.: responde FAQs del evento, consulta el "
        "pronóstico del salto y agenda citas. Internamente usa un sistema multiagente "
        "jerárquico, pero hacia afuera habla A2A como un solo agente.",
        url=url,
        version="1.0.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="faq",
                name="Preguntas frecuentes",
                description="Responde preguntas informativas sobre el evento de paracaidismo.",
                tags=["faq", "informacion"],
                examples=["¿A qué hora es el evento?", "¿Qué debo llevar al salto?"],
            ),
            AgentSkill(
                id="clima",
                name="Pronóstico de salto",
                description="Consulta el pronóstico de Open-Meteo y el nivel de seguridad del día "
                "(ideal, marginal o prohibido).",
                tags=["clima", "pronostico"],
                examples=["¿Cómo está el clima para el 2026-10-25?"],
            ),
            AgentSkill(
                id="citas",
                name="Agendar cita",
                description="Agenda una cita para saltar, revisando el clima antes de confirmar.",
                tags=["citas", "agenda"],
                examples=[
                    "Quiero agendar una cita para mañana a las 09:00, servicio tándem, a nombre de Ana."
                ],
            ),
        ],
    )


if __name__ == "__main__":
    agentes_comunes.configurar_modelo()
    host = os.getenv("A2A_HOST", "127.0.0.1")
    port = int(os.getenv("A2A_PORT", "9000"))
    url = os.getenv("A2A_URL", f"http://{host}:{port}/")

    agent_card = construir_agent_card(url)
    handler = DefaultRequestHandler(agent_executor=ParachuteExecutor(), task_store=InMemoryTaskStore())
    app = A2AStarletteApplication(agent_card=agent_card, http_handler=handler).build()

    logger.info("Servidor A2A de Parachute S.A. escuchando en %s (arquitectura jerárquica)", url)
    uvicorn.run(app, host=host, port=port)
