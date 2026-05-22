import os
import uuid
import tempfile
import subprocess
import shutil
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# path ke folder utilitas TTS (coqui_utils berada di level repo, satu folder di atas `app`)
COQUI_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "coqui_utils"))

# probe likely locations for model and config
_COQUI_MODEL_CANDIDATES = [
    os.path.join(COQUI_DIR, "checkpoint_1260000-inference.pth"),
    os.path.join(COQUI_DIR, "model.pth"),
]

_COQUI_CONFIG_CANDIDATES = [
    os.path.join(COQUI_DIR, "config.json"),
]

# pick first existing candidate or default to first candidate path
COQUI_MODEL_PATH = next((p for p in _COQUI_MODEL_CANDIDATES if os.path.isfile(p)), _COQUI_MODEL_CANDIDATES[0])
COQUI_CONFIG_PATH = next((p for p in _COQUI_CONFIG_CANDIDATES if os.path.isfile(p)), _COQUI_CONFIG_CANDIDATES[0])

# TODO: Tentukan nama speaker yang digunakan
# Pilih nama speaker yang sesuai dengan isi file speakers.pth (misalnya: "wibowo")
COQUI_SPEAKER = "wibowo"

_TTS_EXECUTABLE = shutil.which("tts") or os.path.join(os.path.dirname(sys.executable), "tts")

def transcribe_text_to_speech(text: str) -> str:
    """
    Fungsi untuk mengonversi teks menjadi suara menggunakan TTS engine yang ditentukan.
    Args:
        text (str): Teks yang akan diubah menjadi suara.
    Returns:
        str: Path ke file audio hasil konversi.
    """
    # ensure model and config files exist before attempting synthesis
    if not os.path.isfile(COQUI_MODEL_PATH):
        return f"[ERROR] Coqui TTS model file not found: {COQUI_MODEL_PATH}"
    if not os.path.isfile(COQUI_CONFIG_PATH):
        return f"[ERROR] Coqui TTS config file not found: {COQUI_CONFIG_PATH}"

    path = _tts_with_coqui(text)
    return path

# === ENGINE 1: Coqui TTS ===
def _tts_with_coqui(text: str) -> str:
    tmp_dir = tempfile.gettempdir()
    output_path = os.path.join(tmp_dir, f"tts_{uuid.uuid4()}.wav")

    # jalankan Coqui TTS dengan subprocess
    cmd = [
        _TTS_EXECUTABLE,
        "--text", text,
        "--model_path", COQUI_MODEL_PATH,
        "--config_path", COQUI_CONFIG_PATH,
        "--speaker_idx", COQUI_SPEAKER,
        "--out_path", output_path
    ]

    if not os.path.isfile(_TTS_EXECUTABLE):
        return f"[ERROR] TTS executable not found: {_TTS_EXECUTABLE}"
    
    try:
        subprocess.run(cmd, check=True, cwd=COQUI_DIR)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] TTS subprocess failed: {e}")
        return f"[ERROR] Failed to synthesize speech: {e}"

    return output_path