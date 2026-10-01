import os

import discord
from anthropic import AsyncAnthropic

ANTHROPIC_KEY = os.environ["ANTHROPIC_KEY"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1000
DISCORD_LIMIT = 2000

# Cada canal tiene su propio "rol" (las instrucciones que sigue Claude).
ROLES = {
    "content-strategist": (
        "Eres un Estratega de Contenido experto. Ante cualquier mensaje del usuario, "
        "responde siempre en español con esta estructura:\n"
        "1. **3 opciones de gancho**: tres ganchos distintos y llamativos.\n"
        "2. **Guion completo o caption**: un guion listo para grabar o un caption listo para publicar.\n"
        "3. **Hashtags**: una lista de hashtags relevantes.\n"
        "4. **Ángulo alternativo**: otra forma diferente de abordar el mismo tema."
    ),
    "researcher": (
        "Eres un Investigador de Contenido experto. Ante cualquier mensaje del usuario, "
        "responde siempre en español con esta estructura:\n"
        "1. **Por qué funciona**: explica por qué este contenido funciona (psicología, formato, algoritmo).\n"
        "2. **Cómo aplicarlo**: pasos concretos para aplicarlo.\n"
        "3. **Qué probar**: experimentos o variaciones a probar.\n"
        "Termina siempre con **Siguiente paso**: una única acción concreta para hacer ahora."
    ),
    "product-builder": (
        "Eres un Constructor de Producto experto en productos digitales. Ante cualquier mensaje "
        "del usuario, responde siempre en español con esta estructura:\n"
        "1. **Evaluación del mercado**: demanda, público objetivo y competencia.\n"
        "2. **Descripción del producto**: qué es y qué problema resuelve.\n"
        "3. **Secciones**: escribe las secciones o módulos del producto.\n"
        "4. **5 nombres**: cinco opciones de nombre para el producto.\n"
        "5. **Precio recomendado**: un precio concreto y por qué."
    ),
}

intents = discord.Intents.default()
intents.message_content = True  # Necesario para leer el texto de los mensajes

client = discord.Client(intents=intents)
anthropic = AsyncAnthropic(api_key=ANTHROPIC_KEY)


def split_message(text, limit=DISCORD_LIMIT):
    """Discord solo permite 2000 caracteres por mensaje, así que partimos el texto."""
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


@client.event
async def on_ready():
    print(f"Bot conectado como {client.user}")


@client.event
async def on_message(message):
    # No responder a otros bots (ni a sí mismo).
    if message.author.bot:
        return

    channel_name = getattr(message.channel, "name", None)
    system_prompt = ROLES.get(channel_name)
    if system_prompt is None:
        return  # Ignorar mensajes de cualquier otro canal

    if not message.content.strip():
        return

    async with message.channel.typing():
        try:
            response = await anthropic.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": message.content}],
            )
            reply = "".join(
                block.text for block in response.content if block.type == "text"
            )
        except Exception as e:
            print(f"Error al llamar a Anthropic: {e}")
            reply = "Lo siento, hubo un error al generar la respuesta. Inténtalo de nuevo."

    for chunk in split_message(reply or "No obtuve respuesta."):
        await message.channel.send(chunk)


client.run(DISCORD_TOKEN)
