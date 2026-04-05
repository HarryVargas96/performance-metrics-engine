import argparse
import sys
import os
import json
import logging

# Añadir el raíz del proyecto al path para que "from src..." funcione
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.strava import StravaClient
from src.core.athlete import AthleteProfile
from src.core.analytics import ActivityMetricsCalculator

# Mutear logs en INFO para que la salida sea JSON puro
logging.getLogger().setLevel(logging.WARNING)

def analyze_activity(activity_id):
    try:
        # 1. Configurar cliente y descargar datos de la nube
        client = StravaClient()
        df_telemetria = client.get_activity_streams(activity_id)

        if df_telemetria is None or df_telemetria.empty:
            print(json.dumps({"error": f"No se encontró telemetría para la actividad {activity_id}."}))
            sys.exit(1)

        # 2. Inicializar Perfil (Auto-carga tu FTP desde config.py)
        mi_perfil = AthleteProfile()
        motor_metricas = ActivityMetricsCalculator(mi_perfil)

        # 3. Procesar Inteligencia Fisiológica
        resultados = motor_metricas.process_full_activity_summary(df_telemetria)

        # 4. Imprimir JSON estrictamente limpio a la terminal
        print(json.dumps(resultados, indent=2, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analizador Fisiológico de Strava CLI (Versión Core/API)."
    )
    parser.add_argument("activity_id", type=int, help="El ID de la actividad de Strava.")
    
    args = parser.parse_args()
    analyze_activity(args.activity_id)
