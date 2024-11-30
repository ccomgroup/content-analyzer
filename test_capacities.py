import requests
import os
from dotenv import load_dotenv

def test_capacities_credentials():
    # Cargar variables de entorno
    load_dotenv()
    
    api_key = os.getenv("CAPACITIES_API_KEY")
    space_id = os.getenv("CAPACITIES_SPACE_ID")
    
    print(f"Space ID: {space_id}")
    print(f"API Key (primeros 8 caracteres): {api_key[:8]}...")
    
    # Configurar headers
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # URLs a probar
    urls = [
        f"https://app.capacities.io/api/v1/spaces/{space_id}",
        f"https://capacities.io/api/spaces/{space_id}",
        f"https://api.capacities.io/v1/spaces/{space_id}",
        f"https://app.capacities.io/api/spaces/{space_id}"
    ]
    
    # Probar cada URL
    for url in urls:
        print(f"\nProbando URL: {url}")
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=10
            )
            
            print(f"Código de estado: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Respuesta: {response.text[:200]}...")  # Primeros 200 caracteres
            
            if response.status_code == 200:
                print("\n✅ Conexión exitosa con esta URL")
                print("\nHeaders y datos para usar:")
                print(f"URL base: {url.split('/api')[0]}")
                print(f"Headers: {headers}")
                return
                
        except Exception as e:
            print(f"Error con esta URL: {str(e)}")
    
    print("\n❌ No se pudo conectar con ninguna URL")

if __name__ == "__main__":
    test_capacities_credentials() 