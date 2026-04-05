"""Generador de contexto estructurado para el Virtual Coach (LLM).

Este módulo recopila datos fisiológicos, tendencias de carga de 8 semanas
y sensaciones subjetivas para enviarlos como contexto a un modelo de IA.
"""

import os
import sys
import pandas as pd
import json
import logging
from datetime import datetime, timedelta

# Garantizar visibilidad del módulo raíz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.athlete import AthleteProfile
from src.services.sync import run_historical_sync, generate_pmc_report

# Configuración de registro local
logger = logging.getLogger(__name__)

def get_llm_context(days_back=90) -> dict:
    """Consolida el estado actual y tendencias del atleta en un JSON estructurado.

    Extrae el PMC, calcula TSS semanal de los últimos 2 meses y resume
    las sensaciones subjetivas (RPE, Notas) de la última semana.

    Args:
        days_back (int): Ventana de historial para el cálculo de PMC.

    Returns:
        dict: Diccionario listo para ser convertido a JSON por el LLM.
    """
    try:
        athlete = AthleteProfile()
        df_history = run_historical_sync(days=days_back)
        pmc_report = generate_pmc_report(df_history)
    except Exception as e:
        logger.error("Error al generar el contexto para LLM: %s", e)
        return {"error": str(e)}

    # 1. Análisis de tendencias: 8 semanas de carga acumulativa
    df_daily = df_history.copy()
    df_daily['date'] = pd.to_datetime(df_daily['date'], utc=True).dt.tz_localize(None).dt.normalize()
    df_daily = df_daily.groupby('date')['tss'].sum()
    
    hoy = pd.Timestamp.now().normalize()
    inicio_8w = hoy - timedelta(days=55) # Garantiza 56 días de ventana
    idx_8w = pd.date_range(inicio_8w, hoy, freq='D')
    
    df_resampled = df_daily.reindex(idx_8w, fill_value=0)
    # Agrupamos en bloques de 7 días exactos
    weekly_tss = [round(float(df_resampled.iloc[i : i+7].sum()), 1) for i in range(0, 56, 7)]
    
    # 2. Resumen detallado: Últimos 7 días activos
    semana_atras = hoy - pd.Timedelta(days=7)
    # Forzamos tz_localize(None) para evitar error de comparación con 'hoy' (naive)
    df_recent = df_history[pd.to_datetime(df_history['date'], utc=True).dt.tz_localize(None).dt.normalize() >= semana_atras].sort_values('date')
    
    last_7_days_list = []
    for _, row in df_recent.iterrows():
        workout = {
            "date": row['date'].strftime('%Y-%m-%d'),
            "name": row['name'],
            "tss": round(row['tss'], 1),
            "tss_source": row.get('tss_source', 'unknown'),
        }
        
        # Enriquecimiento subjetivo: Público + Privado + RPE
        notas = []
        if row.get('description'):
            notas.append(f"[Público] {str(row['description'])[:150]}")
        if row.get('private_note'):
            notas.append(f"[Privado] {str(row['private_note'])[:150]}")
        
        workout["sensations"] = " | ".join(notas) if notas else "Sin comentarios vinculados."
        
        if row.get('perceived_exertion') is not None:
            workout["perceived_exertion_rpe"] = row['perceived_exertion']
        if row.get('suffer_score') is not None:
            workout["suffer_score"] = row['suffer_score']
        
        last_7_days_list.append(workout)

    logger.info("Contexto LLM construido satisfactoriamente con %d sesiones recientes.", len(last_7_days_list))

    return {
        "athlete": athlete.to_dict(),
        "pmc_snapshot": pmc_report,
        "trends": {
            "last_8_weeks_tss": weekly_tss,
            "weekly_avg_tss": round(sum(weekly_tss)/len(weekly_tss), 1) if weekly_tss else 0
        },
        "last_7_days_workouts": last_7_days_list
    }

def main():
    """Genera e imprime el reporte estructurado de estado actual."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    context = get_llm_context()
    
    logger.info("ESTADO VIRTUAL COACH (Context Snapshot)")
    logger.info("-" * 40)
    logger.info("Fitness (CTL): %s | Fatiga (ATL): %s | Forma (TSB): %s", 
                context.get('pmc_snapshot', {}).get('ctl', 'N/A'),
                context.get('pmc_snapshot', {}).get('atl', 'N/A'),
                context.get('pmc_snapshot', {}).get('tsb', 'N/A'))
    
    logger.info("Contexto JSON generado (Compacto):")
    logger.info(json.dumps(context, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
