"""Motor de cálculo de métricas de potencia y frecuencia cardíaca.

Implementa algoritmos específicos de rendimiento ciclista y aeróbico como
NP (Potencia Normalizada), IF (Factor de Intensidad), y TSS (Training Stress Score).
"""

import pandas as pd
import numpy as np
import logging
from src.core.athlete import AthleteProfile

# Configuración de registro local del módulo
logger = logging.getLogger(__name__)

class ActivityMetricsCalculator:
    """Motor analítico central de procesamiento de telemetría de sesiones.

    Responsibilities:
        - Cálculo de Potencia Normalizada (NP)
        - Estimación de Carga de Entrenamiento (TSS e hrTSS)
        - Análisis de distribución de tiempo en zonas de intensidad.

    Attributes:
        athlete (AthleteProfile): Configuración fisiológica del atleta.
    """
    
    def __init__(self, athlete_config: AthleteProfile):
        """Inicializa el calculador vinculado a un perfil de atleta.

        Args:
            athlete_config (AthleteProfile): Atleta contra el que se medirán umbrales.
        """
        if not athlete_config:
            logger.error("Se intentó inicializar ActivityMetricsCalculator sin perfil de atleta.")
            raise ValueError("El Perfil del Atleta no puede ser vacío.")
        self.athlete = athlete_config
        logger.info("Motor analítico vinculado a atleta con FTP: %s W.", self.athlete.ftp)

    def calculate_normalized_power(self, df_streams: pd.DataFrame) -> float:
        """Calcula la Potencia Normalizada (NP) de la sesión.

        NP usa una media móvil de 30s elevada a la cuarta potencia para penalizar
        los picos de esfuerzo y simular la respuesta fisiológica real.

        Args:
            df_streams (pd.DataFrame): Telemetría con columna 'watts'.

        Returns:
            float: Potencia Normalizada en vatios.
        """
        if 'watts' not in df_streams.columns:
            logger.debug("La telemetría no contiene potencia; NP será 0.0.")
            return 0.0
        
        # Suavizado exponencial fisiológico (Rolling 30s)
        power_series = df_streams['watts'].fillna(0).astype(float)
        rolling_30s = power_series.rolling(window=30, min_periods=1).mean()
        
        # El algoritmo de Dr. Coggan eleva a la cuarta potencia la media móvil
        potencias_pow_4_mean = (rolling_30s ** 4).mean()
        np_calculado = potencias_pow_4_mean ** 0.25
        
        return round(float(np_calculado), 2)
        
    def calculate_tss_if(self, np_value: float, duration_seconds: int) -> dict:
        """Calcula el estrés (TSS) y factor de intensidad (IF) basado en potencia.

        Args:
            np_value (float): Potencia Normalizada calculada.
            duration_seconds (int): Segundos activos de la sesión.

        Returns:
            dict: Diccionario con 'IF' y 'TSS'.
        """
        if np_value <= 0 or duration_seconds <= 0:
            return {'IF': 0.0, 'TSS': 0.0}
            
        intensity_factor = np_value / self.athlete.ftp
        # Fórmula Coggan: (s * NP * IF) / (FTP * 3600) * 100
        tss_calculado = (duration_seconds * np_value * intensity_factor) / (self.athlete.ftp * 3600) * 100
        
        return {'IF': round(intensity_factor, 3), 'TSS': round(tss_calculado, 1)}

    def calculate_hr_tss(self, df_streams: pd.DataFrame) -> float:
        """Estima la carga de entrenamiento basada en frecuencia cardíaca (hrTSS).

        Modelo fallback para cuando los datos de potencia no están disponibles.
        Usa pesos multiplicadores por zona de frecuencia cardíaca Friel.

        Args:
            df_streams (pd.DataFrame): Telemetría con columna 'heartrate'.

        Returns:
            float: hrTSS estimado.
        """
        tiz_hr = self.calculate_time_in_zones(df_streams, 'hr')
        if not tiz_hr: 
            return 0.0
            
        # Pesos exponenciales de carga aeróbica / anaeróbica por zona
        pesos = {
            'Z1_Recovery': 0.3, 'Z2_Aerobic': 0.5, 'Z3_Tempo': 0.7, 
            'Z4_SubThr': 0.85, 'Z5a_SuperThr': 1.0, 'Z5b_Anaerobic': 1.2, 'Z5c_AllOut': 1.5
        }
        hr_tss_acumulado = sum((tiz_hr.get(z, {}).get('minutes', 0)/60)*p*100 for z, p in pesos.items())
        
        return round(hr_tss_acumulado, 1)

    def calculate_efficiency_factor(self, np_value: float, hr_average: float) -> float:
        """Calcula el EF (Normalized Power / Factor de Pulso medio).

        Mide la eficiencia aeróbica: vatios producidos por cada latido cardíaco.

        Args:
            np_value (float): Potencia Normalizada.
            hr_average (float): Media de frecuencia cardíaca.

        Returns:
            float: Ratio EF.
        """
        return round(np_value / hr_average, 3) if (hr_average and hr_average > 0) else 0.0
        
    def calculate_variability_index(self, np_value: float, avg_power: float) -> float:
        """Calcula el VI (Índice de Variabilidad) de la sesión.

        Indica qué tan "constante" fue el esfuerzo. Un VI de 1.0 es esfuerzo de rodillo.

        Args:
            np_value (float): Potencia Normalizada.
            avg_power (float): Potencia Media Simple.

        Returns:
            float: Ratio VI.
        """
        return round(np_value / avg_power, 3) if avg_power > 0 else 0.0

    def calculate_time_in_zones(self, df_streams: pd.DataFrame, source: str = 'power') -> dict:
        """Tabula el tiempo de permanencia en cada zona fisiológica.

        Args:
            df_streams (pd.DataFrame): Datos de sesión.
            source (str): 'power' para zonas de potencia o 'hr' para cardíacas.

        Returns:
            dict: Resultados agrupados por zona en segundos y minutos.
        """
        if source == 'power' and 'watts' in df_streams.columns:
            datos_analizar = df_streams['watts'].fillna(0)
            zonas = self.athlete.get_coggan_power_zones()
        elif source == 'hr' and ('heartrate' in df_streams.columns):
            datos_analizar = df_streams['heartrate'].fillna(0)
            zonas = self.athlete.get_friel_hr_zones()
            if not zonas: 
                return {}
        else: 
            return {}
            
        tiempo_en_zonas = {}
        for nombre, limites in zonas.items():
            bucket = ((datos_analizar >= limites[0]) & (datos_analizar <= limites[1]))
            segundos_en_zona = int(bucket.sum())
            tiempo_en_zonas[nombre] = {'seconds': segundos_en_zona, 'minutes': round(segundos_en_zona/60, 2)}
            
        return tiempo_en_zonas

    def process_full_activity_summary(self, df_streams: pd.DataFrame) -> dict:
        """Genera un reporte analítico completo a partir de los streams de telemetría.

        Punto de entrada maestro que coordina los cálculos de estrés, potencia,
        eficiencia y distribución de zonas.

        Args:
            df_streams (pd.DataFrame): Serie temporal completa de la actividad.

        Returns:
            dict: Metodología analítica completa de la sesión.
        """
        if df_streams.empty: 
            logger.warning("Solicitado resumen de actividad para DataFrame vacío.")
            return {}
            
        duration_seconds = len(df_streams)
        avg_power = float(df_streams['watts'].mean()) if 'watts' in df_streams.columns else 0.0
        avg_hr = float(df_streams['heartrate'].mean()) if 'heartrate' in df_streams.columns else 0.0
        
        np_val = self.calculate_normalized_power(df_streams)
        tss_if_val = self.calculate_tss_if(np_val, duration_seconds)
        hr_tss_val = self.calculate_hr_tss(df_streams)
        
        # Selección de la fuente de estrés más precisa (Power > HR)
        tss_final = tss_if_val['TSS'] if tss_if_val['TSS'] > 0 else hr_tss_val
        
        logger.info("Procesamiento completo de actividad finalizado (TSS Final: %s).", tss_final)
        
        avg_cadence = float(df_streams['cadence'].mean()) if 'cadence' in df_streams.columns else 0.0
        
        return {
            'activity_duration_minutes': round(duration_seconds / 60, 2),
            'average_power': round(avg_power, 2),
            'average_cadence': round(avg_cadence, 1),
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
