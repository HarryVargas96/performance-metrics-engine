import os
import requests
from dotenv import load_dotenv

def get_new_token():
    load_dotenv()
    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Falta el CLIENT_ID o CLIENT_SECRET en el .env")
        return
        
    print("\n==============================================")
    print("🔑 OBTENIENDO NUEVOS PERMISOS PARA TUS DATOS")
    print("==============================================\n")
    print("Paso 1: Copia y pega la siguiente URL en tu navegador:\n")
    
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={client_id}&response_type=code&redirect_uri=http://localhost/exchange_token&approval_prompt=force&scope=activity:read_all"
    print(auth_url)
    print("\nPaso 2: Strava te pedirá autorizar tu propia aplicación para 'Ver datos de tus actividades'. Dale a Autorizar.")
    
    print("\nPaso 3: Serás redirigido a una página en el navegador que dirá algo como 'localhost rechazó la conexión'. ¡ESTO ESPERADO!")
    print("\nPaso 4: Fíjate en la URL de esa página de error. Verás algo así:")
    print("   http://localhost/exchange_token?state=&code=ESTE_ES_EL_CODIGO&scope=...")
    print("\nCopia únicamente el pedazo de texto que viene después de 'code=' y pégalo abajo.")
    
    code = input("\nIngresa el código que obtuviste: ")
    
    print("\nGenerando tu nuevo Token...")
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code.strip(),
        "grant_type": "authorization_code"
    }
    
    response = requests.post(token_url, data=payload)
    if response.status_code == 200:
        data = response.json()
        print("\n✅ ¡ÉXITO! Ahora abre tu archivo .env y reemplaza los tokens viejos por estos nuevos:\n")
        print("Copia y reemplaza esto en el .env:")
        print(f"STRAVA_ACCESS_TOKEN={data.get('access_token')}")
        print(f"STRAVA_REFRESH_TOKEN={data.get('refresh_token')}\n")
    else:
        print("\n❌ Error creando el token:")
        print(response.text)

if __name__ == "__main__":
    get_new_token()
