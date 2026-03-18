import openai
from config import OPENAI_API_KEY, OPENAI_MODEL

def refine_prompt(text: str, output_type: str = "Prompt (estándar)", context: str = "") -> str:
    """Takes a raw transcribed text and refines it into the requested output type."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY no configurada. Añádela en .env")
        
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    # Base instructions
    system_prompt = (
        "Eres un asistente experto en estructurar, ordenar y dar formato a textos. "
        "Tu tarea es procesar el input crudo (que puede estar desordenado) y convertirlo "
        f"en un resultado excelente y listo para usar de tipo: '{output_type}'.\n\n"
    )

    if context:
        system_prompt += f"CONTEXTO O PROPÓSITO ADICIONAL PROPORCIONADO POR EL USUARIO:\n{context}\n\n"
        
    system_prompt += (
        "REGLAS:\n"
        "1. Mantén la intención e información proporcionada por el usuario. Si el input está desordenado o es una lluvia de ideas, ordénalo con lógica (cronológica, temática o por secciones).\n"
        f"2. Adapta el tono, la estructura y el formato a lo que corresponde a un(a) '{output_type}'.\n"
        "3. IMPORTANTE CRÍTICO: NO inventes datos que no se aporten. Si es absolutamente necesario, deja marcadores claros (ej. [Nombre], [Fecha]).\n"
        "4. Si hay nombres de archivos, código o variables, no los modifiques ni traduzcas.\n"
        "5. Entrega DIRECTAMENTE el resultado final, sin introducciones tipo 'Aquí tienes...' ni comentarios extra, solo el texto listo para usar.\n"
    )

    if output_type == "Prompt (estándar)":
        system_prompt += "6. Al ser un Prompt, estructúralo en secciones claras: Contexto, Objetivo, Instrucciones y Restricciones.\n"
    elif output_type == "Correo electrónico":
        system_prompt += "6. Al ser un Correo electrónico, asegúrate de incluir un asunto adecuado (si no lo hay, sugiérelo al principio), saludo, cuerpo principal, y despedida.\n"
    elif output_type == "Informe":
        system_prompt += "6. Al ser un Informe, usa un formato estructurado con introducción, desarrollo en puntos clave y conclusión.\n"
    elif output_type == "Novela":
        system_prompt += "6. Al ser una Novela, usa un tono narrativo, une las escenas o personajes con descripciones ricas y flujo natural de la historia.\n"
    elif output_type == "Guion de vídeo":
        system_prompt += "6. Al ser un Guion de vídeo, estructura en introducción (gancho), desarrollo visual/hablado, y cierre con llamada a la acción si procede.\n"

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    )
    
    return response.choices[0].message.content.strip()
