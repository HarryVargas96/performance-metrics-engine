# Performance Metrics Engine 🏃‍♂️🚴‍♀️

An AI-powered training data pipeline and dashboard designed to ingest raw workout data from the Strava API, compute advanced **Performance Management Chart (PMC)** metrics like Chronic Training Load (CTL), Acute Training Load (ATL), Training Stress Score (TSS), and Fatigue. It ultimately acts as a context engine for Google's Gemini LLM—fed with sports science literature—to generate highly personalized, science-based coaching insights.

## Project Vision 🚀
The fundamental goal of this project is to build a Virtual Endurance Coach. By marrying sports science with cutting-edge artificial intelligence, this engine will:
1. **Automate Data Extraction:** Continuously pull workout data (distance, duration, heart rate, power, perceived exertion) directly from your devices via Strava.
2. **Compute Real Physiological Metrics:** Replicate complex calculations typically reserved for premium platforms like TrainingPeaks (calculating rolling averages for CTL, ATL, and TSS).
3. **Generate Actionable Insights using Generative AI:** Feed these daily metrics, along with curated sports science literature, into **Gemini** to answer questions like:
   - *"Am I overtraining based on my current TSS ramp rate?"*
   - *"What kind of workout should I do tomorrow to achieve a positive Form (TSB) for my race this weekend?"*

## Desarrollo y Uso

### 1. Configuración Fisiológica
Ajusta tu **FTP**, **Max HR** y **Peso** en el archivo central:
`src/core/athlete.py` (o en su defecto `src/config.py`).

### 2. Sincronización de Datos (Persistence Layer)
Ejecuta el sincronizador para bajar tu historial de Strava (últimos 90 días), calcular TSS y guardar en formato **Parquet**:
```powershell
poetry run python src/services/sync.py
```
*Este proceso descarga automáticamente las descripciones/comentarios de Strava para análisis de sensaciones.*

### 3. Análisis de Actividades Individuales (CLI)
Para analizar una actividad específica por su ID:
```powershell
poetry run python src/main.py <activity_id>
```

### 4. Coach de Inteligencia Artificial
Si tienes configurada tu `GEMINI_API_KEY` en el `.env`, puedes obtener consejos expertos:
```powershell
poetry run python src/services/coach.py
```

---
*Developed for training optimization and data-driven athletic performance.*
