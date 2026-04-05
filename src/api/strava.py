# src/api/strava.py
import os
import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key, find_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StravaClient:
    """Clase principal para interactuar con la API de Strava."""
    
    def __init__(self):
        load_dotenv()
        self.base_url = "https://www.strava.com/api/v3"
        
        # 1. Cargar credenciales desde .env
        self.client_id = os.getenv("STRAVA_CLIENT_ID")
        self.client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        self.access_token = os.getenv("STRAVA_ACCESS_TOKEN")
        self.refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")

        if not self.access_token or not self.refresh_token:
            logger.error("Credenciales de Strava incompletas en el .env.")
            raise ValueError("Faltan tokens o credenciales en las variables de entorno.")

        # 2. Refrescar token automáticamente al inicializar (Garantiza 6h extras de vida)
        self.refresh_access_token()
            
        self.headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        logger.info("StravaClient inicializado y autenticado.")

    def refresh_access_token(self):
        """Usa el REFRESH_TOKEN para obtener un nuevo ACCESS_TOKEN válido."""
        url = "https://www.strava.com/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        
        logger.info("Refrescando token de acceso con Strava...")
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            # A veces Strava también rota el refresh_token
            nuevo_refresh = data.get("refresh_token")
            
            # Actualizar el objeto y el archivo .env para persistencia
            self.update_env_file(self.access_token, nuevo_refresh)
            
            if nuevo_refresh:
                self.refresh_token = nuevo_refresh
        else:
            logger.error("No se pudo refrescar el token de Strava: %s", response.text)
            response.raise_for_status()

    def update_env_file(self, access_token, refresh_token):
        """Actualiza el archivo .env local con los nuevos tokens recibidos."""
        try:
            env_path = find_dotenv()
            if env_path:
                set_key(env_path, "STRAVA_ACCESS_TOKEN", access_token)
                if refresh_token:
                    set_key(env_path, "STRAVA_REFRESH_TOKEN", refresh_token)
                logger.info("Archivo .env actualizado con los nuevos tokens.")
            else:
                logger.warning("No se encontró el archivo .env para actualizarlo.")
        except Exception as e:
            logger.error("Error actualizando .env: %s", e)

    def get_athlete_info(self):
        url = f"{self.base_url}/athlete"
        logger.info("Buscando información del atleta en la API...")
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error obteniendo atleta. Respuesta de la API: %s", response.text)
            response.raise_for_status()

    def get_recent_activities(self, days=30, per_page=50, return_dataframe=True):
        url = f"{self.base_url}/athlete/activities"
        hace_n_dias = datetime.now() - timedelta(days=days)
        timestamp_after = int(hace_n_dias.timestamp())
        params = {"after": timestamp_after, "per_page": per_page}

        logger.info("Consultando actividades Strava de los últimos %s días...", days)
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            actividades = response.json()
            if not return_dataframe:
                return actividades
            if not actividades:
                return pd.DataFrame()
            
            df = pd.DataFrame(actividades)
            columnas_relevantes = [
                'id', 'name', 'type', 'start_date_local', 
                'distance', 'moving_time', 'elapsed_time', 
                'total_elevation_gain', 'average_speed', 
                'average_heartrate', 'max_heartrate', 'suffer_score'
            ]
            columnas_finales = [col for col in columnas_relevantes if col in df.columns]
            df = df[columnas_finales].copy()
            
            if 'distance' in df.columns:
                df['distance_km'] = (df['distance'] / 1000).round(2)
            if 'moving_time' in df.columns:
                df['moving_time_min'] = (df['moving_time'] / 60).round(2)
            if 'start_date_local' in df.columns:
                df['date'] = pd.to_datetime(df['start_date_local']).dt.date
            
            return df
        else:
            logger.error("Error obteniendo actividades. Respuesta de la API: %s", response.text)
            response.raise_for_status()

    def get_activity(self, activity_id):
        url = f"{self.base_url}/activities/{activity_id}"
        logger.info("Consultando detalles de la actividad %s...", activity_id)
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error obteniendo detalles de la actividad %s. Respuesta: %s", activity_id, response.text)
            response.raise_for_status()

    def get_activity_streams(self, activity_id, keys=None, return_dataframe=True, start_date=None):
        if keys is None:
            keys = ['time', 'distance', 'heartrate', 'cadence', 'velocity_smooth', 'watts', 'altitude', 'temp', 'moving', 'grade_smooth']
            
        url = f"{self.base_url}/activities/{activity_id}/streams"
        params = {"keys": ",".join(keys), "key_by_type": "true"}
        
        logger.info("📥 Descargando telemetría pesada de la actividad %s...", activity_id)
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            streams_crudos = response.json()
            if not return_dataframe:
                return streams_crudos
                
            datos_ordenados = {metrica: info.get('data', []) for metrica, info in streams_crudos.items()}
            df_stream = pd.DataFrame(datos_ordenados)
            
            if 'velocity_smooth' in df_stream.columns:
                df_stream['speed_kmh'] = (df_stream['velocity_smooth'] * 3.6).round(2)
                df_stream.drop(columns=['velocity_smooth'], inplace=True)
                
            if return_dataframe and start_date is None and 'time' in df_stream.columns:
                detalles = self.get_activity(activity_id)
                start_date = detalles.get('start_date_local') or detalles.get('start_date')

            if start_date and 'time' in df_stream.columns:
                inicio_dt = pd.to_datetime(start_date)
                df_stream['timestamp'] = inicio_dt + pd.to_timedelta(df_stream['time'], unit='s')
                
            return df_stream
        else:
            logger.error("Error al descargar streams: %s", response.text)
            response.raise_for_status()
