# Agente de FAQs - Parachute S.A.

Agente de línea de comandos que responde preguntas sobre el evento de
paracaidismo de Parachute S.A. (Guatemala, 29 de septiembre de 2026).

## Arquitectura (RAG simple)

Esta es la versión más simple posible de RAG: se lee el archivo `faq.txt`
completo y se inyecta como texto dentro del system prompt del modelo. El
modelo responde únicamente con base en ese contenido.

No se usan embeddings, vector databases, chunking ni búsqueda semántica,
porque el documento de FAQs es pequeño y cabe completo en el contexto del
modelo. Para un caso así, agregar retrieval semántico sería complejidad
innecesaria.

Cada pregunta se envía de forma independiente (sin memoria de conversación),
por lo que el historial de preguntas anteriores no afecta las respuestas.

## Requisitos previos

- Python 3.10 o superior.
- Una cuenta en [NVIDIA Build](https://build.nvidia.com) para obtener una API key.

## Instalación

```bash
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # y pegar la API key adentro
python main.py
```

## Obtener la API key

1. Entra a [build.nvidia.com](https://build.nvidia.com) y crea una cuenta o inicia sesión.
2. Busca el modelo `meta/llama-3.2-11b-vision-instruct` (o cualquier modelo disponible
   para tu cuenta; algunos modelos requieren acceso habilitado por NVIDIA).
3. Genera una API key desde tu perfil.
4. Pega la key en el archivo `.env`:
   ```
   NVIDIA_API_KEY=nvapi-...
   ```

## Ejemplos de uso

```
Tú: ¿Cuál es el límite de peso para el salto?
Agente: El límite de peso máximo es de 100 kg (220 lbs)...

Tú: ¿Qué métodos de pago aceptan?
Agente: Aceptamos transferencias bancarias, tarjetas de crédito/débito...

Tú: ¿Qué ropa debo llevar?
Agente: Recomendamos ropa cómoda y deportiva...

Tú: ¿Hay descuento para estudiantes?
Agente: Lo siento, no tengo esa información en las preguntas frecuentes del evento...
```

Para salir, escribe `Bye` o presiona `Ctrl-C`.

## Seguridad

El archivo `.env` está en `.gitignore` y nunca se sube al repositorio. Usa
`.env.example` como plantilla para configurar tu propia API key localmente.
