from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import whisper
import torch
import shutil
import os

# ✅ Optimize for low memory (Render friendly)
os.environ["OMP_NUM_THREADS"] = "1"
torch.set_num_threads(1)

app = FastAPI()

# ✅ Load Whisper model (lightweight)
device = "cpu"
model = whisper.load_model("tiny", device=device)

# Store subtitles globally
transcription_result = None

# =========================
# ROOT (Serve UI)
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

    file_path = f"uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print("🎬 Processing video...")

    # ✅ Transcribe video
    transcription_result = model.transcribe(file_path)

    print("✅ Transcription completed")

    return {"message": "Video processed successfully"}

# =========================
# GENERATE SUBTITLES
# =========================
@app.post("/generate-subtitles/")
async def generate_subtitles(language: str = "en"):
    global transcription_result

    if not transcription_result:
        return {"error": "No transcription found"}

    subtitles = []

    for segment in transcription_result["segments"]:
        subtitles.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"]  # ✅ No translation (safe)
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

            # Expected format: time:12.34|lang:te
            parts = data.split("|")
            current_time = float(parts[0].split(":")[1])

            subtitle_text = ""

            if transcription_result:
                for segment in transcription_result["segments"]:
                    if segment["start"] <= current_time <= segment["end"]:
                        subtitle_text = segment["text"]
                        break

            print(f"⏱ Time: {current_time} | Subtitle: {subtitle_text}")

            await websocket.send_text(subtitle_text)

    except Exception as e:
        print("🔌 Client disconnected")

# =========================
# DOWNLOAD SRT
# =========================
@app.post("/download-srt/")
async def download_srt():
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
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            text = seg["text"]

            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    return {"message": "SRT generated", "path": srt_path}