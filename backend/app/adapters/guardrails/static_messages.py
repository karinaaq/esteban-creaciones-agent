"""
Respuestas estáticas cuando el guardrail bloquea o se abstiene.

Editá estas tuplas para cambiar el tono. Se elige UNA al azar.
"""

EMPTY_MESSAGES: tuple[str, ...] = (
    "Necesito un mensaje con tu consulta para poder ayudarte.",
    "Escribime tu pregunta sobre productos, plazos o entrega y te oriento.",
)

TOO_LONG_MESSAGES: tuple[str, ...] = (
    "Tu mensaje es demasiado largo. Resumí la consulta en unas pocas oraciones, por favor.",
    "Para ayudarte mejor, acortá el mensaje y contame lo esencial de tu pedido o duda.",
)

INJECTION_MESSAGES: tuple[str, ...] = (
    "No puedo seguir instrucciones que intentan alterar mi comportamiento. "
    "Si tenés una consulta sobre productos, plazos o entrega de Esteban Creaciones, escribimela.",
    "Ese tipo de pedido no lo puedo procesar. Contame qué necesitás saber del catálogo o los plazos.",
)

ABUSE_MESSAGES: tuple[str, ...] = (
    "Prefiero mantener la conversación respetuosa. ¿En qué puedo ayudarte con Esteban Creaciones?",
    "No puedo continuar con ese contenido. Si tenés una consulta de productos o plazos, estoy para ayudarte.",
)

OFF_TOPIC_UNSAFE_MESSAGES: tuple[str, ...] = (
    "No puedo ayudar con ese pedido. Si querés, consultame por carpetas, centros de mesa, disfraces o entrega.",
    "Esa solicitud está fuera de lo que puedo hacer. Probá con una pregunta sobre el emprendimiento creativo.",
)

WEAK_RETRIEVE_MESSAGES: tuple[str, ...] = (
    "Encontré poca evidencia confiable en la base de conocimiento para responder con seguridad. "
    "¿Podés reformular la pregunta (producto, plazo o entrega)?",
    "No tengo contexto suficiente para contestarte bien. Probá ser más específica con el producto o el plazo.",
)

# category del judge → tupla de mensajes
BLOCK_MESSAGES_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "empty": EMPTY_MESSAGES,
    "too_long": TOO_LONG_MESSAGES,
    "injection": INJECTION_MESSAGES,
    "jailbreak": INJECTION_MESSAGES,
    "prompt_injection": INJECTION_MESSAGES,
    "abuse": ABUSE_MESSAGES,
    "hate": ABUSE_MESSAGES,
    "violence": ABUSE_MESSAGES,
    "sexual": ABUSE_MESSAGES,
    "self_harm": ABUSE_MESSAGES,
    "illegal": OFF_TOPIC_UNSAFE_MESSAGES,
    "other": OFF_TOPIC_UNSAFE_MESSAGES,
    "unsafe": OFF_TOPIC_UNSAFE_MESSAGES,
    "weak_retrieve": WEAK_RETRIEVE_MESSAGES,
    "no_hits": WEAK_RETRIEVE_MESSAGES,
}
