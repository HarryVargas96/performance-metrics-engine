"""Modelo de datos y configuración fisiológica del atleta.

Define los umbrales de rendimiento (FTP, LTHR), peso y zonas de potencia/FC
necesarias para los cálculos analíticos del Performance Metrics Engine.
"""

import os
from dotenv import load_dotenv
import logging

# Logger para la configuración del perfil
logger = logging.getLogger(__name__)

class AthleteProfile:
    """Perfil fisiológico del atleta cargado desde variables de entorno.

    Permite obtener zonas dinámicas de entrenamiento basadas en umbrales 
    e información antropométrica como peso.

    Attributes:
        ftp (int): Umbral de Potencia Funcional (Functional Threshold Power) en W.
        max_hr (int): Frecuencia cardíaca máxima en bpm.
        lthr (int): Umbral de Lactato (Lactate Threshold Heart Rate) en bpm.
        weight_kg (float): Peso corporal del atleta en kilogramos.
    """
    
    def __init__(self):
        """Inicializa el perfil cargando constantes desde el entorno .env."""
        load_dotenv()
        self.ftp = int(os.getenv("ATHLETE_FTP", 200))
        self.max_hr = int(os.getenv("ATHLETE_MAX_HR", 195))
        self.lthr = int(os.getenv("ATHLETE_LTHR", 175))
        self.weight_kg = float(os.getenv("ATHLETE_WEIGHT", 72.0))
        
        logger.info("Perfil del Atleta cargado satisfactoriamente (FTP: %s W, LTHR: %s bpm).", self.ftp, self.lthr)

    def power_to_weight(self) -> float:
        """Calcula la relación potencia a peso (W/kg).

        Returns:
            float: Relación W/kg de 1 hora redondeada a 2 decimales.
        """
        return round(self.ftp / self.weight_kg, 2) if self.weight_kg > 0 else 0.0

    def get_coggan_power_zones(self) -> dict:
        """Genera zonas de potencia basadas en el modelo de Andrew Coggan.

        Se basa en porcentajes del FTP para determinar 7 zonas metabólicas.

        Returns:
            dict: Diccionario de zonas con nombre y tupla de (vatios min, vatios max).
        """
        return {
            'Z1_ActiveRecovery': (0, int(0.55 * self.ftp)),
            'Z2_Endurance': (int(0.55 * self.ftp) + 1, int(0.75 * self.ftp)),
            'Z3_Tempo': (int(0.75 * self.ftp) + 1, int(0.90 * self.ftp)),
            'Z4_LactateThreshold': (int(0.90 * self.ftp) + 1, int(1.05 * self.ftp)),
            'Z5_V02Max': (int(1.05 * self.ftp) + 1, int(1.20 * self.ftp)),
            'Z6_AnaerobicCapacity': (int(1.20 * self.ftp) + 1, int(1.50 * self.ftp)),
            'Z7_NeuromuscularPower': (int(1.50 * self.ftp) + 1, 9999)
        }

    def get_friel_hr_zones(self) -> dict:
        """Genera zonas de frecuencia cardíaca según el modelo de Joe Friel.

        Calcula 7 zonas aeróbicas y anaeróbicas basadas en el LTHR.

        Returns:
            dict: Diccionario de zonas (nombre y rango de pulsaciones).
        """
        if not self.lthr:
            logger.warning("No se puede calcular zonas HR: LTHR no definido.")
            return {}
        return {
            'Z1_Recovery': (0, int(0.81 * self.lthr)),
            'Z2_Aerobic': (int(0.81 * self.lthr) + 1, int(0.89 * self.lthr)),
            'Z3_Tempo': (int(0.89 * self.lthr) + 1, int(0.93 * self.lthr)),
            'Z4_SubThr': (int(0.93 * self.lthr) + 1, int(0.99 * self.lthr)),
            'Z5a_SuperThr': (int(0.99 * self.lthr) + 1, int(1.02 * self.lthr)),
            'Z5b_Anaerobic': (int(1.02 * self.lthr) + 1, int(1.06 * self.lthr)),
            'Z5c_AllOut': (int(1.06 * self.lthr) + 1, 250)
        }

    def to_dict(self) -> dict:
        """Serializa el perfil a un diccionario para reporting o integración LLM.

        Returns:
            dict: Atributos clave del atleta.
        """
        return {
            "ftp": self.ftp,
            "max_hr": self.max_hr,
            "lthr": self.lthr,
            "weight_kg": self.weight_kg,
            "w_kg": self.power_to_weight()
        }
