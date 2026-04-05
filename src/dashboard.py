"""Dashboard interactivo para visualización de métricas de rendimiento.

Este módulo implementa una interfaz web local usando Streamlit que permite 
visualizar el PMC (Performance Management Chart), la carga semanal de TSS 
y el desglose detallado de sesiones incluyendo métricas subjetivas de Strava.
"""

import os
import sys
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime, timedelta

# Añadir raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from src.core.pmc import PMCProcessor
from src.core.athlete import AthleteProfile
from src.services.sync import generate_pmc_report

# Configuración de UI
st.set_page_config(
    page_title="Performance Metrics Engine",
    page_icon="🚴‍♂️",
    layout="wide",
)

TSS_CACHE_FILE = Path("data/tss_history.parquet")

@st.cache_data(ttl=300)
def load_data():
    """Carga y procesa los datos del caché para su visualización.

    Returns:
        tuple: (DataFrame con actividades crudas, DataFrame con serie PMC).
    """
    if not TSS_CACHE_FILE.exists():
        return pd.DataFrame(), pd.DataFrame()
    
    df_raw = pd.read_parquet(TSS_CACHE_FILE)
    df_raw['date'] = pd.to_datetime(df_raw['date'], utc=True).dt.tz_localize(None)
    
    hoy = pd.Timestamp.now().normalize()
    # Ventana mínima de 90 días para el PMC
    inicio_90d = hoy - pd.Timedelta(days=90)
    
    df_input = df_raw[['date', 'tss']].copy()
    if df_input['date'].min() > inicio_90d:
        df_input = pd.concat([df_input, pd.DataFrame({'date': [inicio_90d], 'tss': [0.0]})])
    
    pmc_proc = PMCProcessor()
    df_pmc = pmc_proc.calculate_pmc(df_input)
    
    return df_raw, df_pmc

def render_kpi_metrics(reporte: dict, athlete: AthleteProfile, df_raw: pd.DataFrame):
    """Renderiza las tarjetas de métricas clave (Fitness, Fatiga, Forma)."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Delta basado en el TSB (Forma)
    col1.metric("🚀 CTL (Fitness)", reporte['ctl'], help="Media 42 días (Carga Crónica)")
    col2.metric("🔥 ATL (Fatiga)", reporte['atl'], help="Media 7 días (Carga Aguda)")
    
    tsb = reporte['tsb']
    tsb_delta = round(tsb, 1)
    col3.metric("🎯 TSB (Forma)", tsb, delta=tsb_delta, help="CTL - ATL")

    hoy = pd.Timestamp.now().normalize()
    semana_atras = hoy - pd.Timedelta(days=7)
    df_semana = df_raw[pd.to_datetime(df_raw['date']).dt.normalize() >= semana_atras]
    tss_semana = round(df_semana['tss'].sum(), 1)

    col4.metric("📊 TSS Semana", tss_semana)
    col5.metric("💪 Ratio W/kg", f"{athlete.power_to_weight()}")

def main():
    """Punto de entrada para la ejecución del dashboard de Streamlit."""
    st.title("🚴‍♂️ Performance Metrics Engine")
    st.caption("Visualización avanzada de rendimiento fisiológico · Sincronizado con Strava")

    df_raw, df_pmc = load_data()

    if df_raw.empty:
        st.error("❌ No hay datos locales. Ejecuta primero la sincronización: `make sync` o `poetry run python src/services/sync.py`.")
        st.stop()

    athlete = AthleteProfile()
    reporte = generate_pmc_report(df_raw)
    render_kpi_metrics(reporte, athlete, df_raw)

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📈 Gráfica PMC", "📅 Histórico Semanal", "🔍 Detalle Actividades"])

    # --- TAB 1: PMC ---
    with tab1:
        hoy = pd.Timestamp.now().normalize()
        df_plot = df_pmc[df_pmc['date'] >= (hoy - pd.Timedelta(days=90))]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['ctl'], name='Fitness (CTL)',
                                 line=dict(color='royalblue', width=3), fill='tozeroy',
                                 fillcolor='rgba(65,105,225,0.1)'))
        fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['atl'], name='Fatiga (ATL)',
                                 line=dict(color='orange', width=2, dash='dot')))
        fig.add_trace(go.Scatter(x=df_plot['date'], y=df_plot['tsb'], name='Forma (TSB)',
                                 line=dict(color='forestgreen', width=1.5), fill='tozeroy',
                                 fillcolor='rgba(34,139,34,0.07)'))
        fig.update_layout(
            title="Performance Management Chart (90 Días)",
            xaxis_title="Fecha", yaxis_title="Puntos de Estrés",
            template="plotly_dark", height=450
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 2: Semanal ---
    with tab2:
        df_weekly = df_pmc.set_index('date').resample('W').sum().tail(12)
        fig2 = px.bar(df_weekly, x=df_weekly.index, y='tss',
                      title='Carga Semanal Acumulada (TSS)',
                      labels={'tss': 'TSS Semanal', 'date': 'Semana'},
                      template='plotly_dark', color='tss', color_continuous_scale='Turbo')
        st.plotly_chart(fig2, use_container_width=True)

    # --- TAB 3: Detalle ---
    with tab3:
        st.subheader("Últimas Sesiones")
        df_ui = df_raw.sort_values('date', ascending=False).head(15).copy()
        df_ui['fecha'] = df_ui['date'].dt.strftime('%Y-%m-%d')
        
        st.dataframe(df_ui[['fecha', 'name', 'tss', 'tss_source', 'perceived_exertion']].rename(columns={
            'fecha': 'Fecha', 'name': 'Nombre', 'tss': 'TSS', 'tss_source': 'Fuente', 'perceived_exertion': 'RPE'
        }), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Notas y Sensaciones")
        selected_name = st.selectbox("Selecciona una sesión para ver detalles:", df_ui['name'].tolist())
        
        row = df_ui[df_ui['name'] == selected_name].iloc[0]
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"**Descripción Pública:**\n\n{row['description'] or 'Sin descripción.'}")
        with c2:
            st.warning(f"**Notas Privadas (Grit & Feel):**\n\n{row['private_note'] or 'Sin notas privadas.'}")

if __name__ == "__main__":
    main()
