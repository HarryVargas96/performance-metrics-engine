"""Servicio de orquestación para sincronización de datos con Strava.

Este módulo coordina la descarga de actividades, el procesamiento analítico 
de telemetría y la persistencia en caché local (Parquet). También genera 
el reporte fisiológico PMC.
"""

import os
import argparse
import pandas as pd
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Asegurar que el raíz del proyecto esté en el path para ejecución directa
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.api.strava import StravaClient
from src.core.athlete import AthleteProfile
from src.core.analytics import ActivityMetricsCalculator
from src.core.pmc import PMCProcessor

# Configuración de registro centralizado
logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
TSS_CACHE_FILE = DATA_DIR / "tss_history.parquet"

def run_historical_sync(days=90, force_resync=False):
    """Ejecuta el proceso completo de sincronización de historial con Strava.

    Descarga telemetría pesada (streams), calcula TSS/NP y persiste los datos
    subjetivos (RPE, notas privadas) en un archivo Parquet eficiente.

    Args:
        days (int): Ventana de tiempo hacia atrás a sincronizar.
        force_resync (bool): Si es True, ignora el caché y reprocesa todo.

    Returns:
        pd.DataFrame: Historial completo y enriquecido de actividades.
    """
    DATA_DIR.mkdir(exist_ok=True)
    
    try:
        client = StravaClient()
        athlete = AthleteProfile()
        calc = ActivityMetricsCalculator(athlete)
    except Exception as e:
        logger.error("No se pudo inicializar los clientes necesarios para sync: %s", e)
        return pd.DataFrame()
    
    # Carga de la base de datos local
    if TSS_CACHE_FILE.exists():
        df_cache = pd.read_parquet(TSS_CACHE_FILE)
        if 'date' in df_cache.columns:
            df_cache['date'] = pd.to_datetime(df_cache['date'])
        
        nuevos_campos = ['private_note', 'perceived_exertion', 'suffer_score']
        if force_resync or not all(c in df_cache.columns for c in nuevos_campos):
            logger.info("Migración de datos necesaria o re-sync forzado detectado.")
            existentes_ids = set()
        else:
            # Re-sincronizar solo las actividades que no tienen datos subjetivos (Subjective Gap)
            mask_sin_datos = (
                df_cache.get('private_note', pd.Series([None]*len(df_cache))).isna() &
                df_cache.get('perceived_exertion', pd.Series([None]*len(df_cache))).isna()
            )
            ids_sin_datos = set(df_cache[mask_sin_datos]['id'].tolist())
            existentes_ids = set(df_cache['id'].tolist()) - ids_sin_datos
            if ids_sin_datos:
                logger.info("%d sesiones requieren re-sincronización de campos subjetivos...", len(ids_sin_datos))
    else:
        df_cache = pd.DataFrame(columns=[
            'id', 'date', 'name', 'description', 'private_note',
            'perceived_exertion', 'suffer_score',
            'tss', 'tss_source', 'hr_tss', 'pwr_tss'
        ])
        existentes_ids = set()

    # Recuperación de metadatos de Strava
    actividades_meta = client.get_recent_activities(days=days, per_page=200, return_dataframe=True)
    if actividades_meta.empty: 
        logger.info("No se encontraron actividades nuevas en Strava.")
        return df_cache

    nuevas_filas = []
    for _, act in actividades_meta.iterrows():
        act_id = act['id']
        if act_id in existentes_ids:
            continue
            
        logger.info("⚡ Sincronizando: %s (%s)...", act['name'], act['start_date_local'])
        try:
            # Recuperar detalle (notas privadas) y streams (telemetría)
            detalle_act = client.get_activity(act_id)
            df_stream = client.get_activity_streams(act_id, start_date=act['start_date_local'])
            
            if df_stream is not None and not df_stream.empty:
                summary = calc.process_full_activity_summary(df_stream)
                
                nuevas_filas.append({
                    'id': act_id,
                    'date': pd.to_datetime(act['start_date_local']),
                    'name': act['name'],
                    'description': detalle_act.get('description', '') or '',
                    'private_note': detalle_act.get('private_note', '') or '',
                    'perceived_exertion': detalle_act.get('perceived_exertion'),
                    'suffer_score': detalle_act.get('suffer_score'),
                    'tss': summary['training_stress_score'],
                    'tss_source': summary['tss_source'],
                    'hr_tss': summary['hr_tss'],
                    'pwr_tss': summary['pwr_tss']
                })
        except Exception as e:
            logger.error("Fallo inesperado al procesar actividad ID %s: %s", act_id, e)

    if nuevas_filas:
        df_nuevas = pd.DataFrame(nuevas_filas)
        # Concatenar prefiriendo datos nuevos en caso de IDs duplicadas (keep='first')
        df_final = pd.concat([df_nuevas, df_cache]).drop_duplicates(subset=['id'], keep='first').reset_index(drop=True)
        df_final.to_parquet(TSS_CACHE_FILE, index=False)
        logger.info("Sincronización finalizada satisfactoriamente. Total: %d registros.", len(df_final))
    else:
        df_final = df_cache
        logger.info("Caché local está actualizado. No se detectaron cambios requeridos.")

    return df_final

def generate_pmc_report(df_tss: pd.DataFrame) -> dict:
    """Calcula el estado metabólico actual (PMC) del atleta a partir del historial.

    Args:
        df_tss (pd.DataFrame): DataFrame con historial de TSS.

    Returns:
        dict: Snapshot resumido de CTL, ATL y TSB.
    """
    if df_tss.empty:
        return {}
    pmc = PMCProcessor()
    df_pmc = pmc.calculate_pmc(df_tss[['date', 'tss']])
    return pmc.get_summary(df_pmc)

def main():
    """Entrada principal del ejecutable de sincronización CLI."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(description="Performance Metrics Engine - Sync Tool")
    parser.add_argument("--days", type=int, default=90, help="Ventana de días hacia atrás.")
    parser.add_argument("--force-resync", action="store_true", help="Reprocesar todo ignorando caché.")
    args = parser.parse_args()

    logger.info("--- INICIANDO MOTOR DE SINCRONIZACIÓN ---")
    df = run_historical_sync(days=args.days, force_resync=args.force_resync)
    
    if not df.empty:
        reporte = generate_pmc_report(df)
        logger.info("ESTADO ACTUAL PMC:")
        logger.info(f"   CTL (Fitness): {reporte['ctl']}")
        logger.info(f"   ATL (Fatiga): {reporte['atl']}")
        logger.info(f"   TSB (Form):    {reporte['tsb']}")
        
        # Última semana
        df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
        ultimos_7 = df[df['date'] >= (datetime.now() - timedelta(days=7))]
        tss_semana = round(ultimos_7['tss'].sum(), 1)
        logger.info(f"   Carga Semanal (TSS): {tss_semana}")
    else:
        logger.warning("No hay suficientes datos procesados para generar el reporte.")

if __name__ == "__main__":
    main()
