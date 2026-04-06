from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import HTMLResponse
import whisper
import torch
import shutil
import os
from deep_translator import GoogleTranslator

# =========================
# 🔥 MEMORY OPTIMIZATION
# =========================
os.environ["OMP_NUM_THREADS"] = "1"
torch.set_num_threads(1)

app = FastAPI()

# =========================
# 🔥 LAZY LOAD MODEL
# =========================
model = None

def get_model():
    global model
    if model is None:
        print("⚡ Loading Whisper tiny model...")
        model = whisper.load_model("tiny.en")  # lightweight
    return model

# Store transcription
transcription_result = None

# =========================
# 🌐 INDIAN LANGUAGES MAP
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
    "ur": "Urdu"
}

# =========================
# ROOT (UI)
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
    global transcription_result

    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("🎬 Processing video...")

    model_instance = get_model()

    transcription_result = model_instance.transcribe(file_path)

    print("✅ Transcription completed")

    return {"message": "Video processed successfully"}

# =========================
# GENERATE SUBTITLES (WITH TRANSLATION)
# =========================
@app.post("/generate-subtitles/")
async def generate_subtitles(language: str = "en"):
    global transcription_result

    if not transcription_result:
        return {"error": "No transcription found"}

    subtitles = []

    for segment in transcription_result["segments"]:
        text = segment["text"]

        # 🌍 TRANSLATION
        if language != "en":
            try:
                text = GoogleTranslator(source='auto', target=language).translate(text)
            except Exception as e:
                print("⚠️ Translation error:", e)

        subtitles.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": text
        })

    return {"subtitles": subtitles}

# =========================
# WEBSOCKET (LIVE SUBTITLES)
# =========================
@app.websocket("/ws/subtitles")
async def websocket_subtitles(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()

            # format: time:12.3|lang:te
            parts = data.split("|")
            current_time = float(parts[0].split(":")[1])
            language = parts[1].split(":")[1]

            subtitle_text = ""

            if transcription_result:
                for segment in transcription_result["segments"]:
                    if segment["start"] <= current_time <= segment["end"]:
                        subtitle_text = segment["text"]

                        # 🌍 LIVE TRANSLATION
                        if language != "en":
                            try:
                                subtitle_text = GoogleTranslator(
                                    source='auto',
                                    target=language
                                ).translate(subtitle_text)
                            except:
                                pass

                        break

            print(f"⏱ {current_time} → {subtitle_text}")

            await websocket.send_text(subtitle_text)

    except Exception:
        print("🔌 Client disconnected")

# =========================
# DOWNLOAD SRT
# =========================
@app.post("/download-srt/")
async def download_srt(language: str = "en"):
    global transcription_result

    if not transcription_result:
        return {"error": "No subtitles available"}

    os.makedirs("outputs", exist_ok=True)
    srt_path = "outputs/subtitles.srt"

    def format_time(seconds):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(transcription_result["segments"], start=1):
            text = seg["text"]

            # 🌍 TRANSLATE FOR DOWNLOAD
            if language != "en":
                try:
                    text = GoogleTranslator(source='auto', target=language).translate(text)
                except:
                    pass

            f.write(f"{i}\n")
            f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
            f.write(f"{text}\n\n")

    return {"message": "SRT generated", "path": srt_path}

# =========================
# GET LANGUAGES (FOR DROPDOWN)
# =========================
@app.get("/languages")
def get_languages():
    return LANGUAGES