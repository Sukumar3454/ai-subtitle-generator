import whisper
import subprocess
import os

model = whisper.load_model("base")


def extract_audio(video_path: str, output_path: str):
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path,
        "-y"
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    error_output = result.stderr.decode()

    if "does not contain any stream" in error_output:
        raise RuntimeError("No audio stream found in video ❌")

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed:\n{error_output}")


def transcribe_audio(file_path: str):
    audio_path = os.path.join("outputs", "temp_audio.wav")

    os.makedirs("outputs", exist_ok=True)

    extract_audio(file_path, audio_path)

    if not os.path.exists(audio_path):
        raise RuntimeError("Audio extraction failed")

    result = model.transcribe(audio_path)

    return result