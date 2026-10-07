"""Arquitectura JERÁRQUICA.

Un supervisor general delega en dos gerentes; cada gerente controla sus especialistas.
Los gerentes se exponen con as_tool().

    Usuario -> Supervisor general
                 |-- as_tool --> Gerente de información -- as_tool --> Agente FAQ
                 |-- as_tool --> Gerente de operaciones -- as_tool --> Agente de clima
                                                         -- as_tool --> Agente de citas

Uso:  python jerarquica.py
"""

from agentes_comunes import agente_citas, agente_clima, agente_faq, crear_agente, ejecutar_terminal


def _gerente_informacion():
    return crear_agente(
        "gerente_informacion",
        "Atiendes consultas informativas del evento. Delegas en el Agente FAQ y devuelves su respuesta "
        "sin inventar datos. Responde en español.",
        [
            agente_faq().as_tool(
                tool_name="buscar_en_faq",
                tool_description="Busca la respuesta en las preguntas frecuentes del evento.",
            )
        ],
    )


def _gerente_operaciones():
    return crear_agente(
        "gerente_operaciones",
        "Atiendes solicitudes de clima y citas. Para agendar, primero consulta el pronóstico con el "
        "Agente de clima y después pide al Agente de citas que agende. Nunca agendes un día prohibido. "
        "Responde en español.",
        [
            agente_clima().as_tool(
                tool_name="consultar_pronostico",
                tool_description="Devuelve el pronóstico y el nivel de salto de una fecha (AAAA-MM-DD).",
            ),
            agente_citas().as_tool(
                tool_name="gestionar_cita",
                tool_description="Agenda una cita para saltar, revisando el clima.",
            ),
        ],
    )


def construir_agente_principal():
    return crear_agente(
        "supervisor_general",
        "Eres el supervisor general de Parachute S.A. Clasifica cada mensaje: si es informativo, usa "
        "el gerente de información; si es sobre clima o citas, usa el gerente de operaciones. "
        "Responde en español, breve y amable.",
        [
            _gerente_informacion().as_tool(
                tool_name="gerente_informacion",
                tool_description="Resuelve preguntas informativas sobre el evento.",
            ),
            _gerente_operaciones().as_tool(
                tool_name="gerente_operaciones",
                tool_description="Resuelve consultas de clima y citas para saltar.",
            ),
        ],
    )


if __name__ == "__main__":
    ejecutar_terminal(construir_agente_principal(), "jerárquica")
