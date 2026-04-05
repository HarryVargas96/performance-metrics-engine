# src/services/sync.py
import os
import argparse
import pandas as pd
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Añadir el raíz del proyecto al path para que "from src..." funcione como script crudo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.api.strava import StravaClient
from src.core.athlete import AthleteProfile
from src.core.analytics import ActivityMetricsCalculator
from src.core.pmc import PMCProcessor

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
TSS_CACHE_FILE = DATA_DIR / "tss_history.parquet" # CAMBIO: PARQUET

def run_historical_sync(days=90, force_resync=False):
    """
    Sincroniza historial usando PARQUET persistente.
    - days: ventana de días hacia atrás (usa 20 para pruebas rápidas).
    - force_resync: re-procesa actividades ya existentes si tienen campos subjetivos vacíos.
    """
    DATA_DIR.mkdir(exist_ok=True)
    
    client = StravaClient()
    athlete = AthleteProfile()
    calc = ActivityMetricsCalculator(athlete)
    
    # 1. Cargar caché Parquet
    if TSS_CACHE_FILE.exists():
        df_cache = pd.read_parquet(TSS_CACHE_FILE)
        if 'date' in df_cache.columns:
            df_cache['date'] = pd.to_datetime(df_cache['date'])
        
        # Detectar IDs sin campos subjetivos (schema migration)
        nuevos_campos = ['private_note', 'perceived_exertion', 'suffer_score']
        if force_resync or not all(c in df_cache.columns for c in nuevos_campos):
            logger.info("Re-sync forzado: se reprocesarán actividades sin datos subjetivos...")
            existentes_ids = set()  # Re-process all
        else:
            # Excluir del caché los IDs donde los campos subjetivos son todos NaN
            mask_sin_datos = (
                df_cache.get('private_note', pd.Series([None]*len(df_cache))).isna() &
                df_cache.get('perceived_exertion', pd.Series([None]*len(df_cache))).isna()
            )
            ids_sin_datos = set(df_cache[mask_sin_datos]['id'].tolist())
            existentes_ids = set(df_cache['id'].tolist()) - ids_sin_datos
            if ids_sin_datos:
                logger.info("%d actividades sin datos subjetivos serán re-procesadas.", len(ids_sin_datos))
    else:
        df_cache = pd.DataFrame(columns=[
            'id', 'date', 'name', 'description', 'private_note',
            'perceived_exertion', 'suffer_score',
            'tss', 'tss_source', 'hr_tss', 'pwr_tss'
        ])
        existentes_ids = set()

    actividades_meta = client.get_recent_activities(days=days, per_page=200, return_dataframe=True)
    if actividades_meta.empty: return df_cache

    nuevas_filas = []
    for _, act in actividades_meta.iterrows():
        act_id = act['id']
        if act_id in existentes_ids: continue
            
        logger.info("🚀 Procesando: %s...", act['name'])
        try:
            # Traer detalles completos: descripción, notas privadas y sensaciones subjetivas
            detalle_act = client.get_activity(act_id)
            comentarios_publicos = detalle_act.get('description', '') or ''
            notas_privadas = detalle_act.get('private_note', '') or ''
            esfuerzo_percibido = detalle_act.get('perceived_exertion')  # RPE 1-10
            suffer_score = detalle_act.get('suffer_score')              # Puntuación Strava
            
            df_stream = client.get_activity_streams(act_id, start_date=act['start_date_local'])
            if df_stream is not None and not df_stream.empty:
                summary = calc.process_full_activity_summary(df_stream)
                
                nuevas_filas.append({
                    'id': act_id,
                    'date': pd.to_datetime(act['start_date_local']),
                    'name': act['name'],
                    'description': comentarios_publicos,
                    'private_note': notas_privadas,
                    'perceived_exertion': esfuerzo_percibido,
                    'suffer_score': suffer_score,
                    'tss': summary['training_stress_score'],
                    'tss_source': summary['tss_source'],
                    'hr_tss': summary['hr_tss'],
                    'pwr_tss': summary['pwr_tss']
                })
        except Exception as e:
            logger.error("Error en %s: %s", act_id, e)

    if nuevas_filas:
        df_nuevas = pd.DataFrame(nuevas_filas)
        # IMPORTANTE: nuevas primero → drop_duplicates(keep='first') preserva los datos frescos
        df_final = pd.concat([df_nuevas, df_cache]).drop_duplicates(subset=['id'], keep='first').reset_index(drop=True)
        df_final.to_parquet(TSS_CACHE_FILE, index=False)
        logger.info("✅ Sincronización exitosa en data/tss_history.parquet (%d actividades)", len(df_final))
    else:
        df_final = df_cache
        logger.info("ℹ️  Sin actividades nuevas. Caché actualizado.")

    return df_final

def generate_pmc_report(df_tss):
    if df_tss.empty: return {}
    pmc = PMCProcessor()
    df_pmc = pmc.calculate_pmc(df_tss[['date', 'tss']])
    return pmc.get_summary(df_pmc)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    parser = argparse.ArgumentParser(description="Sincroniza actividades de Strava y actualiza el historial PMC.")
    parser.add_argument(
        "--days", type=int, default=90,
        help="Número de días hacia atrás a sincronizar (default: 90). Usa 20 para pruebas rápidas."
    )
    parser.add_argument(
        "--force-resync", action="store_true",
        help="Re-procesa todas las actividades ignorando el caché de IDs ya existentes."
    )
    args = parser.parse_args()

    print(f"=== INICIANDO SINCRONIZACIÓN (ventana: {args.days} días) ===")
    df = run_historical_sync(days=args.days, force_resync=args.force_resync)
    
    if not df.empty:
        reporte = generate_pmc_report(df)
        print("\n📈 ESTADO ACTUAL DEL ATLETA (PMC):")
        print(f"   CTL (Fitness): {reporte['ctl']}")
        print(f"   ATL (Fatigue): {reporte['atl']}")
        print(f"   TSB (Form):    {reporte['tsb']}")
        
        # Análisis de impacto de la última semana
        df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
        semana_atras = datetime.now() - timedelta(days=7)
        ultimos_7_dias = df[df['date'] >= semana_atras]
        tss_semanal = ultimos_7_dias['tss'].sum()
        print(f"   Carga Semanal (TSS): {round(tss_semanal, 1)}")
        
        if tss_semanal > (reporte['ctl'] * 7 * 1.2):
            print("   🚀 IMPACTO: Semana de carga alta. Tu fatiga (ATL) está subiendo rápido.")
        elif tss_semanal < (reporte['ctl'] * 7 * 0.7):
            print("   💤 IMPACTO: Semana de descarga o inactividad. Tu Fitness (CTL) podría estancarse.")
        else:
            print("   ✅ IMPACTO: Carga estable. Manteniendo el Fitness.")
    else:
        print("No hay datos suficientes para generar el reporte PMC.")

