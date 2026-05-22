import os
import uuid
import tempfile
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

# path ke folder utilitas STT
WHISPER_DIR = os.path.join(PROJECT_DIR, "whisper.cpp")

# Path binary whisper-cli dan model dapat dioverride lewat environment.
WHISPER_BINARY = os.getenv(
    "WHISPER_BINARY",
    os.path.join(WHISPER_DIR, "build", "bin", "whisper-cli"),
)

WHISPER_MODEL_PATH = os.getenv(
    "WHISPER_MODEL_PATH",
    os.path.join(WHISPER_DIR, "models", "ggml-large-v3-turbo.bin"),
)

FFMPEG_BINARY = os.getenv("FFMPEG_BINARY", "ffmpeg")

WHISPER_LIBRARY_DIRS = [
    os.path.join(WHISPER_DIR, "build", "src"),
    os.path.join(WHISPER_DIR, "build", "ggml", "src"),
]

WHISPER_LIBRARY_SYMLINKS = [
    (
        os.path.join(WHISPER_DIR, "build", "src", "libwhisper.so.1"),
        os.path.join(WHISPER_DIR, "build", "src", "libwhisper.so.1.8.4"),
    ),
    (
        os.path.join(WHISPER_DIR, "build", "ggml", "src", "libggml.so.0"),
        os.path.join(WHISPER_DIR, "build", "ggml", "src", "libggml.so.0.11.1"),
    ),
    (
        os.path.join(WHISPER_DIR, "build", "ggml", "src", "libggml-cpu.so.0"),
        os.path.join(WHISPER_DIR, "build", "ggml", "src", "libggml-cpu.so.0.11.1"),
    ),
    (
        os.path.join(WHISPER_DIR, "build", "ggml", "src", "libggml-base.so.0"),
        os.path.join(WHISPER_DIR, "build", "ggml", "src", "libggml-base.so.0.11.1"),
    ),
]


def _ensure_whisper_library_links() -> None:
    for link_path, target_path in WHISPER_LIBRARY_SYMLINKS:
        if not os.path.exists(target_path):
            continue

        if os.path.islink(link_path) or os.path.exists(link_path):
            continue

        try:
            os.symlink(os.path.basename(target_path), link_path)
        except FileExistsError:
            continue


def _transcode_audio_to_wav(source_path: str, target_path: str) -> str:
    if not os.path.exists(source_path):
        return f"[ERROR] Audio source file not found: {source_path}"

    if not shutil.which(FFMPEG_BINARY):
        return f"[ERROR] FFmpeg executable not found: {FFMPEG_BINARY}"

    cmd = [
        FFMPEG_BINARY,
        "-y",
        "-i",
        source_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        target_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else ""
        stdout = e.stdout.strip() if e.stdout else ""
        details = stderr or stdout or str(e)
        return f"[ERROR] FFmpeg failed: {details}"

    return target_path

def transcribe_speech_to_text(file_bytes: bytes, file_ext: str = ".wav") -> str:
    """
    Transkrip file audio menggunakan whisper.cpp CLI
    Args:
        file_bytes (bytes): Isi file audio
        file_ext (str): Ekstensi file, default ".wav"
    Returns:
        str: Teks hasil transkripsi
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _ensure_whisper_library_links()

        source_audio_path = os.path.join(tmpdir, f"{uuid.uuid4()}{file_ext}")
        wav_audio_path = os.path.join(tmpdir, f"{uuid.uuid4()}.wav")
        output_base = os.path.join(tmpdir, "transcription")
        result_path = f"{output_base}.txt"

        if not os.path.exists(WHISPER_BINARY):
            return f"[ERROR] Whisper binary not found: {WHISPER_BINARY}"

        if not os.access(WHISPER_BINARY, os.X_OK):
            return f"[ERROR] Whisper binary is not executable: {WHISPER_BINARY}"

        if not os.path.exists(WHISPER_MODEL_PATH):
            return f"[ERROR] Whisper model not found: {WHISPER_MODEL_PATH}"

        # simpan audio ke file temporer
        with open(source_audio_path, "wb") as f:
            f.write(file_bytes)

        transcoded_audio_path = _transcode_audio_to_wav(source_audio_path, wav_audio_path)
        if transcoded_audio_path.startswith("[ERROR]"):
            return transcoded_audio_path

        # jalankan whisper.cpp dengan subprocess
        cmd = [
            WHISPER_BINARY,
            "-m", WHISPER_MODEL_PATH,
            "-f", transcoded_audio_path,
            "-otxt",
            "-of", output_base,
        ]

        env = os.environ.copy()
        library_path_parts = [path for path in WHISPER_LIBRARY_DIRS if os.path.isdir(path)]
        existing_library_path = env.get("LD_LIBRARY_PATH")
        if existing_library_path:
            library_path_parts.append(existing_library_path)
        if library_path_parts:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(library_path_parts)

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else ""
            stdout = e.stdout.strip() if e.stdout else ""
            details = stderr or stdout or str(e)
            return f"[ERROR] Whisper failed: {details}"
        except FileNotFoundError:
            return "[ERROR] Whisper executable not found. Build whisper.cpp first or set WHISPER_BINARY."
        
        # baca hasil transkripsi
        try:
            with open(result_path, "r", encoding="utf-8") as result_file:
                return result_file.read()
        except FileNotFoundError:
            return "[ERROR] Transcription file not found"