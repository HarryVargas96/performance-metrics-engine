# 🚴‍♂️ Performance Metrics Engine (PME) 📊

Motor de rendimiento fisiológico de grado profesional para ciclistas y atletas de resistencia. Integra datos de **Strava** con modelos avanzados de ciencia del deporte (Coggan/Friel) para calcular **CTL, ATL, TSB y TSS**.

---

## 🌟 Características Principales

- **Dashboard Interactivo:** Visualiza tu Fitness (CTL), Fatiga (ATL) y Forma (TSB) en tiempo real con Streamlit.
- **Auth Setup "One-Click":** Proceso automatizado de autorización Strava OAuth2 (sin URLs manuales).
- **Inteligencia Sensorial:** Captura no solo vatios y pulso, sino también tus **Notas Privadas** y **Esfuerzo Percibido (RPE)**.
- **Virtual Coach Readiness:** Genera contexto JSON estructurado para alimentar a modelos de IA (Gemini/ChatGPT).
- **Cálculo Híbrido de Carga:** Soporte nativo para **TSS (Potencia)** y fallback automático a **hrTSS (Pulso)**.

---

## 🛠️ Guía de Configuración Paso a Paso (PME Setup)

Sigue estos pasos para tener tu motor funcionando en menos de 5 minutos:

### 0. Requisitos Previos y Clonación
Para usar este proyecto en Windows, se recomienda tener instalado [Git Bash](https://gitfor-windows.github.io/) para manejar comandos de terminal cómodamente.

```bash
# Clonar el repositorio
git clone https://github.com/HarryVargas96/performance-metrics-engine.git
cd performance-metrics-engine

# Instalar dependencias con Poetry
poetry install
```

### 1. Preparar Strava (API)
1. Ve a [Strava Settings > My API Application](https://www.strava.com/settings/api).
2. Crea una aplicación (Nombre: "My PME", Website: "http://localhost").
3. Copia tu **Client ID** y **Client Secret**.

### 2. Configuración Inicial (Entorno)
Copia el archivo de ejemplo a un `.env` real:
```bash
# Crea tu .env y pega tu Client ID y Secret allí
STRAVA_CLIENT_ID=XXXXX
STRAVA_CLIENT_SECRET=YYYYY
# Opcional: Perfil del atleta
ATHLETE_FTP=250
ATHLETE_LTHR=175
ATHLETE_WEIGHT=70
```

### 3. Autenticación Automática 🔑
Ejecuta el script de autorización:
```bash
make auth  
# O manualmente: poetry run python src/api/auth_setup.py
```
*Se abrirá tu navegador. Autoriza la aplicación y listo. Tus tokens se guardarán solos en el `.env`.*

---

## 🚀 Uso Diario

### Sincronización de Datos
Descarga tus actividades, calcula la carga (TSS) y actualiza el historial local:
```bash
make sync
# Opcional: --days 20 para sync rápido
```

### Dashboard de Rendimiento
Lanza la interfaz visual para ver tus gráficas y sensaciones:
```bash
make dashboard
```

### Reporte de IA (Virtual Coach)
Genera el bloque de contexto para enviarlo a tu entrenador virtual:
```bash
make status
```

---

## 📂 Arquitectura del Sistema

- **`src/api/`**: Cliente de Strava con rotación automática de tokens y setup de auth.
- **`src/core/`**: Motores de cálculo fisiológico (PMC, TSS, Zonas).
- **`src/services/`**: Orquestación de sincronización y generación de contexto LLM.
- **`data/`**: Almacenamiento persistente en formato **Parquet** (eficiencia extrema).
- **`Makefile`**: Atajos de comandos para una experiencia simplificada.

---

## ⚙️ Personalización Fisiológica

Puedes ajustar tus umbrales en el `.env` o directamente en `src/core/athlete.py`. El motor recalculará todo tu historial de fatiga y fitness basándose en tus ajustes actuales de FTP y LTHR.

---
## 📚 Más Información y Dominios

Si quieres profundizar en cómo funciona el motor o en las definiciones científicas detrás de las métricas, consulta nuestra documentación detallada:

*   **[Definición de Métricas](docs/metrics_definitions.md):** Qué significa TSS, CTL, ATL y cómo se calculan para Potencia y Pulso.
*   **[Arquitectura del Sistema](docs/architecture.md):** Cómo fluye el dato desde Strava hasta el Parquet local.
*   **[Guía de Clases](docs/classes.md):** Referencia técnica de los módulos y responsabilidades de cada objeto Python.

---
> [!TIP]
> **¿Por qué usar PME?** A diferencia de Strava Free, PME te da acceso gratuito a las métricas de carga crónica (Fitness) y fatiga que suelen estar detrás de un muro de pago, además de permitirte exportar tus sensaciones subjetivas para análisis con IA.
