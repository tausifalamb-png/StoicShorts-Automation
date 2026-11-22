"""Daily quality-first Stoic Shorts pipeline.

A run either creates a validated original script, neural narration, timed captions,
and a portrait MP4, or exits with an error. It never silently uses the old script bank.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .llm import generate_script
from .render import build

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube.upload"


def read_history():
    if not HISTORY.exists():
        return {"videos": []}
    try:
        value = json.loads(HISTORY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot read history file safely: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("videos"), list):
        raise RuntimeError("History file has an invalid schema; refusing to risk duplicate uploads.")
    return value


def validate_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Date must use YYYY-MM-DD.") from exc
    return value


def assert_not_already_uploaded(day, history, digest):
    for entry in history["videos"]:
        if entry.get("date") == day and entry.get("youtube_video_id"):
            raise RuntimeError(
                f"A YouTube Short was already uploaded for {day} "
                f"(video ID {entry['youtube_video_id']}). Daily upload limit is one."
            )
    recent_hashes = {
        entry.get("content_hash")
        for entry in history["videos"][-30:]
        if entry.get("content_hash")
    }
    if digest in recent_hashes:
        raise RuntimeError("This narration duplicates a recent upload; refusing to publish recycled content.")


def upload_private(video_path, metadata):
    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise RuntimeError("Missing YouTube OAuth secrets: " + ", ".join(missing))

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as google_build
    from googleapiclient.http import MediaFileUpload

    credentials = Credentials(
        None,
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip(),
        scopes=[YOUTUBE_SCOPE],
    )
    credentials.refresh(Request())
    youtube = google_build("youtube", "v3", credentials=credentials, cache_discovery=False)

    body = {
        "snippet": {
            "title": metadata["title"][:100],
            "description": metadata["description"][:5000],
            "tags": metadata["tags"][:20],
            "categoryId": metadata["categoryId"],
            "defaultLanguage": metadata["defaultLanguage"],
            "defaultAudioLanguage": metadata["defaultAudioLanguage"],
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=8 * 1024 * 1024,
        resumable=True,
    )
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("YouTube did not return a video ID after upload.")
    return video_id


def oauth_setup():
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_file = ROOT / "client_secret.json"
    if not client_file.exists():
        raise RuntimeError(
            "Place your own Google OAuth Desktop client JSON at client_secret.json. "
            "Never commit or share this file."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(client_file), [YOUTUBE_SCOPE])
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    if not credentials.refresh_token:
        raise RuntimeError("Google did not return a refresh token. Check OAuth consent and try again.")
    secret_values = {
        "YOUTUBE_CLIENT_ID": credentials.client_id,
        "YOUTUBE_CLIENT_SECRET": credentials.client_secret,
        "YOUTUBE_REFRESH_TOKEN": credentials.refresh_token,
    }
    private_dir = ROOT / ".oauth"
    private_dir.mkdir(exist_ok=True)
    private_file = private_dir / "github-actions-secrets.json"
    private_file.write_text(json.dumps(secret_values, indent=2), encoding="utf-8")
    try:
        private_file.chmod(0o600)
    except OSError:
        pass
    print(f"OAuth values saved locally to {private_file}.")
    print("Copy each value into the matching GitHub Actions repository secret.")
    print("Do not paste these values into chat, issues, commits, or screenshots.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build one private-first Stoic YouTube Short.")
    parser.add_argument("--output", default="output")
    parser.add_argument(
        "--date",
        default=datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d"),
        type=validate_date,
    )
    parser.add_argument("--upload", action="store_true", help="Upload to YouTube with privacyStatus=private.")
    parser.add_argument("--oauth-setup", action="store_true", help="Complete local YouTube OAuth setup.")
    args = parser.parse_args(argv)

    if args.oauth_setup:
        oauth_setup()
        return 0

    history = read_history()
    item = generate_script(args.date, history)
    digest = hashlib.sha256(item["narration"].encode("utf-8")).hexdigest()
    assert_not_already_uploaded(args.date, history, digest)

    video_path, metadata, validation = build(item, args.output)
    video_id = upload_private(video_path, metadata) if args.upload else None

    history["videos"].append({
        "date": args.date,
        "script_id": item["id"],
        "title": item["title"],
        "content_hash": digest,
        "youtube_video_id": video_id,
        "privacy_status": "private" if video_id else "not_uploaded",
        "validation": validation,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    history["videos"] = history["videos"][-180:]
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "script_id": item["id"],
        "youtube_video_id": video_id,
        "privacy_status": "private" if video_id else "not_uploaded",
        "validation": validation,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
