# src/dashboard.py
"""
Dashboard local de métricas de rendimiento usando Streamlit.
Ejecutar con: poetry run streamlit run src/dashboard.py
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

# ---------------------------------------------------------------------------
# Config de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Performance Metrics Engine",
    page_icon="🚴‍♂️",
    layout="wide",
)

TSS_CACHE_FILE = Path("data/tss_history.parquet")

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300)
def load_data():
    if not TSS_CACHE_FILE.exists():
        return pd.DataFrame(), pd.DataFrame()
    
    df_raw = pd.read_parquet(TSS_CACHE_FILE)
    df_raw['date'] = pd.to_datetime(df_raw['date'], utc=True).dt.tz_localize(None)
    
    hoy = pd.Timestamp.now().normalize()
    inicio_90d = hoy - pd.Timedelta(days=90)
    
    df_input = df_raw[['date', 'tss']].copy()
    if df_input['date'].min() > inicio_90d:
        df_input = pd.concat([df_input, pd.DataFrame({'date': [inicio_90d], 'tss': [0.0]})])
    
    pmc_proc = PMCProcessor()
    df_pmc = pmc_proc.calculate_pmc(df_input)
    
    return df_raw, df_pmc

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🚴‍♂️ Performance Metrics Engine")
st.caption("Panel de control local · Datos desde Strava")

df_raw, df_pmc = load_data()

if df_raw.empty:
    st.error("❌ No se encontraron datos. Ejecuta primero: `poetry run python src/services/sync.py`")
    st.stop()

# ---------------------------------------------------------------------------
# KPIs – Métricas clave en tarjetas
# ---------------------------------------------------------------------------
athlete = AthleteProfile()
reporte = generate_pmc_report(df_raw)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("🚀 CTL (Fitness)", reporte['ctl'], help="Carga Crónica – Media 42 días")
col2.metric("🔥 ATL (Fatiga)", reporte['atl'], help="Carga Aguda – Media 7 días")
col3.metric("🎯 TSB (Forma)", reporte['tsb'], delta=round(reporte['tsb'] - reporte['atl'], 1),
            help="Forma = CTL - ATL")

hoy = pd.Timestamp.now().normalize()
semana_atras = hoy - pd.Timedelta(days=7)
df_semana = df_raw[pd.to_datetime(df_raw['date']).dt.normalize() >= semana_atras]
tss_semana = round(df_semana['tss'].sum(), 1)

col4.metric("📊 TSS Última Semana", tss_semana)
col5.metric("💪 FTP / W·kg", f"{athlete.ftp}W / {athlete.power_to_weight()}")

st.divider()

# ---------------------------------------------------------------------------
# Tabs principales
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📈 PMC (CTL / ATL / TSB)", "📅 Carga Semanal", "🔍 Actividades Recientes"])

# ---- Tab 1: PMC ----
with tab1:
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
        title="Performance Management Chart – Últimos 90 días",
        xaxis_title="Fecha", yaxis_title="Puntos TSS",
        template="plotly_dark", legend_orientation="h",
        height=420
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- Tab 2: Carga Semanal ----
with tab2:
    df_weekly = df_pmc.set_index('date').resample('W').sum().tail(12)
    fig2 = px.bar(df_weekly, x=df_weekly.index, y='tss',
                  title='Carga Acumulada Semanal (TSS) – Últimas 12 Semanas',
                  labels={'tss': 'Suma TSS', 'date': 'Semana'},
                  template='plotly_dark', color='tss', color_continuous_scale='Magma')
    fig2.update_layout(coloraxis_showscale=False, height=400)
    st.plotly_chart(fig2, use_container_width=True)

# ---- Tab 3: Actividades Recientes ----
with tab3:
    n_acts = st.slider("Número de actividades a mostrar", min_value=5, max_value=30, value=10)
    df_show = df_raw.sort_values('date', ascending=False).head(n_acts).copy()
    
    # Columnas a mostrar
    cols_display = ['date', 'name', 'tss', 'tss_source']
    if 'perceived_exertion' in df_show.columns:
        cols_display.append('perceived_exertion')
    if 'suffer_score' in df_show.columns:
        cols_display.append('suffer_score')
    
    df_show['date'] = df_show['date'].dt.strftime('%Y-%m-%d %H:%M')
    st.dataframe(
        df_show[cols_display].rename(columns={
            'date': 'Fecha', 'name': 'Actividad', 'tss': 'TSS',
            'tss_source': 'Fuente', 'perceived_exertion': 'RPE',
            'suffer_score': 'Suffer Score'
        }),
        use_container_width=True, hide_index=True
    )
    
    st.divider()
    st.subheader("🔍 Detalle de Sensaciones")
    
    opciones = [f"{r['date']} – {r['name']}" for _, r in df_raw.sort_values('date', ascending=False).head(20).iterrows()]
    seleccion = st.selectbox("Elige una actividad", opciones)
    
    if seleccion:
        idx = opciones.index(seleccion)
        row = df_raw.sort_values('date', ascending=False).iloc[idx]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("TSS", round(row['tss'], 1))
        if pd.notna(row.get('perceived_exertion')):
            c2.metric("RPE (1–10)", row['perceived_exertion'])
        if pd.notna(row.get('suffer_score')):
            c3.metric("Suffer Score", row['suffer_score'])
        
        if row.get('description'):
            st.markdown(f"**📝 Descripción Pública:**\n> {row['description']}")
        if row.get('private_note'):
            st.markdown(f"**🔒 Notas Privadas:**\n> {row['private_note']}")
        if not row.get('description') and not row.get('private_note'):
            st.info("Esta actividad no tiene notas o comentarios registrados.")
