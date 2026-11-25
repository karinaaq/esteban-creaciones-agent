"""
Mensajes estáticos del chatbot (sin LLM).

Editá estas tuplas para cambiar el tono. El agente elige UNA al azar.
"""

# Saludos → intent "greeting"
GREETING_MESSAGES: tuple[str, ...] = (
    "Hola, soy el asistente de Esteban Creaciones. Puedo ayudarte con plazos, productos, precios orientativos y entrega.",
    "¡Buenas! Contame qué necesitás saber sobre carpetas, centros de mesa o disfraces.",
    "Hola, ¿en qué te puedo orientar hoy?",
)

# Despedidas → intent "farewell"
FAREWELL_MESSAGES: tuple[str, ...] = (
    "¡Chau! Cualquier duda sobre un encargo, acá estamos.",
    "Hasta luego. Que tengas un lindo día.",
    "Nos vemos. Cuando quieras cotizar o consultar plazos, escribime.",
)

# Agradecimientos → intent "thanks"
THANKS_MESSAGES: tuple[str, ...] = (
    "¡Con gusto! Si surge otra consulta, avisame.",
    "Para eso estamos. ¿Algo más sobre productos o plazos?",
    "De nada. Seguimos cuando quieras.",
)

# Fallback cuando el router no está seguro / intent general
GENERAL_MESSAGES: tuple[str, ...] = (
    "Puedo ayudarte con preguntas frecuentes (plazos, productos, precios orientativos, entrega). ¿Qué necesitás saber?",
    "No terminé de entender. Probá preguntarme por un producto, un plazo o una zona de entrega.",
)

MESSAGES_BY_INTENT: dict[str, tuple[str, ...]] = {
    "greeting": GREETING_MESSAGES,
    "farewell": FAREWELL_MESSAGES,
    "thanks": THANKS_MESSAGES,
    "general": GENERAL_MESSAGES,
}
