# StoicShorts Automation

A private-first Hinglish YouTube Shorts generator using Python, eSpeak NG, Pillow, FFmpeg, and GitHub Actions.

## Automation
No separate app is required: use the repository's **Actions** tab. The daily workflow runs at 13:30 UTC = 19:00 Asia/Kolkata. Enable Actions in the repository if prompted.

## YouTube OAuth setup
In Google Cloud Console, enable YouTube Data API v3, configure OAuth consent, create an OAuth Client ID, and authorize the channel owner with scope `https://www.googleapis.com/auth/youtube.upload`. Store the resulting credentials only as repository Actions secrets:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Never commit or paste secrets into chat. Google OAuth consent/testing restrictions can affect authorization and refresh-token lifetime.

## Run
The workflow builds a 1080x1920 MP4, checks audio/video/duration, and uploads it as **PRIVATE only** if all three secrets exist. Without secrets it generates a review artifact and skips upload. Download the artifact from the Actions run.

Open-source tooling does not mean unlimited free compute: GitHub Actions usage limits apply. eSpeak NG voice quality is synthetic/robotic. Add original scripts in `content/scripts.json`. Tests: `python -m unittest discover -s tests -v`.

The workflow never makes a video public. Review each upload manually in YouTube Studio before publishing. Repetitive templated content is not a monetization guarantee.
