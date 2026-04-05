# Documentación de Clases y Métodos

Este documento profundiza en el comportamiento y las responsabilidades de cada clase e interfaz pública dentro del directorio `src/`.

---

## 🏃 `src/strava_client.py`

### `StravaClient`
**Responsabilidad**: Comunicación exclusiva con la API de Strava.
- `get_athlete_info()`: Obtiene el perfil básico (Nombre, ID) del atleta authenticado.
- `get_recent_activities(days, per_page, return_dataframe)`: Lista actividades recientes (metadatos generales).
- `get_activity(activity_id)`: Detalles base de una actividad (fecha, nombre, ID).
- `get_activity_streams(activity_id, keys, start_date)`: **El método pesado**. Baja telemetría segundo-a-segundo. Implementa la reconstrucción automática de `timestamp` si se le provee la fecha.

---

## 🛠️ `src/athlete_config.py`

### `AthleteProfile`
**Responsabilidad**: Modelar la fisiología del deportista y sus rangos de esfuerzo.
- `get_coggan_power_zones()`: Retorna un diccionario con los vatios de las 7 zonas de potencia basadas en el FTP de `config.py`.
- `get_friel_hr_zones()`: Retorna un diccionario con los latidos (bpm) de las 7 zonas de frecuencia cardíaca basadas en el Lactate Threshold (LTHR).
- `power_to_weight()`: Radio W/kg del atleta.

---

## 📈 `src/metrics_processor.py`

### `ActivityMetricsCalculator`
**Responsabilidad**: Procesamiento avanzado de telemetría bruta en métricas fisiológicas.
- `calculate_normalized_power(df_streams)`: Implementa la fórmula de **Dr. Andy Coggan** (Media móvil 30s + elevar a la 4ta potencia + raíz cuarta).
- `calculate_tss_if(np_value, duration_seconds)`: Calcula el estrés y el Intensity Factor.
- `calculate_hr_tss(df_streams)`: **Algoritmo de fallback** basado en tiempo en zonas cardíacas con pesos.
- `calculate_time_in_zones(df_streams, source)`: Agrupa los segundos grabados en sus 7 zonas correspondientes.
- `process_full_activity_summary(df_streams)`: **Método Maestro**. Retorna un JSON completo con toda la analítica de la sesión.

---

## 📊 `src/pmc_processor.py`

### `PMCProcessor`
**Responsabilidad**: Análisis de series de tiempo de carga (TSS) para gestionar el entrenamiento.
- `calculate_pmc(df_tss)`: Calcula el **CTL** (Chronic Training Load - 42 días), **ATL** (Acute Training Load - 7 días) y **TSB** (Forma - Balance).
- `get_summary(df_pmc)`: Extrae el estado exacto "de hoy" del atleta para dárselo al Coach.

---

## 🧠 `src/coach_service.py`

### `GeminiCoach`
**Responsabilidad**: Traducción de métricas numéricas a lenguaje natural motivador y experto.
- `generate_coach_prompt(pmc_summary, workout_summary)`: Genera el prompt enriquecido para el LLM.
- `get_coaching_advice(pmc_summary, workout_summary)`: Envía el prompt a **Google Gemini** y retorna el análisis en español.

---

## ⚙️ `src/config.py`

No es una clase, sino el **Repositório de Parámetros Fisiológicos**. Aquí el usuario debe actualizar su **FTP**, **Max HR** y **Peso** para que el motor funcione con precisión milimétrica.
