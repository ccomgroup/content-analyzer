import os
import subprocess
import sys

def check_venv():
    # Verifica si estamos en un entorno virtual
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        print("✅ Estás dentro del entorno virtual")
        print(f"📍 Ubicación del entorno: {sys.prefix}")
    else:
        print("❌ No estás dentro de un entorno virtual")
        print("Activar el entorno con:")
        print("source .venv/bin/activate")
        sys.exit(1)

def run_app():
    # Primero verificamos el entorno virtual
    check_venv()
    
    # Activar el entorno virtual
    venv_path = os.path.join(os.getcwd(), '.venv', 'bin')
    streamlit_path = os.path.join(venv_path, 'streamlit')
    
    # Verificar si streamlit está instalado
    if not os.path.exists(streamlit_path):
        print("Instalando streamlit...")
        subprocess.run(['pip', 'install', 'streamlit'])
    
    # Ejecutar la aplicación
    try:
        subprocess.run(['streamlit', 'run', 'app.py'], check=True)
    except subprocess.CalledProcessError:
        print("Error al ejecutar streamlit. Asegúrate de que app.py existe y streamlit está instalado correctamente")
    except FileNotFoundError:
        print("No se encontró streamlit. Intenta instalarlo manualmente con: pip install streamlit")

if __name__ == "__main__":
    run_app()
    