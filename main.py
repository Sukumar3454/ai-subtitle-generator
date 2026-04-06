from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import HTMLResponse
import whisper
import torch
import shutil
import os
from deep_translator import GoogleTranslator

# =========================
# PERFORMANCE SETTINGS
# =========================
os.environ["OMP_NUM_THREADS"] = "1"
torch.set_num_threads(1)

app = FastAPI()

model = None
transcription_result = None
translated_segments = None  # ✅ STORE TRANSLATED DATA

def get_model():
    global model
    if model is None:
        print("⚡ Loading Whisper tiny model...")
        model = whisper.load_model("tiny.en")
    return model

# =========================
# 🇮🇳 ALL INDIAN LANGUAGES
# =========================
LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
    "ur": "Urdu",
    "sd": "Sindhi",
    "sa": "Sanskrit",
    "ne": "Nepali",
    "kok": "Konkani",
    "mai": "Maithili",
    "bho": "Bhojpuri",
    "doi": "Dogri",
    "mni": "Manipuri"
}

# =========================
# ROOT
# =========================
@app.get("/", response_class=HTMLResponse)
def serve_ui():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

# =========================
# UPLOAD VIDEO
# =========================
@app.post("/upload-video/")
async def upload_video(file: UploadFile = File(...)):
    global transcription_result, translated_segments

    translated_segments = None  # reset

    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("🎬 Processing video...")

    model_instance = get_model()
    transcription_result = model_instance.transcribe(file_path)

    print("✅ Transcription done")

    return {"message": "done"}

# =========================
# GENERATE TRANSLATION ONCE
# =========================
@app.post("/generate-subtitles/")
async def generate_subtitles(language: str = "en"):
    global transcription_result, translated_segments

    if not transcription_result:
        return {"error": "No transcription"}

    print(f"🌍 Translating to {language}...")

    translated_segments = []

    for seg in transcription_result["segments"]:
        text = seg["text"]

        if language != "en":
            try:
                text = GoogleTranslator(source='auto', target=language).translate(text)
            except:
                pass

        translated_segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": text
        })

    print("✅ Translation completed")

    return {"message": "translated"}

# =========================
# WEBSOCKET (USE TRANSLATED DATA)
# =========================
@app.websocket("/ws/subtitles")
async def websocket_subtitles(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            current_time = float(data.split(":")[1])

            subtitle = ""

            # ✅ USE TRANSLATED IF AVAILABLE
            source = translated_segments if translated_segments else transcription_result["segments"]

            for seg in source:
                if seg["start"] <= current_time <= seg["end"]:
                    subtitle = seg["text"]
                    break

            await websocket.send_text(subtitle)

    except:
        print("🔌 Client disconnected")

# =========================
# LANGUAGES API
# =========================
@app.get("/languages")
def get_languages():
    return LANGUAGES