"""Neural Hindi narration and word-timed subtitle generation.

Uses the edge-tts community client with Microsoft's online read-aloud service.
This is a network dependency, not a contractual or guaranteed free API.
"""
import asyncio
from pathlib import Path

DEFAULT_VOICE = "hi-IN-MadhurNeural"


async def _stream_audio(text, output_path, voice):
    import edge_tts

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate="+0%",
        volume="+0%",
        pitch="+0Hz",
        boundary="WordBoundary",
    )
    boundaries = []
    output_path = Path(output_path)
    with output_path.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append({
                    "offset": int(chunk["offset"]),
                    "duration": int(chunk["duration"]),
                    "text": str(chunk["text"]),
                })
    if not output_path.exists() or output_path.stat().st_size < 1024:
        raise RuntimeError("Hindi neural TTS returned an empty or invalid audio file.")
    if not boundaries:
        raise RuntimeError("Hindi neural TTS returned no word timings; refusing to render unsynchronised captions.")
    return boundaries


def synthesize(text, output_path, voice=DEFAULT_VOICE):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Narration text is empty.")
    try:
        return asyncio.run(_stream_audio(text.strip(), output_path, voice))
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Hindi neural voice generation failed: {type(exc).__name__}: {exc}") from exc


def _srt_time(milliseconds):
    milliseconds = max(0, int(milliseconds))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def write_srt(boundaries, output_path, words_per_caption=4):
    """Write short, readable caption groups from Edge TTS word timings."""
    if not boundaries:
        raise ValueError("Cannot create subtitles without word timings.")
    cues = []
    group = []
    for item in boundaries:
        word = str(item.get("text", "")).strip()
        if not word:
            continue
        start_ms = int(item["offset"]) / 10_000
        end_ms = (int(item["offset"]) + int(item["duration"])) / 10_000
        group.append((word, start_ms, end_ms))
        if len(group) >= words_per_caption or word.endswith((".", "?", "!", "।", "…")):
            cues.append(group)
            group = []
    if group:
        cues.append(group)

    lines = []
    for index, cue in enumerate(cues, 1):
        start = max(0, cue[0][1] - 30)
        end = max(start + 250, cue[-1][2] + 180)
        text = " ".join(part[0] for part in cue)
        lines.extend([str(index), f"{_srt_time(start)} --> {_srt_time(end)}", text, ""])
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return len(cues)
