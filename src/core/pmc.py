"""Cálculos fisiológicos del Performance Management Chart (PMC).

Este módulo implementa el motor PMC que calcula Fitness (CTL), Fatiga (ATL)
y Forma (TSB) a partir de series temporales de TSS diaria.
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Logging a nivel de módulo
logger = logging.getLogger(__name__)

class PMCProcessor:
    """Calculadora de CTL, ATL y TSB basada en promedios exponenciales móviles.

    Attributes:
        ctl_days (int): Ventana de días para CTL (Fitness), típicamente 42.
        atl_days (int): Ventana de días para ATL (Fatiga), típicamente 7.
    """

    def __init__(self, ctl_days=42, atl_days=7):
        """Inicializa el PMCProcessor con constantes de tiempo específicas."""
        self.ctl_days = ctl_days
        self.atl_days = atl_days

    def calculate_pmc(self, df_tss: pd.DataFrame) -> pd.DataFrame:
        """Calcula el PMC completo basándose en una serie temporal de TSS.

        Gestiona la normalización de fechas y el relleno de días sin actividad
        con TSS 0 para asegurar la continuidad del decaimiento físico.

        Args:
            df_tss (pd.DataFrame): DataFrame con columnas ['date', 'tss'].

        Returns:
            pd.DataFrame: DataFrame con CTL, ATL, TSB y serie temporal completa.
        """
        if df_tss.empty:
            logger.warning("No hay datos de TSS para procesar el PMC.")
            return pd.DataFrame()
        
        # Preparación de datos
        df = df_tss.copy()
        # Normalizamos a medianoche sin zona horaria para coincidencia de índice
        df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None).dt.normalize()
        
        # Agregación diaria por si hay múltiples sesiones en un día
        df = df.groupby('date')[['tss']].sum()
        
        # Re-indexación para cubrir todos los días hasta HOY (decaimiento)
        idx = pd.date_range(df.index.min(), datetime.now().date(), freq='D')
        df = df.reindex(idx, fill_value=0)
        df.index.name = 'date'
        
        # Alphas de promedios exponenciales (EMA)
        alpha_ctl = 1.0 / self.ctl_days
        alpha_atl = 1.0 / self.atl_days
        
        ctl_prev, atl_prev = 0.0, 0.0
        ctls, atls = [], []
        
        # Iteración secuencial del modelo fisiológico
        for tss in df['tss']:
            ctl_today = ctl_prev + (tss - ctl_prev) * alpha_ctl
            atl_today = atl_prev + (tss - atl_prev) * alpha_atl
            ctls.append(ctl_today)
            atls.append(atl_today)
            ctl_prev, atl_prev = ctl_today, atl_today
            
        df['ctl'], df['atl'] = ctls, atls
        # TSB = CTL de ayer - ATL de ayer (Balance del estado actual)
        df['tsb'] = df['ctl'].shift(1, fill_value=0) - df['atl'].shift(1, fill_value=0)
        
        logger.info("PMC procesado satisfactoriamente para %s días.", len(df))
        return df.reset_index()

    def get_summary(self, df_pmc: pd.DataFrame) -> dict:
        """Extrae el estado más reciente del atleta a partir del PMC generado.

        Args:
            df_pmc (pd.DataFrame): Resultado de calculate_pmc.

        Returns:
            dict: Snapshot con CTL, ATL, TSB y fecha última.
        """
        if df_pmc.empty:
            return {}
        last = df_pmc.iloc[-1]
        return {
            'date': last['date'].strftime('%Y-%m-%d'), 
            'ctl': round(float(last['ctl']), 1),
            'atl': round(float(last['atl']), 1), 
            'tsb': round(float(last['tsb']), 1),
            'tss_today': round(float(last['tss']), 1)
        }
