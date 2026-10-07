"""Arquitectura CENTRALIZADA.

Un único supervisor decide qué especialista llamar. Los especialistas se exponen
como herramientas con as_tool(); el supervisor no delega en otros supervisores.

    Usuario -> Supervisor --as_tool--> Agente FAQ
                           --as_tool--> Agente de clima
                           --as_tool--> Agente de citas

Uso:  python centralizada.py
"""

from agentes_comunes import agente_citas, agente_clima, agente_faq, crear_agente, ejecutar_terminal


def construir_agente_principal():
    especialistas = [
        agente_faq().as_tool(
            tool_name="consultar_informacion",
            tool_description="Responde preguntas informativas sobre el evento (FAQ).",
        ),
        agente_clima().as_tool(
            tool_name="consultar_pronostico",
            tool_description="Devuelve el pronóstico y el nivel de salto de una fecha (AAAA-MM-DD).",
        ),
        agente_citas().as_tool(
            tool_name="gestionar_cita",
            tool_description="Agenda una cita para saltar; revisa el clima antes de agendar.",
        ),
    ]
    return crear_agente(
        "supervisor_centralizado",
        "Eres el supervisor de atención de Parachute S.A. Recibes al usuario y decides qué especialista "
        "usar: consultar_informacion para preguntas, consultar_pronostico para el clima, gestionar_cita "
        "para agendar. Nunca inventes datos: usa siempre a un especialista. Responde en español, breve y amable.",
        especialistas,
    )


if __name__ == "__main__":
    ejecutar_terminal(construir_agente_principal(), "centralizada")
