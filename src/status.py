import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Añadir el raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from src.core.athlete import AthleteProfile
from src.core.pmc import PMCProcessor
from src.services.sync import generate_pmc_report

TSS_CACHE_FILE = Path("data/tss_history.parquet")

def get_llm_context(df_history, athlete, pmc_report):
    """
    Genera un diccionario estructurado con tendencias y detalles
    específicamente diseñado para enviárselo a un LLM (Gemini).
    """
    # 1. Tendencia de carga (Últimas 8 semanas)
    # Normalizamos fechas para que el match sea exacto al día
    df_copy = df_history.copy()
    df_copy['date'] = pd.to_datetime(df_copy['date']).dt.normalize()
    df_daily = df_copy.groupby('date')['tss'].sum()
    
    # Aseguramos un rango de exactamente 8 semanas terminando ayer o hoy
    hoy = pd.Timestamp.now().normalize()
    inicio_8w = hoy - timedelta(days=55) # 56 días incluyendo hoy
    idx_8w = pd.date_range(inicio_8w, hoy, freq='D')
    
    df_resampled = df_daily.reindex(idx_8w, fill_value=0)
    
    # Agrupamos por bloques de 7 días exactos para evitar problemas de "Sun/Mon"
    # Tomamos los últimos 56 días y los dividimos en 8 bloques de 7
    weekly_tss = [round(df_resampled.iloc[i : i+7].sum(), 1) for i in range(0, 56, 7)]
    
    # 2. Detalle diario (Últimos 7 días)
    semana_atras = hoy - pd.Timedelta(days=7)
    df_recent = df_history[pd.to_datetime(df_history['date']).dt.normalize() >= semana_atras].sort_values('date')
    
    last_7_days_list = []
    for _, row in df_recent.iterrows():
        workout = {
            "date": row['date'].strftime('%Y-%m-%d'),
            "name": row['name'],
            "tss": round(row['tss'], 1),
            "tss_source": row.get('tss_source', 'unknown'),
        }
        # Combinar descripción pública y notas privadas en un solo campo de contexto
        notas = []
        if row.get('description'):
            notas.append(f"[Público] {str(row['description'])[:150]}")
        if row.get('private_note'):
            notas.append(f"[Privado] {str(row['private_note'])[:150]}")
        workout["sensations"] = " | ".join(notas) if notas else ""
        
        # Esfuerzo percibido (RPE 1-10) y puntuación de sufrimiento de Strava
        if row.get('perceived_exertion') is not None:
            workout["perceived_exertion_rpe"] = row['perceived_exertion']
        if row.get('suffer_score') is not None:
            workout["suffer_score"] = row['suffer_score']
        
        last_7_days_list.append(workout)

    return {
        "athlete": athlete.to_dict(),
        "pmc_snapshot": pmc_report,
        "trends": {
            "last_8_weeks_tss": weekly_tss,
            "weekly_avg": round(sum(weekly_tss)/len(weekly_tss), 1) if weekly_tss else 0
        },
        "last_7_days_workouts": last_7_days_list
    }

def show_current_status():
    """
    Lee el histórico persistido y muestra el estado actual del atleta
    sin necesidad de conectarse a la API de Strava.
    """
    if not TSS_CACHE_FILE.exists():
        print("❌ No se encontró el histórico en data/tss_history.parquet. Por favor, corre el sync primero.")
        return

    df = pd.read_parquet(TSS_CACHE_FILE)
    if df.empty:
        print("El archivo histórico está vacío.")
        return

    # Convertir fecha a datetime y normalizar a naive (sin zona horaria)
    df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
    
    # Generar reporte PMC
    reporte = generate_pmc_report(df)
    
    print("==========================================")
    print("   ESTADO ACTUAL DEL ATLETA (VIRTUAL COACH)")
    print("==========================================")
    print(f"📅 Fecha de análisis: {reporte['date']}")
    print(f"🚀 CTL (Fitness):    {reporte['ctl']}")
    print(f"🔥 ATL (Fatiga):     {reporte['atl']}")
    print(f"🎯 TSB (Forma):      {reporte['tsb']}")
    print("------------------------------------------")
    
    # Análisis de la última semana
    semana_atras = datetime.now() - timedelta(days=7)
    df_semana = df[df['date'] >= semana_atras]
    tss_semanal = df_semana['tss'].sum()
    num_entrenamientos = len(df_semana)

    print(f"📊 Resumen de los últimos 7 días:")
    print(f"   - Entrenamientos: {num_entrenamientos}")
    print(f"   - Carga Total:    {round(tss_semanal, 1)} TSS")
    
    # Interpretación de la carga
    objetivo_semanal = reporte['ctl'] * 7
    ratio = tss_semanal / objetivo_semanal if objetivo_semanal > 0 else 1.0
    
    if ratio > 1.2:
        print("   ⚠️  ESTADO: Sobrecarga detectada. Estás entrenando un 20%+ por encima de tu media.")
    elif ratio < 0.7:
        print("   💤 ESTADO: Desentrenamiento. Tu carga semanal es baja respecto a tu Fitness.")
    else:
        print("   ✅ ESTADO: Carga equilibrada y productiva.")
    
    # Últimas sensaciones si hay metadata h
    ultimas_sensaciones = df.sort_values('date', ascending=False).iloc[0]['description']
    if ultimas_sensaciones:
        print(f"\n📝 Últimas sensaciones registradas:\n   \"{ultimas_sensaciones[:100]}...\"")
    
    # --- BLOQUE NUEVO: LLM CONTEXT ---
    athlete = AthleteProfile() # Carga desde config.py por defecto
    llm_json = get_llm_context(df, athlete, reporte)
    
    print("\n" + "="*42)
    print("   🤖 LLM CONTEXT (READY FOR GEMINI)")
    print("="*42)
    print(json.dumps(llm_json, indent=2, ensure_ascii=False))
    print("="*42)

if __name__ == "__main__":
    show_current_status()
