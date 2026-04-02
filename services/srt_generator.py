def format_time(seconds: float):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"


def generate_srt(segments):
    srt_content = ""

    for i, seg in enumerate(segments):
        start = format_time(seg['start'])
        end = format_time(seg['end'])
        text = seg['text']

        srt_content += f"{i+1}\n{start} --> {end}\n{text}\n\n"

    return srt_content