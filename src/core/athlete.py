# src/core/athlete.py
import logging
from src.config import DEFAULT_FTP, DEFAULT_MAX_HR, DEFAULT_LTHR, DEFAULT_WEIGHT_KG

logger = logging.getLogger(__name__)

class AthleteProfile:
    """Clase que encapsula la fisiología y configuración del atleta."""
    
    def __init__(self, ftp: int = None, max_hr: int = None, lthr: int = None, weight_kg: float = None):
        """
        Si no se pasan parámetros, la clase inicializará automáticamente con las constantes de src.config
        """
        self.ftp = ftp or DEFAULT_FTP
        self.max_hr = max_hr or DEFAULT_MAX_HR
        self.lthr = lthr or DEFAULT_LTHR
        self.weight_kg = weight_kg or DEFAULT_WEIGHT_KG

        if self.ftp <= 0:
            raise ValueError("El FTP debe ser mayor a 0 para calcular métricas de potencia de forma realista.")
        
        if self.lthr is None and self.max_hr is not None:
            self.lthr = int(self.max_hr * 0.88)
            logger.info("LTHR estimado automáticamente a %s bpm", self.lthr)

    def get_coggan_power_zones(self):
        """Modelo Coggan de 7 zonas."""
        return {
            'Z1_Recovery':      (0, int(self.ftp * 0.55)),
            'Z2_Endurance':     (int(self.ftp * 0.55)+1, int(self.ftp * 0.75)),
            'Z3_Tempo':         (int(self.ftp * 0.75)+1, int(self.ftp * 0.90)),
            'Z4_SweetSpot':     (int(self.ftp * 0.90)+1, int(self.ftp * 1.05)),
            'Z5_VO2_Max':       (int(self.ftp * 1.05)+1, int(self.ftp * 1.20)),
            'Z6_Anaerobic':     (int(self.ftp * 1.20)+1, int(self.ftp * 1.50)),
            'Z7_Neuromuscular': (int(self.ftp * 1.50)+1, 3000)
        }

    def get_friel_hr_zones(self):
        """Modelo Joe Friel de 7 zonas cardiacas."""
        if not self.lthr:
            return None
        return {
            'Z1_Recovery':  (0, int(self.lthr * 0.81)),
            'Z2_Aerobic':   (int(self.lthr * 0.81)+1, int(self.lthr * 0.89)),
            'Z3_Tempo':     (int(self.lthr * 0.89)+1, int(self.lthr * 0.93)),
            'Z4_SubThr':    (int(self.lthr * 0.93)+1, int(self.lthr * 0.99)),
            'Z5a_SuperThr': (int(self.lthr * 0.99)+1, int(self.lthr * 1.02)),
            'Z5b_Anaerobic':(int(self.lthr * 1.02)+1, int(self.lthr * 1.06)),
            'Z5c_AllOut':   (int(self.lthr * 1.06)+1, int(self.max_hr * 1.1) if self.max_hr else 250) 
        }

    def power_to_weight(self):
        return round(self.ftp / self.weight_kg, 2) if self.weight_kg else None
