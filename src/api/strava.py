"""Cliente de la API de Strava para gestión de datos de actividades.

Este módulo contiene la clase StravaClient, que maneja la autenticación,
el refresco de tokens y la recuperación de datos de actividades y streams.
"""

import os
import requests
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key, find_dotenv

# Configuración de logs unificada para el módulo
logger = logging.getLogger(__name__)

class StravaClient:
    """Clase principal para interactuar con la API de Strava.

    Maneja el ciclo de vida de la autenticación OAuth2, incluyendo el refresco
    automático de tokens y la persistencia en el archivo .env.

    Attributes:
        base_url (str): URL base de la API de Strava v3.
        client_id (str): ID de cliente Strava obtenido en el panel de API.
        client_secret (str): Secreto de cliente Strava.
        access_token (str): Token de acceso actual.
        refresh_token (str): Token para renovar el acceso.
        headers (dict): Cabeceras HTTP para las peticiones a la API.
    """
    
    def __init__(self):
        """Inicializa el cliente de Strava y refresca los tokens si es necesario."""
        load_dotenv()
        self.base_url = "https://www.strava.com/api/v3"
        
        self.client_id = os.getenv("STRAVA_CLIENT_ID")
        self.client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        self.access_token = os.getenv("STRAVA_ACCESS_TOKEN")
        self.refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")

        if not self.access_token or not self.refresh_token:
            logger.error("Credenciales de Strava incompletas en el .env.")
            raise ValueError("Faltan tokens o credenciales en las variables de entorno.")

        # Refrescar token automáticamente al inicializar para garantizar validez
        self.refresh_access_token()
            
        self.headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        logger.info("StravaClient inicializado y autenticado satisfactoriamente.")

    def refresh_access_token(self):
        """Refresca el token de acceso usando el token de actualización.

        Usa el REFRESH_TOKEN para obtener un nuevo ACCESS_TOKEN válido y
        actualiza tanto los atributos de la instancia como el archivo .env.

        Raises:
            requests.exceptions.HTTPError: Si la petición a Strava falla.
        """
        url = "https://www.strava.com/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        
        logger.info("Iniciando proceso de refresco de token con Strava...")
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            nuevo_refresh = data.get("refresh_token")
            
            self.update_env_file(self.access_token, nuevo_refresh)
            
            if nuevo_refresh:
                self.refresh_token = nuevo_refresh
        else:
            logger.error("Error al refrescar el token de Strava: %s", response.text)
            response.raise_for_status()

    def update_env_file(self, access_token, refresh_token):
        """Persiste los nuevos tokens en el archivo .env local.

        Args:
            access_token (str): El nuevo token de acceso.
            refresh_token (str, optional): El nuevo token de refresco (si cambió).
        """
        try:
            env_path = find_dotenv()
            if env_path:
                set_key(env_path, "STRAVA_ACCESS_TOKEN", access_token)
                if refresh_token:
                    set_key(env_path, "STRAVA_REFRESH_TOKEN", refresh_token)
                logger.debug("Archivo .env actualizado con los tokens actualizados.")
            else:
                logger.warning("No se encontró archivo .env; los tokens solo persistirán en memoria.")
        except Exception as e:
            logger.error("Fallo inesperado al actualizar .env: %s", e)

    def get_athlete_info(self):
        """Obtiene la información del perfil del atleta autenticado.

        Returns:
            dict: Datos del atleta (nombre, ID, etc.).
        """
        url = f"{self.base_url}/athlete"
        logger.v("Solicitando información del perfil del atleta...")
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error recuperando info del atleta: %s", response.text)
            response.raise_for_status()

    def get_recent_activities(self, days=30, per_page=50, return_dataframe=True):
        """Consulta la lista de actividades recientes del atleta.

        Args:
            days (int): Ventana de días hacia atrás desde hoy.
            per_page (int): Cantidad de actividades por página.
            return_dataframe (bool): Si es True, retorna un DataFrame de Pandas.

        Returns:
            Union[pd.DataFrame, list]: Lista de actividades procesada o cruda.
        """
        url = f"{self.base_url}/athlete/activities"
        hace_n_dias = datetime.now() - timedelta(days=days)
        timestamp_after = int(hace_n_dias.timestamp())
        params = {"after": timestamp_after, "per_page": per_page}

        logger.info("Buscando actividades Strava de los últimos %s días...", days)
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
            logger.error("Error consultando actividades: %s", response.text)
            response.raise_for_status()

    def get_activity(self, activity_id):
        """Obtiene el detalle completo de una actividad específica.

        Args:
            activity_id (int): ID único de la actividad en Strava.

        Returns:
            dict: Detalle de la actividad incluyendo descripción y notas privadas.
        """
        url = f"{self.base_url}/activities/{activity_id}"
        logger.debug("Consultando detalle de actividad ID: %s", activity_id)
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error("Error recuperando actividad %s: %s", activity_id, response.text)
            response.raise_for_status()

    def get_activity_streams(self, activity_id, keys=None, return_dataframe=True, start_date=None):
        """Descarga la telemetría segundo a segundo de una actividad.

        Args:
            activity_id (int): ID de la actividad.
            keys (list, optional): Métricas a descargar (watts, heartrate, etc.).
            return_dataframe (bool): Si retorna un DF de Pandas.
            start_date (str, optional): Fecha de inicio para reconstruir timestamps.

        Returns:
            Union[pd.DataFrame, dict]: Telemetría de la sesión.
        """
        if keys is None:
            keys = ['time', 'distance', 'heartrate', 'cadence', 'velocity_smooth', 'watts', 'altitude', 'temp', 'moving', 'grade_smooth']
            
        url = f"{self.base_url}/activities/{activity_id}/streams"
        params = {"keys": ",".join(keys), "key_by_type": "true"}
        
        logger.info("Recuperando telemetría pesada (streams) para actividad %s...", activity_id)
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
            logger.error("Fallo al descargar streams: %s", response.text)
            response.raise_for_status()
