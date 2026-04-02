import os
import shutil
from fastapi import UploadFile


# ✅ Ensure folders exist
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ✅ Save uploaded file
def save_upload_file(file: UploadFile, filename: str) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return file_path


# ✅ Format time for SRT (HH:MM:SS,ms)
def format_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"


# ✅ Save subtitles as .srt file
def save_srt(result, filename: str) -> str:
    srt_content = ""

    segments = result.get("segments", [])

    for i, seg in enumerate(segments):
        start = format_time(seg["start"])
        end = format_time(seg["end"])
        text = seg["text"].strip()

        srt_content += f"{i+1}\n"
        srt_content += f"{start} --> {end}\n"
        srt_content += f"{text}\n\n"

    file_path = os.path.join(OUTPUT_DIR, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return file_path