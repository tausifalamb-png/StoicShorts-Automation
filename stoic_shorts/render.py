"""Original portrait scene cards, animated rendering, and quality checks."""
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .tts import synthesize, write_srt


def run_command(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr[-2500:]}")
    return result.stdout.strip()


def font(size, bold=False):
    candidates = (
        ["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def wrap_text(draw, text, selected_font, max_width):
    lines, current = [], ""
    for word in str(text).split():
        candidate = (current + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=selected_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def make_scene_card(item, caption, index, total, path):
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    # Original indigo-to-charcoal gradient with restrained gold accents.
    for y in range(height):
        ratio = y / height
        color = (
            int(12 + 12 * ratio),
            int(19 + 10 * ratio),
            int(43 + 28 * ratio),
        )
        draw.line((0, y, width, y), fill=color)

    draw.ellipse((650, 80, 1240, 670), outline=(48, 67, 112), width=5)
    draw.ellipse((760, 190, 1120, 550), outline=(35, 49, 86), width=3)
    draw.rounded_rectangle((62, 70, 1018, 1850), radius=48, outline=(67, 82, 128), width=3)
    draw.rounded_rectangle((105, 130, 330, 142), radius=6, fill=(235, 177, 82))

    draw.text((112, 185), "STOIC PRACTICE", font=font(30, True), fill=(181, 197, 231))
    draw.text((112, 300), f"{index + 1:02d} / {total:02d}", font=font(34, True), fill=(238, 190, 104))

    title_font = font(68, True)
    y = 520
    for line in wrap_text(draw, item["title"].upper(), title_font, 820)[:3]:
        draw.text((112, y), line, font=title_font, fill=(250, 250, 252))
        y += 92

    draw.rounded_rectangle((112, y + 28, 370, y + 39), radius=5, fill=(235, 177, 82))
    y += 165
    caption_font = font(54, True)
    for line in wrap_text(draw, caption, caption_font, 820)[:5]:
        draw.text((112, y), line, font=caption_font, fill=(218, 228, 247))
        y += 82

    draw.text((112, 1640), "PAUSE  •  THINK  •  CHOOSE", font=font(30, True), fill=(238, 190, 104))
    draw.text((112, 1710), "Original Hinglish Stoic reflection", font=font(25), fill=(157, 174, 211))
    image.save(path, quality=95)


def _probe_duration(path):
    value = run_command([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    return float(value)


def build(item, output_dir):
    for binary in ("ffmpeg", "ffprobe"):
        if not shutil.which(binary):
            raise RuntimeError(f"Required executable is missing: {binary}")

    output_dir = Path(output_dir)
    work_dir = output_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    voice = "hi-IN-MadhurNeural"
    audio_path = work_dir / "narration.mp3"
    boundaries = synthesize(item["narration"], audio_path, voice=voice)
    duration = _probe_duration(audio_path)
    if not 30 <= duration <= 60:
        raise RuntimeError(f"Neural narration is {duration:.1f}s; expected 30–60 seconds. Regenerate the script.")

    subtitle_path = work_dir / "captions.srt"
    cue_count = write_srt(boundaries, subtitle_path)
    if cue_count < 5:
        raise RuntimeError("Too few timed subtitle cues; refusing to publish an under-captioned video.")

    scene_paths = []
    for index, caption in enumerate(item["scenes"]):
        scene_path = work_dir / f"scene-{index + 1:02d}.png"
        make_scene_card(item, caption, index, len(item["scenes"]), scene_path)
        scene_paths.append(scene_path)

    # The concat demuxer holds each original scene card for one third of narration.
    segment_duration = duration / len(scene_paths)
    concat_path = work_dir / "scenes.txt"
    concat_lines = []
    for scene_path in scene_paths:
        concat_lines.append(f"file '{scene_path.resolve()}'")
        concat_lines.append(f"duration {segment_duration:.5f}")
    concat_lines.append(f"file '{scene_paths[-1].resolve()}'")
    concat_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    video_path = output_dir / "short.mp4"
    subtitle_filter = (
        f"subtitles=filename='{subtitle_path.resolve()}':"
        "force_style='FontName=Noto Sans Devanagari,FontSize=48,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H0010182B,"
        "BorderStyle=1,Outline=4,Shadow=1,Alignment=2,MarginV=300'"
    )
    video_filter = (
        "fps=30,scale=1080:1920,"
        "zoompan=z='min(zoom+0.00018,1.06)':d=1:s=1080x1920:fps=30,"
        + subtitle_filter
    )
    run_command([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path),
        "-i", str(audio_path), "-t", f"{duration:.3f}",
        "-vf", video_filter, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "192k",
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-movflags", "+faststart", "-shortest", str(video_path),
    ])

    thumbnail_path = output_dir / "thumbnail.png"
    shutil.copy2(scene_paths[0], thumbnail_path)
    (output_dir / "captions.srt").write_text(subtitle_path.read_text(encoding="utf-8"), encoding="utf-8")
    (output_dir / "script.txt").write_text(
        f"{item['title']}\n\n{item['narration']}\n\nEditorial note: {item['source']}\n",
        encoding="utf-8",
    )

    metadata = {
        "title": item["title"] + " | Stoic Wisdom #shorts",
        "description": (
            item["hook"] + "\n\n"
            "Original Hinglish reflection on practical Stoicism. "
            "This is an educational interpretation, not a direct quotation.\n\n"
            "#stoicism #selfdiscipline #wisdom #hinglish #shorts"
        ),
        "tags": ["stoicism", "stoic philosophy", "self discipline", "hinglish", "wisdom", "shorts"],
        "categoryId": "22",
        "defaultLanguage": "hi",
        "defaultAudioLanguage": "hi",
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    probe = json.loads(run_command([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video_path)
    ]))
    video_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
    audio_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)
    if not video_stream or not audio_stream:
        raise RuntimeError("Rendered MP4 is missing a video or audio stream.")
    if (video_stream["width"], video_stream["height"]) != (1080, 1920):
        raise RuntimeError("Rendered MP4 is not 1080x1920 portrait.")
    if video_stream["codec_name"] != "h264" or audio_stream["codec_name"] != "aac":
        raise RuntimeError("Rendered MP4 has unexpected codecs.")
    final_duration = float(probe["format"]["duration"])
    if not 30 <= final_duration <= 60 or abs(final_duration - duration) > 2:
        raise RuntimeError(f"Final render duration check failed: {final_duration:.1f}s.")

    checks = {
        "duration_seconds": round(final_duration, 2),
        "width": 1080,
        "height": 1920,
        "video_codec": video_stream["codec_name"],
        "audio_codec": audio_stream["codec_name"],
        "subtitle_cues": cue_count,
        "tts_voice": voice,
        "captions_burned_in": True,
    }
    return video_path, metadata, checks
