"""
Keywords del router híbrido.

- STATIC_*: cierran a mensajes fijos (sin LLM).
- AGENT_KEYWORDS: intent de agente → keywords. Para agregar un agente nuevo,
  sumá una entrada acá y registrá el agente en create_container().
"""

# --- Intents estáticos (sin LLM) ---
GREETING_KEYWORDS: tuple[str, ...] = (
    "hola",
    "buenas",
    "buenos dias",
    "buenos días",
    "buen dia",
    "buen día",
    "buenas tardes",
    "buenas noches",
    "hey",
    "hi",
    "hello",
)

FAREWELL_KEYWORDS: tuple[str, ...] = (
    "chau",
    "adios",
    "adiós",
    "hasta luego",
    "nos vemos",
    "bye",
    "hasta pronto",
)

THANKS_KEYWORDS: tuple[str, ...] = (
    "gracias",
    "muchas gracias",
    "mil gracias",
    "se agradece",
    "thank",
)

# --- Intents de agentes (activables por keyword; si no matchea → LLM) ---
AGENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "rag": (
        "cuanto",
        "cuánto",
        "precio",
        "plazo",
        "tarda",
        "demora",
        "entrega",
        "envio",
        "envío",
        "producto",
        "productos",
        "carpeta",
        "carpetas",
        "centro de mesa",
        "centros de mesa",
        "disfraz",
        "disfraces",
        "material",
        "cotiz",
        "hacen",
        "ofrecen",
        "zona",
        "retiro",
        "faq",
    ),
    "orders": (
        "agendar",
        "agenda",
        "pedido",
        "pedidos",
        "reservar",
        "reserva",
        "encargar",
        "encargo",
        "encargame",
        "quiero encargar",
        "quiero pedir",
        "hacer un pedido",
        "tomar pedido",
        "solicitar",
        "solicitud",
        "disponibilidad",
        "para una fecha",
        "para el dia",
        "para el día",
    ),
}
