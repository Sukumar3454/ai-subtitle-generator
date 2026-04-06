from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import whisper
import shutil
import os
import asyncio
from googletrans import Translator
import whisper
import torch

app = FastAPI() 
torch.set_num_threads(1)

# ✅ Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ LOAD MODEL (CPU + LOW MEMORY)
device = "cpu"

model = whisper.load_model("tiny")
model = model.to(device)

translator = Translator()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

transcription_result = None


# ✅ Upload Video
@app.post("/upload-video/")
async def upload_video(file: UploadFile = File(...)):
    global transcription_result

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("🎬 Processing video...")

    # Transcribe
    transcription_result = model.transcribe(file_path)

    print("✅ Transcription completed")

    return {"message": "Video uploaded and processed"}


# ✅ Get Subtitle by Time
def get_subtitle_by_time(current_time, language="en"):
    global transcription_result

    if not transcription_result:
        return ""

    for segment in transcription_result["segments"]:
        if segment["start"] <= current_time <= segment["end"]:
            text = segment["text"]

            # 🌍 Translate if needed
            if language != "en":
                try:
                    text = translator.translate(text, dest=language).text
                except:
                    pass

            return text

    return ""


# ✅ WebSocket for LIVE subtitles
@app.websocket("/ws/subtitles")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("🔌 WebSocket connected")

    try:
        while True:
            data = await websocket.receive_text()

            # Expected format: time:12.3|lang:te
            try:
                parts = data.split("|")
                time_part = parts[0].split(":")[1]
                lang_part = parts[1].split(":")[1]

                current_time = float(time_part)
                language = lang_part
            except:
                await websocket.send_text("")
                continue

            subtitle = get_subtitle_by_time(current_time, language)

            print(f"⏱ Time: {current_time:.2f} | Subtitle: {subtitle}")

            await websocket.send_text(subtitle)

            await asyncio.sleep(0.3)

    except:
        print("🔌 Client disconnected")


# ✅ Root API (optional)
@app.get("/")
def home():
    return {"message": "AI Subtitle Generator API running 🚀"}