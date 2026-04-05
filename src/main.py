"""Punto de entrada principal para el análisis granular de una actividad.

Este script CLI permite obtener un reporte analítico detallado (NP, TSS, IF) 
de una actividad de Strava específica, imprimiendo el resultado en formato 
JSON para su integración con otras herramientas.
"""

import argparse
import sys
import os
import json
import logging

# Garantizar visibilidad del módulo raíz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.strava import StravaClient
from src.core.athlete import AthleteProfile
from src.core.analytics import ActivityMetricsCalculator

# Configuración de registro mínimo para asegurar salida JSON limpia
logger = logging.getLogger(__name__)

def analyze_activity(activity_id: int):
    """Descarga, procesa y resume una actividad de Strava como JSON.

    Args:
        activity_id (int): Identificador de sesión en Strava.
    """
    logging.disable(logging.INFO)  # Desactivar logs informativos para salida pura
    try:
        # Recuperación de datos desde Strava Cloud
        client = StravaClient()
        df_telemetria = client.get_activity_streams(activity_id)

        if df_telemetria is None or df_telemetria.empty:
            print(json.dumps({"error": f"No se encontró telemetría para la actividad {activity_id}."}))
            sys.exit(1)

        # Computación de métricas fisiológicas basadas en el perfil de atleta
        atleta = AthleteProfile()
        motor = ActivityMetricsCalculator(atleta)
        resumen = motor.process_full_activity_summary(df_telemetria)

        # Salida estándar serializada para consumo externo
        print(json.dumps(resumen, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.critical("Fallo catastrófico en el análisis de actividad: %s", e)
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PME Analyzer CLI - Analizador Fisiológico Instantáneo."
    )
    parser.add_argument("activity_id", type=int, help="ID de la actividad Strava.")
    
    args = parser.parse_args()
    analyze_activity(args.activity_id)
