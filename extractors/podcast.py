import os
import tempfile
import requests
import whisper


def extract_podcast(url: str = None, attachment: dict = None) -> dict:
    model = whisper.load_model("base")  # ~140MB, runs on CPU

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

        if attachment:
            import base64
            audio_data = base64.b64decode(attachment["data"])
            tmp.write(audio_data)
            filename = attachment.get("filename", "podcast")
        elif url:
            resp = requests.get(url, timeout=60, stream=True)
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            filename = url.split("/")[-1].split("?")[0] or "podcast"
        else:
            raise ValueError("No audio source provided")

    try:
        result = model.transcribe(tmp_path, language="en", fp16=False)
        transcript = result["text"].strip()
        duration_seconds = result.get("duration", 0)
        duration_minutes = round(duration_seconds / 60)
    finally:
        os.unlink(tmp_path)

    return {
        "type": "podcast",
        "title": filename.replace("-", " ").replace("_", " ").rsplit(".", 1)[0].title(),
        "author": None,
        "content": transcript,
        "source_url": url,
        "duration": f"~{duration_minutes} min listen",
    }
