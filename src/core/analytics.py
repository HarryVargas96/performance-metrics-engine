# src/core/analytics.py
import pandas as pd
import numpy as np
import logging
from src.core.athlete import AthleteProfile

logger = logging.getLogger(__name__)

class ActivityMetricsCalculator:
    """Motor analítico central para cálculos deportivos."""
    
    def __init__(self, athlete_config: AthleteProfile):
        if not athlete_config:
            raise ValueError("El Perfil del Atleta no puede ser vacío.")
        self.athlete = athlete_config
        logger.info("Motor de métricas inicializado con FTP de %s W.", self.athlete.ftp)

    def calculate_normalized_power(self, df_streams: pd.DataFrame) -> float:
        if 'watts' not in df_streams.columns:
            return 0.0
        power_series = df_streams['watts'].fillna(0).astype(float)
        rolling_30s = power_series.rolling(window=30, min_periods=1).mean()
        potencias_pow_4_mean = (rolling_30s ** 4).mean()
        np_calculado = potencias_pow_4_mean ** 0.25
        return round(float(np_calculado), 2)
        
    def calculate_tss_if(self, np_value: float, duration_seconds: int) -> dict:
        if np_value <= 0 or duration_seconds <= 0:
            return {'IF': 0.0, 'TSS': 0.0}
        intensity_factor = np_value / self.athlete.ftp
        tss_calculado = (duration_seconds * np_value * intensity_factor) / (self.athlete.ftp * 3600) * 100
        return {'IF': round(intensity_factor, 3), 'TSS': round(tss_calculado, 1)}

    def calculate_hr_tss(self, df_streams: pd.DataFrame) -> float:
        tiz_hr = self.calculate_time_in_zones(df_streams, 'hr')
        if not tiz_hr: return 0.0
        pesos = {
            'Z1_Recovery': 0.3, 'Z2_Aerobic': 0.5, 'Z3_Tempo': 0.7, 
            'Z4_SubThr': 0.85, 'Z5a_SuperThr': 1.0, 'Z5b_Anaerobic': 1.2, 'Z5c_AllOut': 1.5
        }
        hr_tss_acumulado = sum((tiz_hr.get(z, {}).get('minutes', 0)/60)*p*100 for z, p in pesos.items())
        return round(hr_tss_acumulado, 1)

    def calculate_efficiency_factor(self, np_value: float, hr_average: float) -> float:
        return round(np_value / hr_average, 3) if (hr_average and hr_average > 0) else 0.0
        
    def calculate_variability_index(self, np_value: float, avg_power: float) -> float:
        return round(np_value / avg_power, 3) if avg_power > 0 else 0.0

    def calculate_time_in_zones(self, df_streams: pd.DataFrame, source: str = 'power') -> dict:
        if source == 'power' and 'watts' in df_streams.columns:
            datos_analizar = df_streams['watts'].fillna(0)
            zonas = self.athlete.get_coggan_power_zones()
        elif source == 'hr' and ('heartrate' in df_streams.columns):
            datos_analizar = df_streams['heartrate'].fillna(0)
            zonas = self.athlete.get_friel_hr_zones()
            if not zonas: return {}
        else: return {}
            
        tiempo_en_zonas = {}
        for nombre, limites in zonas.items():
            bucket = ((datos_analizar >= limites[0]) & (datos_analizar <= limites[1]))
            segundos_en_zona = int(bucket.sum())
            tiempo_en_zonas[nombre] = {'seconds': segundos_en_zona, 'minutes': round(segundos_en_zona/60, 2)}
        return tiempo_en_zonas

    def process_full_activity_summary(self, df_streams: pd.DataFrame) -> dict:
        if df_streams.empty: return {}
        duration_seconds = len(df_streams)
        avg_power = float(df_streams['watts'].mean()) if 'watts' in df_streams.columns else 0.0
        avg_hr = float(df_streams['heartrate'].mean()) if 'heartrate' in df_streams.columns else 0.0
        np_val = self.calculate_normalized_power(df_streams)
        tss_if_val = self.calculate_tss_if(np_val, duration_seconds)
        hr_tss_val = self.calculate_hr_tss(df_streams)
        tss_final = tss_if_val['TSS'] if tss_if_val['TSS'] > 0 else hr_tss_val
        
        return {
            'activity_duration_minutes': round(duration_seconds / 60, 2),
            'average_power': round(avg_power, 2),
            'normalized_power': np_val,
            'variability_index': self.calculate_variability_index(np_val, avg_power),
            'intensity_factor': tss_if_val['IF'],
            'training_stress_score': tss_final,
            'tss_source': 'power' if tss_if_val['TSS'] > 0 else 'hr',
            'hr_tss': hr_tss_val,
            'pwr_tss': tss_if_val['TSS'],
            'efficiency_factor': self.calculate_efficiency_factor(np_val, avg_hr),
            'time_in_zones_power': self.calculate_time_in_zones(df_streams, 'power'),
            'time_in_zones_hr': self.calculate_time_in_zones(df_streams, 'hr')
        }
