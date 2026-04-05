"""Motor de entrenamiento inteligente basado en modelos generativos (Gemini).

Este servicio actúa como un Virtual Coach que interpreta los datos del PMC y de 
sesiones recientes para ofrecer recomendaciones personalizadas sobre 
recuperación, carga e intensidad.
"""

import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# Registro local de eventos de coaching
logger = logging.getLogger(__name__)

class GeminiCoach:
    """Motor de Coaching Generativo que utiliza Google Gemini.

    Attributes:
        api_available (bool): Indica si la API Key de Gemini está configurada.
        model (genai.GenerativeModel): Instancia del modelo de IA cargado.
    """

    def __init__(self, model_name="gemini-1.5-flash"):
        """Inicializa el Coach de IA configurando las credenciales de Google.

        Args:
            model_name (str): Nombre del modelo de Gemini a utilizar.
        """
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY no encontrada en el .env. Modo Coaching desactivado.")
            self.api_available = False
        else:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name)
                self.api_available = True
                logger.info("Virtual Coach inicializado satisfactoriamente (%s).", model_name)
            except Exception as e:
                logger.error("Fallo al inicializar el modelo Gemini: %s", e)
                self.api_available = False

    def generate_coach_prompt(self, pmc_summary: dict, workout_summary: dict = None) -> str:
        """Construye el prompt estructurado para que la IA actúe como entrenador.

        Args:
            pmc_summary (dict): Estado actual (CTL, ATL, TSB).
            workout_summary (dict, optional): Datos analíticos de la última sesión.

        Returns:
            str: Prompt completo listo para enviar a la IA.
        """
        pmc_context = (
            f"ESTADO FISIOLÓGICO: Fitness (CTL): {pmc_summary.get('ctl')}, "
            f"Fatiga (ATL): {pmc_summary.get('atl')}, Forma (TSB): {pmc_summary.get('tsb')}"
        )
        
        workout_context = ""
        if workout_summary:
            workout_context = (
                f"\nDETALLE SESIÓN: TSS: {workout_summary.get('training_stress_score')}, "
                f"Factor Intensidad (IF): {workout_summary.get('intensity_factor')}, "
                f"Fuente de Estrés: {workout_summary.get('tss_source')}"
            )
            
        system_instruction = (
            "Eres un entrenador experto de deportes de resistencia (Ciclismo y Correr). "
            "Usa un tono profesional, motivador pero basado en ciencia. "
            "Prioriza la prevención de sobreentrenamiento (TSB muy negativo) y la "
            "consistencia (CTL progresivo)."
        )
        
        return f"{system_instruction}\nBasado en estos datos:\n{pmc_context}{workout_context}\nDa un consejo breve (máximo 400 caracteres) en español."

    def get_coaching_advice(self, pmc_summary: dict, workout_summary: dict = None) -> str:
        """Envía los datos al modelo y retorna la recomendación del entrenador.

        Args:
            pmc_summary (dict): Estado fisiológico.
            workout_summary (dict, optional): Resumen de la sesión.

        Returns:
            str: Texto generado por la IA o mensaje de error/bypass.
        """
        if not self.api_available:
            logger.v("Bypass de Coaching: API no disponible.")
            return "[MODO DRY RUN] Gemini API Key no encontrada. Revisa tu archivo .env."
            
        try:
            logger.v("Generando recomendación de IA para el atleta...")
            prompt = self.generate_coach_prompt(pmc_summary, workout_summary)
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error("Excepción en la llamada a Gemini: %s", e)
            return f"Hubo un problema al contactar con tu entrenador IA: {e}"
