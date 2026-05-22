import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.llm import generate_response
from app.stt import transcribe_speech_to_text
from app.tts import transcribe_text_to_speech

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "Start Service is running"}


@app.post("/voice-chat")
async def voice_chat(file: UploadFile = File(...)):
    audio_bytes = await file.read()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    transcript = transcribe_speech_to_text(audio_bytes, file_ext=os.path.splitext(file.filename or "")[1] or ".wav")
    if transcript.startswith("[ERROR]"):
        raise HTTPException(status_code=500, detail=transcript)

    answer = generate_response(transcript)
    if answer.startswith("[ERROR]"):
        raise HTTPException(status_code=500, detail=answer)

    tts_path = transcribe_text_to_speech(answer)
    if isinstance(tts_path, str) and tts_path.startswith("[ERROR]"):
        raise HTTPException(status_code=500, detail=tts_path)

    if not os.path.exists(tts_path):
        raise HTTPException(status_code=500, detail="TTS output file was not created")

    with open(tts_path, "rb") as audio_file:
        audio_content = audio_file.read()

    return Response(content=audio_content, media_type="audio/wav")