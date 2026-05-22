import os
import uuid
import tempfile
import subprocess
import importlib
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# path ke folder utilitas TTS
COQUI_DIR = os.path.join(BASE_DIR, "coqui_utils")

# Jalur model dan konfigurasi Coqui dapat dioverride lewat environment.
COQUI_MODEL_PATH = os.getenv(
    "COQUI_MODEL_PATH",
    os.path.join(COQUI_DIR, "checkpoint_1260000-inference.pth"),
)
COQUI_CONFIG_PATH = os.getenv(
    "COQUI_CONFIG_PATH",
    os.path.join(COQUI_DIR, "config.json"),
)
COQUI_SPEAKER = os.getenv("COQUI_SPEAKER", "wibowo")
TTS_ENGINE = os.getenv("TTS_ENGINE", "auto").lower()

def transcribe_text_to_speech(text: str) -> str:
    """
    Fungsi untuk mengonversi teks menjadi suara menggunakan TTS engine yang ditentukan.
    Args:
        text (str): Teks yang akan diubah menjadi suara.
    Returns:
        str: Path ke file audio hasil konversi.
    """
    if TTS_ENGINE == "pyttsx3":
        return _tts_with_pyttsx3(text)

    if TTS_ENGINE == "coqui":
        return _tts_with_coqui(text)

    coqui_result = _tts_with_coqui(text)
    if not coqui_result.startswith("[ERROR]"):
        return coqui_result

    return _tts_with_pyttsx3(text)

# === ENGINE 1: Coqui TTS ===
def _tts_with_coqui(text: str) -> str:
    tmp_dir = tempfile.gettempdir()
    output_path = os.path.join(tmp_dir, f"tts_{uuid.uuid4()}.wav")

    if not os.path.exists(COQUI_MODEL_PATH):
        return f"[ERROR] Coqui model not found: {COQUI_MODEL_PATH}"

    if not os.path.exists(COQUI_CONFIG_PATH):
        return f"[ERROR] Coqui config not found: {COQUI_CONFIG_PATH}"

    # jalankan Coqui TTS dengan subprocess
    cmd = [
        "tts",
        "--text", text,
        "--model_path", COQUI_MODEL_PATH,
        "--config_path", COQUI_CONFIG_PATH,
        "--speaker_idx", COQUI_SPEAKER,
        "--out_path", output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] TTS subprocess failed: {e}")
        return "[ERROR] Failed to synthesize speech"
    except FileNotFoundError:
        return "[ERROR] TTS executable not found. Install coqui-tts CLI or add it to PATH."

    return output_path


def _tts_with_pyttsx3(text: str) -> str:
    tmp_dir = tempfile.gettempdir()
    output_path = os.path.join(tmp_dir, f"tts_{uuid.uuid4()}.wav")

    try:
        pyttsx3 = importlib.import_module("pyttsx3")
        engine = pyttsx3.init()
        engine.save_to_file(text, output_path)
        engine.runAndWait()
    except Exception as error:
        return f"[ERROR] pyttsx3 failed: {error}"

    if not os.path.exists(output_path):
        return "[ERROR] TTS output file was not created"

    return output_path
