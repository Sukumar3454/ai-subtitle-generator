from fastapi import FastAPI, UploadFile, File, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from services.speech_to_text import transcribe_audio
from services.translator import translate_text
from utils.file_handler import save_upload_file, save_srt

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 Global variables
latest_video_path = None
latest_result = None


# ✅ Root endpoint
@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


# ✅ Upload video + process
@app.post("/upload-video/")
async def upload_video(file: UploadFile = File(...)):
    global latest_video_path, latest_result

    file_path = save_upload_file(file, file.filename)

    print("🎬 Processing video...")

    latest_video_path = file_path
    latest_result = transcribe_audio(file_path)

    print("✅ Transcription completed")

    return {"message": "Video uploaded & processed"}


# ✅ Generate subtitles (Swagger)
@app.post("/generate-subtitles/")
async def generate_subtitles(file: UploadFile = File(...), language: str = "en"):
    file_path = save_upload_file(file, file.filename)

    result = transcribe_audio(file_path)
    original_text = result["text"]

    translated_text = translate_text(original_text, language)

    return {
        "original_text": original_text,
        "translated_text": translated_text
    }


# ✅ Download SRT
@app.post("/download-srt/")
async def download_srt(file: UploadFile = File(...)):
    file_path = save_upload_file(file, file.filename)

    result = transcribe_audio(file_path)

    # ✅ FIXED: pass filename
    srt_path = save_srt(result, "subtitles.srt")

    return FileResponse(
        srt_path,
        media_type="application/octet-stream",
        filename="subtitles.srt"
    )


# ✅ 🔥 REAL-TIME SUBTITLES (FINAL WORKING VERSION)
@app.websocket("/ws/subtitles")
async def websocket_subtitles(websocket: WebSocket):
    await websocket.accept()

    global latest_result

    try:
        while True:
            data = await websocket.receive_text()

            # Example: "time:12.5|lang:te"
            parts = data.split("|")

            current_time = 0
            lang = "en"

            for p in parts:
                if "time:" in p:
                    current_time = float(p.split(":")[1])
                if "lang:" in p:
                    lang = p.split(":")[1]

            subtitle = ""

            if latest_result:
                for seg in latest_result["segments"]:
                    # ✅ FIX: time tolerance
                    if seg["start"] - 0.5 <= current_time <= seg["end"] + 0.5:
                        subtitle = seg["text"]
                        break

            # 🔍 Debug (important)
            print(f"⏱ Time: {current_time} | Subtitle: {subtitle}")

            translated = translate_text(subtitle, lang) if subtitle else ""

            await websocket.send_text(translated)

    except WebSocketDisconnect:
        print("🔌 Client disconnected")

    except Exception as e:
        print("❌ WebSocket error:", e)