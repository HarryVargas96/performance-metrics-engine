# src/services/coach.py
import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class GeminiCoach:
    """Motor de Coaching Generativo con Gemini."""

    def __init__(self, model_name="gemini-1.5-flash"):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.api_available = False
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.api_available = True

    def generate_coach_prompt(self, pmc_summary: dict, workout_summary: dict = None) -> str:
        pmc_context = f"ESTADO DEL ATLETA (PMC): CTL: {pmc_summary.get('ctl')}, ATL: {pmc_summary.get('atl')}, TSB: {pmc_summary.get('tsb')}"
        workout_context = f"SESIÓN: TSS: {workout_summary.get('training_stress_score')}, IF: {workout_summary.get('intensity_factor')}" if workout_summary else ""
        return f"Eres un entrenador experto de resistencia. Basado en:\n{pmc_context}\n{workout_context}\nDa un consejo breve en español."

    def get_coaching_advice(self, pmc_summary: dict, workout_summary: dict = None) -> str:
        if not self.api_available: return "[MODO DRY RUN] Gemini API Key no encontrada."
        try:
            response = self.model.generate_content(self.generate_coach_prompt(pmc_summary, workout_summary))
            return response.text
        except Exception as e: return f"Error: {e}"
