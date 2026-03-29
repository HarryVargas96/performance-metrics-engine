import os
import requests
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configuración básica del logger para desarrollo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StravaClient:
    """Clase principal para interactuar con la API de Strava."""
    
    def __init__(self):
        # Intenta cargar variables desde el .env si el código se ejecuta de base
        load_dotenv()
        self.access_token = os.getenv("STRAVA_ACCESS_TOKEN")
        self.base_url = "https://www.strava.com/api/v3"
        
        if not self.access_token:
            logger.error("Token de Acceso faltante. Revisa el archivo .env.")
            raise ValueError("No se encontró el Token de Acceso en las variables de entorno.")
            
        self.headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        logger.info("StravaClient inicializado correctamente.")

    def get_athlete_info(self):
        """
        Retorna la información básica del atleta autenticado en forma de diccionario.
        """
        url = f"{self.base_url}/athlete"
        logger.info("Buscando información del atleta en la API...")
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            logger.info("Información del atleta recuperada con éxito.")
            return response.json()
        else:
            logger.error("Error obteniendo atleta. Respuesta de la API: %s", response.text)
            response.raise_for_status()

    def get_recent_activities(self, days=30, per_page=50):
        """
        Retorna la lista de actividades registradas recientemenete.
        
        Parámetros:
        - days (int): Número de días hacia atrás a consultar (por defecto 30).
        - per_page (int): Límite de actividades por petición (por defecto 50).
        """
        url = f"{self.base_url}/athlete/activities"
        
        hace_n_dias = datetime.now() - timedelta(days=days)
        timestamp_after = int(hace_n_dias.timestamp())

        params = {
            "after": timestamp_after,
            "per_page": per_page
        }

        logger.info("Consultando actividades Strava de los últimos %s días...", days)
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            actividades = response.json()
            logger.info("Se devolvieron %s actividades correctamente.", len(actividades))
            return actividades
        else:
            logger.error("Error obteniendo actividades. Respuesta de la API: %s", response.text)
            response.raise_for_status()

# Pequeña prueba local (sólo se ejecuta si ejecutas directamente este archivo)
if __name__ == "__main__":
    client = StravaClient()
    
    info = client.get_athlete_info()
    if info:
        logger.info("Conectado como atleta verificado: %s %s", info.get('firstname'), info.get('lastname'))
    
    actividades = client.get_recent_activities()
    if actividades is not None:
        logger.info("Resumen final: se listaron %s actividades de manera exitosa.", len(actividades))
