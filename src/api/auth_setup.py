# src/api/auth_setup.py
"""Módulo de configuración inicial de autenticación Strava OAuth2.

Este script automatiza el proceso de autorización inicial de Strava,
evitando que el usuario tenga que construir URLs manualmente. Levanta un 
servidor local temporal para capturar el callback de redirección.

Requirements:
    - Flask
    - webbrowser
    - STRAVA_CLIENT_ID y STRAVA_CLIENT_SECRET en el .env
"""

import os
import sys
import logging
import webbrowser
import requests
from flask import Flask, request
from dotenv import load_dotenv, set_key, find_dotenv

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuración de Strava
CLIENT_ID = None
CLIENT_SECRET = None
REDIRECT_URI = "http://localhost:8000/callback"

def update_env_file(access_token, refresh_token):
    """Actualiza o crea el archivo .env con los tokens obtenidos.

    Args:
        access_token (str): El token de acceso inicial (6h).
        refresh_token (str): El token para renovar el acceso.
    """
    env_path = find_dotenv() or ".env"
    set_key(env_path, "STRAVA_ACCESS_TOKEN", access_token)
    set_key(env_path, "STRAVA_REFRESH_TOKEN", refresh_token)
    logger.info("Archivo .env actualizado con los tokens de Strava.")

@app.route('/callback')
def callback():
    """Captura el 'code' enviado por Strava tras la autorización del usuario."""
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        return f"Error en la autorización: {error}", 400

    if not code:
        return "No se recibió código de autorización.", 400

    # Intercambiar código por tokens
    logger.info("Intercambiando código de autorización por tokens...")
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    }

    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
        data = response.json()
        
        update_env_file(data['access_token'], data['refresh_token'])
        
        return "✅ ¡Éxito! Los tokens han sido guardados en tu archivo .env. Ya puedes cerrar esta pestaña y detener el script (Ctrl+C)."
    except Exception as e:
        logger.error(f"Fallo al intercambiar tokens: {e}")
        return f"Error intercambiando tokens: {e}", 500

def main():
    """Punto de entrada principal para el proceso de autorización."""
    global CLIENT_ID, CLIENT_SECRET
    load_dotenv()
    
    CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
    CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")

    if not CLIENT_ID or not CLIENT_SECRET:
        logger.error("No se encontró CLIENT_ID o CLIENT_SECRET en el .env.")
        print("\n--- INSTRUCCIONES ---")
        print("1. Ve a https://www.strava.com/settings/api")
        print("2. Crea una aplicación si no tienes una.")
        print("3. Copia el 'Client ID' y 'Client Secret' en tu archivo .env.")
        print("4. Vuelve a ejecutar este script.\n")
        sys.exit(1)

    # Alcance de permisos: Le pedimos a Strava leer actividades (incluyendo privadas)
    # Scope 'activity:read_all' es vital para ver las notas privadas
    scope = "read,activity:read_all,profile:read_all"
    auth_url = (
        f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}&response_type=code"
        f"&scope={scope}&approval_prompt=force"
    )

    logger.info("Abriendo navegador para autorización de Strava...")
    webbrowser.open(auth_url)

    logger.info("Servidor escuchando en http://localhost:8000/callback")
    app.run(port=8000)

if __name__ == "__main__":
    main()
