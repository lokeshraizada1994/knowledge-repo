import re
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
    # Use oEmbed — no API key needed
    resp = requests.get(
        f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
        timeout=10,
    )
    if resp.status_code == 200:
        data = resp.json()
        return {
            "title": data.get("title", "Untitled Video"),
            "author": data.get("author_name"),
        }
    return {"title": "Untitled Video", "author": None}


def extract_youtube(url: str) -> dict:
    video_id = _extract_video_id(url)
    meta = _get_video_metadata(video_id)

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join(t["text"] for t in transcript_list)
    except Exception:
        # Try auto-generated captions
        try:
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript_obj = transcripts.find_generated_transcript(["en"])
            transcript_list = transcript_obj.fetch()
            transcript = " ".join(t["text"] for t in transcript_list)
        except Exception as e:
            transcript = f"[Transcript unavailable: {e}]"

    word_count = len(transcript.split())
    duration_minutes = round(word_count / 150)  # ~150 wpm for video

    return {
        "type": "youtube",
        "title": meta["title"],
        "author": meta["author"],
        "content": transcript,
        "source_url": url,
        "duration": f"~{duration_minutes} min watch",
    }
