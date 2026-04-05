# Performance Metrics Engine 🚴‍♂️📊

Motor de análisis fisiológico avanzado que integra datos de **Strava** con ciencia del deporte para calcular métricas de rendimiento real (CTL, ATL, TSS).

## 🚀 Capacidades Recientes

- **Autenticación Auto-Suficiente:** Integración con Strava OAuth 2.0 que refresca automáticamente el `ACCESS_TOKEN` y actualiza el `.env` dinámicamente.
- **Motor PMC (Performance Management Chart):** Cálculo de Fitness (CTL), Fatiga (ATL) y Forma (TSB) basado en datos históricos (90 días).
- **Contexto Avanzado para LLMs:** Generación de resúmenes estructurados en JSON específicamente diseñados para ser interpretados por **Gemini**, incluyendo:
    - Snapshot actual de métricas PMC.
    - Tendencias de carga de las últimas 8 semanas.
    - Detalle de sensaciones y métricas de los últimos 7 días.
- **Exploración Visual (Notebooks):** Cuaderno interactivo basado en **Plotly** para ver la evolución del fitness y analizar telemetría detallada (potencia/pulso) por segundo.

## 🛠️ Cómo Usar el Sistema

### 1. Sincronizar Datos (Strava API)
Este comando descarga tus últimas actividades, calcula su TSS (vía Potencia o Frecuencia Cardíaca) y actualiza el historial local en Parquet.
```bash
poetry run python src/services/sync.py
```

### 2. Ver Estado Actual (Virtual Coach)
Muestra un dashboard por consola sobre tu nivel de fatiga, fitness y genera el contexto JSON para tu Coach de IA.
```bash
poetry run python src/status.py
```

### 3. Exploración Interactiva
Abre el notebook para visualizar gráficamente tu progreso y analizar sesiones específicas.
*   Archivo: `notebooks/2_fitness_exploration.ipynb`
*   Requiere: Extensión Jupyter en VS Code.

## 📁 Estructura del Proyecto

- `src/api/`: Cliente de Strava con rotación de tokens.
- `src/core/`: Motores de cálculo (PMC, TSS, Athlete Profile).
- `src/services/`: Lógica de sincronización y reporte para el Coach.
- `data/`: Almacenamiento eficiente en formato Parquet (`tss_history.parquet`).
- `notebooks/`: Cuadernos de experimentación y visualización.

## ⚙️ Configuración (Athlete Profile)
Puedes ajustar tu **FTP**, **LTHR**, **Peso** y **Zonas de Entrenamiento** directamente en `src/config.py`. El sistema recalculará todo el historial automágicamente al siguiente sync.
