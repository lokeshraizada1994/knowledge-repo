import re
import os
import tempfile
from youtube_transcript_api import YouTubeTranscriptApi
import requests


def _extract_video_id(url: str) -> str:
    patterns = [
        r"youtube\.com/watch\?v=([\w-]+)",
        r"youtu\.be/([\w-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract video ID from: {url}")


def _get_video_metadata(video_id: str) -> dict:
    resp = requests.get(
        f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
        timeout=10,
    )
    if resp.status_code == 200:
        data = resp.json()
        return {"title": data.get("title", "Untitled Video"), "author": data.get("author_name")}
    return {"title": "Untitled Video", "author": None}


def _transcript_via_api(video_id: str) -> str | None:
    """Try youtube-transcript-api (manual captions then auto-generated)."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(t["text"] for t in transcript_list)
    except Exception:
        pass
    try:
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        obj = transcripts.find_generated_transcript(["en"])
        return " ".join(t["text"] for t in obj.fetch())
    except Exception:
        pass
    return None


def _transcript_via_ytdlp(url: str) -> str | None:
    """
    Fallback: download audio with yt-dlp and transcribe with faster-whisper.
    Used when YouTube disables/blocks transcripts.
    """
    try:
        import yt_dlp
        from faster_whisper import WhisperModel

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.%(ext)s")
            ydl_opts = {
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": audio_path,
                "quiet": True,
                "no_warnings": True,
                "extract_audio": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded = ydl.prepare_filename(info).replace(".%(ext)s", "")

            # Find the downloaded file
            audio_file = None
            for f in os.listdir(tmpdir):
                audio_file = os.path.join(tmpdir, f)
                break

            if not audio_file:
                return None

            print("[YouTube] Transcribing audio with Whisper...")
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_file, beam_size=5)
            transcript = " ".join(seg.text for seg in segments)
            return transcript if len(transcript) > 100 else None

    except Exception as e:
        print(f"[YouTube] yt-dlp/Whisper fallback failed: {e}")
        return None


def extract_youtube(url: str) -> dict:
    video_id = _extract_video_id(url)
    meta = _get_video_metadata(video_id)

    # Try transcript API first (fast)
    transcript = _transcript_via_api(video_id)

    # Fallback to yt-dlp + Whisper if transcript unavailable
    if not transcript or transcript.startswith("["):
        print("[YouTube] Transcript API failed, trying yt-dlp + Whisper...")
        transcript = _transcript_via_ytdlp(url)

    if not transcript:
        transcript = None  # signals complete failure to main.py

    word_count = len(transcript.split()) if transcript else 0
    duration_minutes = round(word_count / 150) if word_count else 0

    return {
        "type": "youtube",
        "title": meta["title"],
        "author": meta["author"],
        "content": transcript,
        "source_url": url,
        "duration": f"~{duration_minutes} min watch" if duration_minutes else None,
    }
