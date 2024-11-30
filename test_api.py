import openai
import os
from dotenv import load_dotenv, find_dotenv

def test_openai_key():
    # Forzar la recarga del archivo .env
    load_dotenv(find_dotenv(), override=True)
    
    # Mostrar el directorio actual
    print(f"📂 Directorio actual: {os.getcwd()}")
    
    # Verificar si el archivo .env existe
    env_path = os.path.join(os.getcwd(), '.env')
    print(f"📄 Archivo .env existe: {os.path.exists(env_path)}")
    
    # Obtener la API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ No se encontró la API key en el archivo .env")
        return
    
    # Mostrar los primeros y últimos caracteres de la key para verificar
    print(f"🔑 API key encontrada: {api_key[:8]}...{api_key[-4:]}")
    
    try:
        # Crear cliente
        client = openai.Client(api_key=api_key)
        
        # Intentar listar modelos
        models = client.models.list()
        print("✅ API key válida!")
        print("📋 Modelos disponibles:")
        for model in models:
            print(f"  - {model.id}")
            
    except openai.AuthenticationError:
        print("❌ Error de autenticación: La API key no es válida")
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")

if __name__ == "__main__":
    test_openai_key() 