"""Agente de FAQs para el evento de paracaidismo de Parachute S.A.

Usa RAG con una herramienta: el modelo llama a `buscar_faq` para consultar pgvector
y responde únicamente con lo que devuelve esa búsqueda.

Uso:
    python agente_faq.py
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from base_datos import buscar_faq

BASE_URL = "https://integrate.api.nvidia.com/v1"
MODELO = "meta/llama-3.1-70b-instruct"  # Modelo con soporte de function calling en NVIDIA Build.
MAX_VUELTAS_HERRAMIENTA = 3

INSTRUCCIONES = """Eres un asistente de atención al cliente de Parachute S.A.
Respondes preguntas sobre el evento de paracaidismo del 29 de septiembre de 2026 en Guatemala.

Reglas:
- Para responder, SIEMPRE usa la herramienta buscar_faq con la pregunta del usuario.
- Responde únicamente con información que aparezca en los resultados de buscar_faq.
- Si los resultados no contienen la respuesta, di claramente que no tienes esa información
  y sugiere contactar a soporte@parachutesa.gt.
- Si los resultados contienen condiciones que parecen contradecirse, menciónalas todas.
- No inventes datos ni uses conocimiento externo.
- Responde en español, de forma breve y amable."""

DEFINICION_HERRAMIENTA = {
    "type": "function",
    "function": {
        "name": "buscar_faq",
        "description": "Busca en la base de conocimiento de FAQs del evento las entradas más relevantes para una pregunta.",
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "La pregunta del usuario, reformulada si conviene para la búsqueda.",
                }
            },
            "required": ["consulta"],
        },
    },
}


def crear_cliente() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("No se encontró NVIDIA_API_KEY. Revisa tu archivo .env")
        sys.exit(1)
    return OpenAI(base_url=BASE_URL, api_key=api_key)


def ejecutar_herramienta(nombre: str, argumentos: str) -> str:
    if nombre != "buscar_faq":
        return json.dumps({"error": f"Herramienta desconocida: {nombre}"})
    consulta = json.loads(argumentos).get("consulta", "")
    return json.dumps(buscar_faq(consulta), ensure_ascii=False)


def responder(cliente: OpenAI, pregunta: str) -> str:
    """Ejecuta el ciclo: el modelo pide la herramienta, se ejecuta y el modelo responde."""
    mensajes = [
        {"role": "system", "content": INSTRUCCIONES},
        {"role": "user", "content": pregunta},
    ]

    for _ in range(MAX_VUELTAS_HERRAMIENTA):
        respuesta = cliente.chat.completions.create(
            model=MODELO,
            messages=mensajes,
            tools=[DEFINICION_HERRAMIENTA],
        )
        mensaje = respuesta.choices[0].message

        if not mensaje.tool_calls:
            return mensaje.content or "No pude generar una respuesta."

        mensajes.append(mensaje.model_dump(exclude_none=True))
        for llamada in mensaje.tool_calls:
            resultado = ejecutar_herramienta(llamada.function.name, llamada.function.arguments)
            mensajes.append(
                {"role": "tool", "tool_call_id": llamada.id, "content": resultado}
            )

    return "No pude completar la búsqueda. Intenta reformular tu pregunta."


def main() -> None:
    cliente = crear_cliente()

    print("Agente de FAQs - Evento de Paracaidismo Parachute S.A.")
    print("Escribe tu pregunta. Escribe 'Bye' o presiona Ctrl-C para salir.\n")

    try:
        while True:
            pregunta = input("Tú: ").strip()

            if pregunta.lower() == "bye":
                print("Agente: ¡Gracias por tu visita! Hasta pronto.")
                break

            if not pregunta:
                continue

            try:
                print(f"Agente: {responder(cliente, pregunta)}\n")
            except Exception as error:
                print(f"Agente: Hubo un problema al procesar tu pregunta ({error}). Intenta de nuevo.\n")
    except KeyboardInterrupt:
        print("\nAgente: ¡Hasta pronto!")


if __name__ == "__main__":
    main()
