# Glosario de Métricas de Rendimiento (PMC) 📈🚴‍♂️

Este documento explica las bases científicas y matemáticas de los cálculos utilizados en el **Performance Metrics Engine**.

## 1. Métricas de Carga de Entrenamiento (TSS)

El **TSS (Training Stress Score)** cuantifica la carga fisiológica de una sesión individual.

### ⚡ Estimación por Potencia (TSS)
Es el método más preciso (Gold Standard). Se basa en la potencia normalizada (NP) respecto a tu umbral (FTP).
*   **NP (Normalized Power):** Media suavizada que penaliza los picos de intensidad (potencia a la cuarta potencia).
*   **IF (Intensity Factor):** Relación entre NP y FTP (`NP / FTP`).
*   **Fórmula TSS:** `TSS = ((segundos * NP * IF) / (FTP * 3600)) * 100`

### 💓 Estimación por Pulso (hrTSS)
Utilizada cuando no hay potenciómetro. Estima el estrés metabólico según el tiempo pasado en diferentes zonas de frecuencia cardíaca respecto al umbral lactato (LTHR).
*   Se basa en el modelo de impulsos de entrenamiento (TRIMP).
*   Zonas más intensas multiplican el estrés exponencialmente.

---

## 2. El Performance Management Chart (PMC)

El PMC combina el estrés de hoy con el historial previo para estimar tu estado de forma.

### 🚀 CTL (Chronic Training Load) - "Fitness"
*   **Definición:** Media con decaimiento exponencial de tu TSS diario de los últimos **42 días**.
*   **Intuición:** Representa tu base aeróbica y volumen acumulado. Tarda semanas en subir y semanas en bajar.
*   **Fórmula:** `CTL_hoy = CTL_ayer + (TSS_hoy - CTL_ayer) * (1/42)`

### 🔥 ATL (Acute Training Load) - "Fatiga"
*   **Definición:** Media con decaimiento exponencial de tu TSS diario de los últimos **7 días**.
*   **Intuición:** Representa el cansancio residual de tus sesiones más recientes. Sube muy rápido tras un entrenamiento duro.
*   **Fórmula:** `ATL_hoy = ATL_ayer + (TSS_hoy - ATL_ayer) * (1/7)`

### 🎯 TSB (Training Stress Balance) - "Forma"
*   **Definición:** Diferencia entre Fitness y Fatiga (`CTL - ATL`).
*   **Intuición:** Indica qué tan "fresco" estás para competir o entrenar duro.
    *   **TSB (+):** Estás fresco (fase de "tapering" o descanso).
    *   **TSB (-):** Estás productivamente cansado (fase de carga).
    *   **TSB (< -20):** Riesgo de sobreentrenamiento o lesión.

---

## 📅 Referencias Técnicas
El motor utiliza una ventana de **90 días** para asegurar que el cálculo de CTL tenga tiempo de "calentarse" y sea preciso al llegar a la fecha actual.
