import asyncio
import json
import os
from typing import List, Optional, Dict, Any, Union

# Importar componentes de Langchain para carga y división de documentos
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader, WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.runnables import Runnable

# Importar el servicio de embeddings si se va a usar para indexación (mantener por si se añade después)
from src.common.services.embeddings_service import get_embeddings
# Importar el proveedor de LLM para interactuar con el modelo
from src.common.providers.llm_provider import LLMProvider
# Importar la excepción personalizada
from src.common.types.errors_types import DocumentServiceError

# Importar pandas para manejar Excel (requiere 'pandas' instalado)
try:
    import pandas as pd
except ImportError:
    pd = None
    print("Advertencia: La librería 'pandas' no está instalada. La funcionalidad de Excel no estará disponible.")

# Definir el modelo Pydantic para la salida estructurada del LLM
class GeneratedMetadata(BaseModel):
    """Metadata generada por el LLM."""
    tags: List[str] = Field(default_factory=list, description="Lista de tags generados por la IA.")
    categories: List[str] = Field(default_factory=list, description="Lista de categorías generadas por la IA.")

class DocumentService:
    """
    Servicio para cargar, procesar y gestionar documentos, incluyendo conversión,
    procesamiento con IA y división en fragmentos.
    """
    def __init__(self, llm_provider: LLMProvider):
        """
        Inicializa el DocumentService con una instancia de LLMProvider.

        Args:
            llm_provider: Instancia del LLMProvider para interactuar con el LLM.
        """
        self.llm_provider = llm_provider

    async def load_document(self, file_path: str) -> List[Document]:
        """
        Carga un documento desde una ruta de archivo.
        Soporta PDF y archivos de texto (.txt).

        Args:
            file_path: La ruta al archivo a cargar.

        Returns:
            Una lista de objetos Document de Langchain.
        """
        try:
            if file_path.lower().endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file_path.lower().endswith(".txt"):
                 loader = TextLoader(file_path)
            # Puedes añadir más tipos de cargadores aquí
            # elif file_path.lower().startswith("http"):
            #     loader = WebBaseLoader(file_path)
            else:
                raise ValueError(f"Tipo de archivo no soportado para carga: {file_path}")

            # Langchain loaders pueden tener métodos asíncronos como aload
            # Si no, usar run_in_threadpool si el método es síncrono
            # Asumiendo que PyPDFLoader y TextLoader tienen load() síncrono
            from anyio.to_thread import run_in_threadpool
            documents = await run_in_threadpool(loader.load)

            return documents

        except FileNotFoundError:
             raise DocumentServiceError(
                message=f"Archivo no encontrado: {file_path}",
                details=f"El archivo en la ruta '{file_path}' no existe."
            )
        except Exception as e:
            print(f"Error interno al cargar el documento: {e}")
            raise DocumentServiceError(
                message=f"Fallo al cargar el documento desde '{file_path}'",
                details=str(e)
            ) from e

    async def excel_to_text(self, file_path: str) -> str:
        """
        Convierte el contenido de un archivo Excel a texto plano.
        Requiere la librería 'pandas'.

        Args:
            file_path: La ruta al archivo Excel (.xlsx, .xls).

        Returns:
            Una cadena de texto plano con el contenido del Excel.
        """
        if pd is None:
             raise DocumentServiceError(
                message="Librería 'pandas' no encontrada",
                details="La conversión de Excel requiere la instalación de 'pandas'."
            )
        try:
            # Leer todas las hojas del Excel
            excel_data = pd.read_excel(file_path, sheet_name=None)
            text_content = ""
            for sheet_name, df in excel_data.items():
                text_content += f"--- Hoja: {sheet_name} ---\n"
                # Convertir cada hoja a una cadena de texto (ej. CSV o simplemente valores separados)
                # Aquí usamos to_string() que es simple, puedes ajustar el formato si es necesario
                text_content += df.to_string(index=False)
                text_content += "\n\n"
            return text_content.strip()
        except FileNotFoundError:
             raise DocumentServiceError(
                message=f"Archivo Excel no encontrado: {file_path}",
                details=f"El archivo en la ruta '{file_path}' no existe."
            )
        except Exception as e:
            print(f"Error interno al convertir Excel a texto: {e}")
            raise DocumentServiceError(
                message=f"Fallo al convertir el archivo Excel '{file_path}' a texto",
                details=str(e)
            ) from e

    def is_json(self, text: str) -> bool:
        """
        Detecta si una cadena de texto es un JSON válido.

        Args:
            text: La cadena de texto a verificar.

        Returns:
            True si es JSON válido, False en caso contrario.
        """
        if not isinstance(text, str) or not text.strip():
            return False
        try:
            json.loads(text)
            return True
        except json.JSONDecodeError:
            return False

    def json_to_text(self, json_data: Union[str, Dict, List]) -> str:
        """
        Convierte datos JSON (cadena, dict o lista) a una cadena de texto plano formateada.

        Args:
            json_data: Los datos JSON a convertir.

        Returns:
            Una cadena de texto plano representando los datos JSON.
        """
        try:
            if isinstance(json_data, str):
                # Si ya es una cadena, intentar parsearla para formatearla
                parsed_json = json.loads(json_data)
            else:
                parsed_json = json_data # Ya es dict o list

            # Usar json.dumps con indent para una representación legible
            return json.dumps(parsed_json, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
             raise DocumentServiceError(
                message="Entrada no es un JSON válido",
                details="La cadena proporcionada no pudo ser parseada como JSON."
            )
        except Exception as e:
            print(f"Error interno al convertir JSON a texto: {e}")
            raise DocumentServiceError(
                message="Fallo al convertir datos JSON a texto",
                details=str(e)
            ) from e

    async def process_with_llm(
        self,
        text_content: str,
        original_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Procesa el texto plano y la metadata original con un LLM para enriquecer
        la descripción y generar tags/categorías adicionales.

        Args:
            text_content: El texto plano del documento.
            original_metadata: La metadata original del documento.

        Returns:
            La metadata actualizada incluyendo el campo 'generated' y la fusión
            de tags/categorías.
        """
        # Definir el prompt para el LLM
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente experto en análisis de documentos y preparación de contenido para sistemas de búsqueda basados en inteligencia artificial y embeddings vectoriales.

Tu tarea consiste en analizar el siguiente texto (proveniente de un documento empresarial) junto con su metadata original. Basado en este contenido debes:

1. Generar una descripción optimizada y enriquecida del texto, pensando en que será dividida en fragmentos y luego vectorizada para búsquedas semánticas. La descripción debe ser precisa, completa, clara y útil para motores de búsqueda de IA.
2. Generar tags y categorías relevantes que NO estén presentes en la metadata original. Estos deben ayudar a clasificar y recuperar el documento desde distintos ángulos temáticos o semánticos.
3. Tu respuesta DEBE ser un objeto JSON que siga estrictamente el siguiente formato:

{{
  "enriched_description": "...", // Descripción optimizada para chunking y embeddings
  "generated": {{
    "tags": ["tag1", "tag2"],       // Tags generados por IA (no duplicados)
    "categories": ["cat1", "cat2"]  // Categorías generadas por IA
  }}
}}

Metadata original (proporcionada como referencia):
{metadata}

Texto del documento:
{document_text}

IMPORTANTE:
- Asegúrate de que la respuesta sea SOLO un objeto JSON válido, sin explicaciones adicionales.
- No repitas ni copie el texto completo del documento original.
- La descripción debe estar en lenguaje natural, pero enfocada a captar los conceptos más importantes del documento.
"""),
            ("human", "Genera la descripción enriquecida y la metadata adicional para este documento.")
        ])

        # Definir el esquema de salida Pydantic para el LLM
        class LLMOutputSchema(BaseModel):
            enriched_description: str = Field(description="La descripción enriquecida o resumida del documento.")
            generated: GeneratedMetadata = Field(description="Metadata generada por la IA.")

        # Preparar la cadena de Langchain con salida estructurada
        # Usamos with_structured_output para forzar al LLM a adherirse al esquema Pydantic
        # Esto requiere un LLM que soporte function calling o herramientas (tool_calling)
        # Si el LLM no lo soporta, se puede usar un OutputParser, pero es menos robusto.
        # Asumimos que el LLM configurado en LLMProvider soporta tool_calling.
        try:
            # Inyectar el esquema JSON en el prompt
            prompt_template_structured = prompt_template.partial(schema=LLMOutputSchema.schema_json(indent=2))

            llm_chain_structured: Runnable = prompt_template_structured | self.llm_provider.get_llm().with_structured_output(LLMOutputSchema)

            llm_output: LLMOutputSchema = await llm_chain_structured.ainvoke({
                "metadata": json.dumps(original_metadata, indent=2, ensure_ascii=False),
                "document_text": text_content
            })

            # Fusionar tags y categorías (usando la salida del nuevo esquema)
            original_tags = set(original_metadata.get("tags", []))
            original_categories = set(original_metadata.get("categories", []))
            generated_tags = set(llm_output.generated.tags)
            generated_categories = set(llm_output.generated.categories)

            merged_tags = list(original_tags.union(generated_tags))
            merged_categories = list(original_categories.union(generated_categories))

            # Crear la metadata actualizada
            updated_metadata = original_metadata.copy()
            updated_metadata["tags"] = merged_tags
            updated_metadata["categories"] = merged_categories
            updated_metadata["generated"] = llm_output.generated.dict() # Guardar la salida cruda de la IA

            # Retornar la descripción enriquecida y la metadata actualizada
            return {
                "enriched_description": llm_output.enriched_description,
                "updated_metadata": updated_metadata
            }

        except Exception as e:
            print(f"Error interno al procesar con LLM: {e}")
            raise DocumentServiceError(
                message="Fallo al procesar el documento con el modelo de IA",
                details=str(e)
            ) from e


    async def split_documents(
        self,
        documents: List[Document],
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Document]:
        """
        Divide una lista de documentos en fragmentos más pequeños y añade el índice
        del fragmento a la metadata.

        Args:
            documents: Lista de objetos Document de Langchain.
            chunk_size: Tamaño máximo de cada fragmento.
            chunk_overlap: Número de caracteres de solapamiento entre fragmentos.

        Returns:
            Una lista de objetos Document fragmentados con metadata actualizada.
        """
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            # split_documents es síncrono, usar run_in_threadpool
            from anyio.to_thread import run_in_threadpool
            split_docs = await run_in_threadpool(text_splitter.split_documents, documents)

            # Añadir chunk_id a la metadata de cada fragmento
            for i, doc in enumerate(split_docs):
                if not isinstance(doc.metadata, dict):
                    doc.metadata = {} # Asegurar que metadata es un dict
                doc.metadata["chunk_id"] = i

            return split_docs
        except Exception as e:
            print(f"Error interno al dividir documentos: {e}")
            raise DocumentServiceError(
                message="Fallo al dividir documentos",
                details=str(e)
            ) from e

    # Método orquestador para procesar un documento completo
    async def process_full_document(
        self,
        document_input: Union[str, bytes], # Puede ser texto plano o contenido de archivo
        metadata: Dict[str, Any],
        process_with_ai: bool = True, # Flag para decidir si pasar por el LLM
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Procesa un documento completo desde la entrada (texto o archivo) hasta
        obtener una lista de fragmentos con metadata enriquecida.

        Args:
            document_input: El contenido del documento (texto plano o bytes de archivo).
            metadata: La metadata inicial del documento. Debe incluir 'formato'.
            process_with_ai: Si es True, el texto se pasa por el LLM para enriquecimiento
                             y generación de metadata adicional.
            chunk_size: Tamaño de los fragmentos para la división.
            chunk_overlap: Solapamiento de los fragmentos.

        Returns:
            Una lista de diccionarios, donde cada diccionario representa un fragmento
            con su contenido y metadata actualizada.
        """
        text_content = ""
        original_format = metadata.get("formato")

        if original_format == "texto":
            if not isinstance(document_input, str):
                 raise DocumentServiceError(
                    message="Entrada inválida para formato 'texto'",
                    details="Se esperaba una cadena de texto para el formato 'texto'."
                )
            text_content = document_input
        elif original_format == "json":
             if isinstance(document_input, bytes):
                 # Si es bytes (ej. subido como archivo), intentar decodificar
                 try:
                     document_input = document_input.decode('utf-8')
                 except Exception as e:
                      raise DocumentServiceError(
                        message="Fallo al decodificar archivo JSON",
                        details=str(e)
                    ) from e

             if isinstance(document_input, str):
                 # Si es cadena, convertir a texto plano
                 text_content = self.json_to_text(document_input)
             elif isinstance(document_input, (Dict, List)):
                 # Si ya es dict/list, convertir a texto plano
                 text_content = self.json_to_text(document_input)
             else:
                 raise DocumentServiceError(
                    message="Entrada inválida para formato 'json'",
                    details="Se esperaba una cadena JSON, dict, list o bytes para el formato 'json'."
                )

        elif original_format == "excel":
             if not isinstance(document_input, bytes):
                 raise DocumentServiceError(
                    message="Entrada inválida para formato 'excel'",
                    details="Se esperaban bytes del archivo para el formato 'excel'."
                )
             # Guardar temporalmente el archivo para que pandas pueda leerlo
             temp_file_path = f"./temp_upload_{os.getpid()}.xlsx" # Usar PID para evitar colisiones
             try:
                 with open(temp_file_path, "wb") as f:
                     f.write(document_input)
                 text_content = await self.excel_to_text(temp_file_path)
             finally:
                 # Limpiar el archivo temporal
                 if os.path.exists(temp_file_path):
                     os.remove(temp_file_path)
        # Puedes añadir más formatos de archivo aquí (ej. .docx, .csv)
        # elif original_format == "pdf":
        #     # Cargar PDF usando load_document y luego extraer texto si es necesario
        #     if not isinstance(document_input, bytes):
        #          raise DocumentServiceError(...)
        #     temp_file_path = f"./temp_upload_{os.getpid()}.pdf"
        #     try:
        #         with open(temp_file_path, "wb") as f:
        #             f.write(document_input)
        #         documents = await self.load_document(temp_file_path)
        #         text_content = "\n".join([doc.page_content for doc in documents])
        #     finally:
        #         if os.path.exists(temp_file_path):
        #             os.remove(temp_file_path)

        else:
            raise DocumentServiceError(
                message=f"Formato de documento no soportado: {original_format}",
                details="Los formatos soportados son 'texto', 'json', 'excel'."
            )

        enriched_description = text_content
        updated_metadata = metadata.copy()

        if process_with_ai:
            # Procesar el texto con el LLM para enriquecer y generar metadata
            llm_result = await self.process_with_llm(text_content, metadata)
            enriched_description = llm_result["enriched_description"]
            updated_metadata = llm_result["updated_metadata"]
        else:
             # Si no se procesa con IA, añadir campo 'generated' vacío
             updated_metadata["generated"] = {"tags": [], "categories": []}


        # Crear un objeto Document de Langchain con el texto enriquecido y la metadata
        # Esto es necesario para usar split_documents
        full_document = Document(page_content=enriched_description, metadata=updated_metadata)

        # Dividir el documento en fragmentos
        split_docs = await self.split_documents([full_document], chunk_size, chunk_overlap)

        # Formatear la salida como lista de diccionarios con metadata separada
        output_chunks = []
        for doc in split_docs:
            # La metadata en doc.metadata ya contiene la fusión y el campo 'generated'
            # Separamos la metadata original de la generada para la salida final
            original_meta = {k: v for k, v in metadata.items() if k not in ["tags", "categories"]} # Excluir tags/cats originales si se fusionaron
            # O mejor, mantener la metadata original intacta y añadir la generada
            # Necesitamos la metadata original que se pasó al método process_full_document
            # La metadata en doc.metadata es la 'updated_metadata' del paso anterior.
            # Vamos a reconstruir la estructura deseada.

            chunk_data = {
                "chunk_id": doc.metadata.get("chunk_id"),
                "content": doc.page_content,
                "original": {"tags": metadata.get("tags", []), "categories": metadata.get("categories", [])}, # Incluir solo tags y categories originales
                "generated": doc.metadata.get("generated", {"tags": [], "categories": []}), # Usar el campo 'generated' de la metadata actualizada
                # Opcional: incluir las listas fusionadas si son útiles
                "merged_tags": doc.metadata.get("tags", []),
                "merged_categories": doc.metadata.get("categories", [])
            }
            output_chunks.append(chunk_data)

        return output_chunks

# Ejemplo de uso (requiere configurar AIService y un LLM)
# async def main():
#     # Configurar AIService (asegúrate de tener las variables de entorno para el LLM)
#     # from src.common.providers.llm_provider import get_llm_instance # Ya importado
#     # ai_service_instance = AIService(llm_provider_name="groq", model="llama3-8b-8192") # O "openai"

#     # doc_service = DocumentService(ai_service=ai_service_instance)

#     # Ejemplo con texto plano
#     # text_doc = "Este es un documento de prueba sobre laptops y accesorios de oficina."
#     # initial_metadata = {"empresa_id": "test_empresa", "categorias": ["tecnologia"], "tags": ["prueba"], "formato": "texto"}
#     # try:
#     #     processed_chunks = await doc_service.process_full_document(text_doc, initial_metadata, process_with_ai=True)
#     #     print("Procesamiento de texto plano completado:")
#     #     for chunk in processed_chunks:
#     #         print(json.dumps(chunk, indent=2, ensure_ascii=False))
#     # except DocumentServiceError as e:
#     #      print(f"Error en DocumentService: {e.message} - Detalles: {e.details}")

#     # Ejemplo con JSON (simulado)
#     # json_doc_data = {"productos": [{"nombre": "Monitor LED 27", "precio": 250}, {"nombre": "Teclado mecánico", "precio": 120}]}
#     # initial_metadata_json = {"empresa_id": "test_empresa", "categorias": ["electronica"], "tags": ["json_test"], "formato": "json"}
#     # try:
#     #     processed_chunks_json = await doc_service.process_full_document(json_doc_data, initial_metadata_json, process_with_ai=True)
#     #     print("\nProcesamiento de JSON completado:")
#     #     for chunk in processed_chunks_json:
#     #         print(json.dumps(chunk, indent=2, ensure_ascii=False))
#     # except DocumentServiceError as e:
#     #      print(f"Error en DocumentService: {e.message} - Detalles: {e.details}")


# if __name__ == "__main__":
#     # asyncio.run(main())
#     pass # No ejecutar el ejemplo automáticamente
