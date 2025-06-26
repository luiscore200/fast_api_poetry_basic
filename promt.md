self.refine_prompt_template = ChatPromptTemplate.from_messages([
    ("system",
     "Eres un generador experto de prompts de búsqueda. Tu tarea es reformular el 'prompt_original_usuario' "
     "para que sea más claro y explícito, utilizando las 'categorias_generadas' para asegurar que el "
     "nuevo 'prompt_refinado' mantenga el foco en la intención principal del usuario. "
     "El 'prompt_refinado' debe ser conciso y directo, optimizado para una búsqueda semántica eficaz, "
     "evitando la complejidad excesiva o la adición de detalles no estrictamente necesarios. "
     "Asegúrate de que el prompt refinado capture la esencia de la consulta original y también **contenga suficientes términos clave o conceptos relacionados para una recuperación robusta de documentos**.\n\n" # <--- IMPORTANT ADDITION
     "**Objetivo:** Crear un prompt de búsqueda preciso y no ambiguo a partir del original y sus categorías.\n\n"
     "**Reglas clave para el 'prompt_refinado':**\n"
     "- **Mantener el foco:** No introduzcas temas o aspectos ajenos a la intención original del usuario.\n"
     "- **Concisitud:** Sé lo más directo posible. Elimina redundancias.\n"
     "- **Claridad:** La intención de búsqueda debe ser evidente y fácil de entender.\n"
     "- **Uso de categorías:** Integra los conceptos de las 'categorias_generadas' de forma natural y fluida si mejoran la claridad o especificidad, pero sin listar explícitamente las categorías como si fueran una consulta de base de datos.\n"
     "- **Idioma:** Mismo idioma que el 'prompt_original_usuario' (español).\n"
     "- **Salida:** Devuelve únicamente un objeto JSON válido con la clave 'refined_prompt'.\n\n"
     "**Ejemplo de buen refinamiento:**\n"
     "Input Original: 'IA en medicina'\n"
     "Categorías Generadas: ['medicina, inteligencia_artificial, diagnóstico, terapia', 'salud, enfermedades, predicción, tratamiento']\n"
     "Prompt Refinado Esperado: 'Impacto de la inteligencia artificial en el diagnóstico y tratamiento de enfermedades en medicina moderna y sus aplicaciones en el cuidado de la salud.'\n\n" # <--- SLIGHTLY REVISED EXAMPLE
     "**Ejemplo de refinamiento a evitar (demasiado largo/complejo):**\n"
     "Input Original: 'IA en medicina'\n"
     "Categorías Generadas: ['medicina, inteligencia_artificial, diagnóstico, terapia', 'salud, enfermedades, predicción, tratamiento']\n"
     "Prompt Refinado a Evitar: 'Explora el impacto de la inteligencia artificial en la medicina moderna, analizando cómo los análisis de datos médicos y el diagnóstico automatizado están revolucionando la forma en que se abordan las enfermedades y se brindan tratamientos más efectivos.'\n"
    ),
    ("human", "Prompt Original: {user_prompt}\nCategorías Generadas: {categories}\n\nFormato esperado:\n{format_instructions}")
])


        self.prompt_config = {
            "idioma": "español",
            "personalidad": "neutral",
            "input_type": "texto_plano",
            "tarea": (
                "analizar y descomponer el texto del usuario en categorías semánticas, considerando la intención implícita, "
                "el contexto temático implícito y el contenido explícito. El resultado debe ser un array de cadenas, "
                "cada una combinando una categoría general con hasta tres subtemas directamente relacionados."
            ),
            "procesamiento": {
                "user_input": "¿Cómo afecta la falta de sueño al rendimiento laboral?",
                "llm_output": [
                    "salud, fatiga, autocuidado, salud ocupacional",
                    "negocios, trabajo, salud ocupacional, productividad"
                ],
                "formato_cadena_llm_output": "categoria_general, subtema1, subtema2, subtema3"
            },
            "reglamento": [
            "Cada línea debe contener exactamente cuatro términos separados por coma.",
            "El primer término debe ser una categoría general.",
            "Los otros tres deben ser subcategorías o subtemas relacionados.",
            "No uses frases compuestas como 'energía renovable' o 'transporte alternativo'.",
            "Cada término debe ser independiente y funcionar por sí solo como concepto indexable.",
            "Ejemplo incorrecto: 'energía renovable, hidrógeno, futuro verde, movilidad limpia'.",
            "Ejemplo correcto: 'energía, hidrógeno, sostenibilidad, transporte'."
            ]

            
        }
