import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Añadir el raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.pmc import PMCProcessor
from src.services.sync import generate_pmc_report

TSS_CACHE_FILE = Path("data/tss_history.parquet")

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
    
    print("==========================================")

if __name__ == "__main__":
    show_current_status()
