"""
Agente de FAQs para el evento de paracaidismo de Parachute S.A.
RAG simple: se lee faq.txt completo y se inyecta en el system prompt.
No usa embeddings, vector DB, ni memoria conversacional.
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

# Constantes: tocar aquí para cambiar modelo, proveedor o archivo de FAQ.
ARCHIVO_FAQ = "faq.txt"
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODELO = "meta/llama-3.2-11b-vision-instruct"


def cargar_faq(ruta: str) -> str:
    """Lee el archivo de FAQ completo. Si no existe, termina el programa."""
    if not os.path.exists(ruta):
        print(f"No se encontró el archivo '{ruta}'. No se puede iniciar el agente.")
        sys.exit(1)
    with open(ruta, "r", encoding="utf-8") as f:
        return f.read()


def crear_cliente() -> OpenAI:
    """Carga la API key desde .env y crea el cliente apuntando a NVIDIA Build."""
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("No se encontró la API key. Revisa tu archivo .env")
        sys.exit(1)
    return OpenAI(base_url=BASE_URL, api_key=api_key)


def construir_system_prompt(contenido_faq: str) -> str:
    """Arma el system prompt concatenando las reglas fijas con el FAQ completo."""
    return f"""Eres un asistente de atención al cliente de Parachute S.A.
Tu trabajo es responder preguntas sobre el evento de paracaidismo usando
únicamente la información del documento que aparece más abajo.

Reglas:
- Responde solo con información que esté en el documento.
- Si la respuesta no está en el documento, di que no tienes esa información
  y sugiere contactar a la empresa por los medios que aparecen en el documento.
- No inventes datos ni uses conocimiento externo.
- Si el documento menciona varias condiciones para un mismo tema (por ejemplo,
  condiciones que parecen contradecirse), menciónalas todas en vez de escoger una sola.
- Responde en español, de forma breve y amable.

DOCUMENTO:
{contenido_faq}
"""


def preguntar(cliente: OpenAI, system_prompt: str, pregunta: str) -> str:
    """Envía la pregunta al modelo junto con el system prompt. Sin historial."""
    respuesta = cliente.chat.completions.create(
        model=MODELO,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pregunta},
        ],
    )
    return respuesta.choices[0].message.content


def main():
    contenido_faq = cargar_faq(ARCHIVO_FAQ)
    cliente = crear_cliente()
    system_prompt = construir_system_prompt(contenido_faq)

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
                respuesta = preguntar(cliente, system_prompt, pregunta)
                print(f"Agente: {respuesta}\n")
            except Exception:
                print("Agente: Hubo un problema al conectar con el servicio. Intenta de nuevo.\n")
    except KeyboardInterrupt:
        print("\nAgente: ¡Hasta pronto!")


if __name__ == "__main__":
    main()
