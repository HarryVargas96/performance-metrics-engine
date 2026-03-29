# src/core/pmc.py
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class PMCProcessor:
    """Calculadora de CTL, ATL y TSB histórico."""

    def __init__(self, ctl_days=42, atl_days=7):
        self.ctl_days = ctl_days
        self.atl_days = atl_days

    def calculate_pmc(self, df_tss: pd.DataFrame) -> pd.DataFrame:
        if df_tss.empty: return pd.DataFrame()
        
        # Copia para no modificar el original y asegurar formato de fecha
        df = df_tss.copy()
        df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None) # Normalizar a naive
        
        df = df.set_index('date').sort_index().resample('D').sum().fillna(0)
        
        alpha_ctl = 1.0 / self.ctl_days
        alpha_atl = 1.0 / self.atl_days
        
        ctl_prev, atl_prev = 0.0, 0.0
        ctls, atls = [], []
        
        for tss in df['tss']:
            ctl_today = ctl_prev + (tss - ctl_prev) * alpha_ctl
            atl_today = atl_prev + (tss - atl_prev) * alpha_atl
            ctls.append(ctl_today); atls.append(atl_today)
            ctl_prev, atl_prev = ctl_today, atl_today
            
        df['ctl'], df['atl'] = ctls, atls
        df['tsb'] = df['ctl'].shift(1, fill_value=0) - df['atl'].shift(1, fill_value=0)
        return df.reset_index()

    def get_summary(self, df_pmc: pd.DataFrame) -> dict:
        if df_pmc.empty: return {}
        last = df_pmc.iloc[-1]
        return {'date': last['date'].strftime('%Y-%m-%d'), 'ctl': round(float(last['ctl']), 1),
                'atl': round(float(last['atl']), 1), 'tsb': round(float(last['tsb']), 1),
                'tss_today': round(float(last['tss']), 1)}
