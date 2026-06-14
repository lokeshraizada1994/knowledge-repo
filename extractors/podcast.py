import os
import tempfile
import requests
from faster_whisper import WhisperModel

# Streaming platforms that need yt-dlp to download
_YTDLP_DOMAINS = {"soundcloud.com", "open.spotify.com", "podcasts.apple.com", "anchor.fm"}


def _needs_ytdlp(url: str) -> bool:
    if not url:
        return False
    domain = url.split("//")[-1].split("/")[0].replace("www.", "")
    return domain in _YTDLP_DOMAINS


def _download_via_ytdlp(url: str, tmp_path: str) -> str:
    """Download audio from streaming platforms using yt-dlp. Returns title."""
    import yt_dlp
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": tmp_path.replace(".mp3", ".%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get("title") or info.get("track") or "Podcast"


def extract_podcast(url: str = None, attachment: dict = None) -> dict:
    model = WhisperModel("base", device="cpu", compute_type="int8")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name

        if attachment:
            import base64
            audio_data = base64.b64decode(attachment["data"])
            tmp.write(audio_data)
            filename = attachment.get("filename", "podcast")
        elif url and _needs_ytdlp(url):
            filename = _download_via_ytdlp(url, tmp_path)
            # yt-dlp writes its own file; find it
            base = tmp_path.replace(".mp3", "")
            for ext in [".mp3", ".m4a", ".webm", ".opus"]:
                if os.path.exists(base + ext):
                    tmp_path = base + ext
                    break
        elif url:
            resp = requests.get(url, timeout=60, stream=True)
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            filename = url.split("/")[-1].split("?")[0] or "podcast"
        else:
            raise ValueError("No audio source provided")

    try:
        segments, info = model.transcribe(tmp_path, language="en")
        transcript = " ".join(seg.text for seg in segments).strip()
        duration_minutes = round(info.duration / 60)
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
