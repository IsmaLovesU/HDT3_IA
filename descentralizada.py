"""Arquitectura DESCENTRALIZADA.

No hay supervisor que controle el flujo: cada agente decide a quién transferir la
conversación con handoffs. Al final de cada atención se devuelve al agente de entrada.

    Usuario -> Agente de entrada --handoff--> Agente FAQ
                                  --handoff--> Agente de clima
                                  --handoff--> Agente de citas --handoff--> Agente de clima

Uso:  python descentralizada.py
"""

from agents import handoff

from agentes_comunes import agente_citas, agente_clima, agente_faq, crear_agente, ejecutar_terminal


def construir_agente_principal():
    entrada = crear_agente(
        "agente_entrada",
        "Eres el primer contacto de Parachute S.A. Identifica la intención del usuario y transfiere la "
        "conversación al agente adecuado mediante handoff: preguntas informativas al Agente FAQ, "
        "clima al Agente de clima, citas al Agente de citas. Responde en español.",
        [],
    )
    faq = agente_faq()
    clima = agente_clima()
    citas = agente_citas()

    # Cada especialista puede devolver la conversación a la entrada o transferir a otro.
    for agente in (faq, clima, citas):
        agente.handoffs = [handoff(entrada)]
    citas.handoffs = [handoff(clima), handoff(entrada)]
    clima.handoffs = [handoff(citas), handoff(entrada)]

    entrada.handoffs = [handoff(faq), handoff(clima), handoff(citas)]
    return entrada


if __name__ == "__main__":
    ejecutar_terminal(construir_agente_principal(), "descentralizada")
