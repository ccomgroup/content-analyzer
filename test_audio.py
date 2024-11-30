from pydub import AudioSegment
import os

def test_pydub():
    print("🔍 Verificando configuración de audio...")
    try:
        # Crear un pequeño archivo de prueba
        silence = AudioSegment.silent(duration=1000)  # 1 segundo de silencio
        test_path = "test.mp3"
        silence.export(test_path, format="mp3")
        
        print("✅ pydub y ffmpeg están configurados correctamente")
        
        # Limpiar archivo de prueba
        os.remove(test_path)
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_pydub() 