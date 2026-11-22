# StoicShorts Automation

A private-first, daily Hinglish Stoicism Shorts pipeline. It generates an original script with Gemini, creates Hindi neural narration, burns word-timed captions into a 1080×1920 video, validates the MP4, and optionally uploads it to YouTube as **PRIVATE**.

## What is automated

1. Gemini 3.8 Flash creates an original script.
2. A second Gemini call reviews and rewrites the draft for accuracy, clarity, originality, and natural Hinglish.
3. Hindi neural narration is generated with the hi-IN-MadhurNeural voice.
4. Word timings are converted into subtitle cues and burned into the video.
5. Three original indigo-and-gold scene cards are rendered with subtle motion.
6. FFprobe checks the MP4 dimensions, codecs, audio/video streams, and 30–60 second duration.
7. If YouTube OAuth secrets are present, the video is uploaded with privacyStatus=private. Otherwise, the run creates a review artifact only.
8. A history file prevents duplicate narration and more than one YouTube upload per date.

## Important service and cost notes

- **LLM:** Gemini 3.8 Flash is the only model. Two API calls are used per Short. Free-tier limits are limited and can change; the workflow stops on quota errors rather than silently switching to a weaker model or recycled script. Check the live [Gemini API pricing and limits](https://ai.google.dev/gemini-api/docs/pricing).
- **Data privacy:** Google states that content submitted on the free tier may be used to improve its products. Do not put private, personal, or sensitive information in prompts. This project sends only channel themes and recent public video titles.
- **Voice:** edge-tts is a community Python client that connects to the online Microsoft Edge read-aloud service. It is not a guaranteed or contractual free API. It requires internet access and may change or become unavailable. If it fails, the workflow stops instead of reverting to robotic eSpeak.
- **Compute:** GitHub Actions has usage limits. This is not unlimited free hosting.
- **Assets:** Scene cards are original procedural graphics. No stock footage or unlicensed music is downloaded or embedded. The current format is animated typography/scene cards, not cinematic stock-footage editing.
- **Human review:** AI editorial review is not independent fact-checking. Review the script and video before any public release. No system can guarantee views or monetization.

## 1. Configure Gemini

1. Obtain an API key from [Google AI Studio](https://aistudio.google.com/api-keys), subject to Google's current account and age requirements.
2. In this repository open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add:
   - Name: GEMINI_API_KEY
   - Value: your Gemini API key
4. The workflow uses GEMINI_MODEL=gemini-3.8-flash. Do not put the key in source code, commits, issues, screenshots, or chat.

If the provider requires an adult account holder, a parent/guardian must create and manage the account and its security settings. Do not misstate age or bypass verification.

## 2. Configure YouTube private upload

YouTube upload is optional. Without all three OAuth secrets, the workflow only creates a review artifact.

1. In Google Cloud Console, create or select a project and enable **YouTube Data API v3**.
2. Configure the Google Auth Platform consent screen and add the channel-owning account as a test user if the app is in Testing.
3. Create a **Desktop app** OAuth client and download its JSON file.
4. Save the downloaded file in the repository root on your own computer as client_secret.json. This filename is ignored by Git; never commit or share it.
5. Install Python 3.11+ and run locally:

~~~bash
python -m pip install -r requirements.txt
python -m stoic_shorts --oauth-setup
~~~

6. Complete Google sign-in for the channel that should receive the video. The script saves the three OAuth values locally in .oauth/github-actions-secrets.json.
7. In GitHub **Settings → Secrets and variables → Actions**, add these repository secrets using the matching values from that local file:
   - YOUTUBE_CLIENT_ID
   - YOUTUBE_CLIENT_SECRET
   - YOUTUBE_REFRESH_TOKEN

Keep the .oauth folder and OAuth client file private. If Google OAuth is left in Testing, refresh-token lifetime and reauthorization requirements can interrupt automation. Follow the current Google OAuth consent-screen and verification requirements for your account and app.

## 3. Run the workflow

Open **Actions → Build and upload private Short → Run workflow**.

The scheduled run is set for **19:00 Asia/Kolkata** (13:30 UTC). GitHub scheduled workflows can be delayed during high load and may be disabled for inactive public repositories.

- With Gemini secret only: creates a video artifact for review.
- With Gemini and all three YouTube secrets: uploads one video as **PRIVATE**.
- A second upload on the same date is blocked.
- The workflow never sets the video to Public or Unlisted.

## Output

The workflow stores these files as a GitHub Actions artifact for 14 days:

- short.mp4 — 1080×1920, H.264/AAC, 30–60 seconds
- thumbnail.png — first-scene artwork (artifact only; not separately uploaded as a custom thumbnail)
- script.txt — final narration
- captions.srt — timed subtitle file
- metadata.json — title, description, tags, and language metadata

## Local development

Install FFmpeg and Noto fonts, then:

~~~bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m stoic_shorts --output output
~~~

For YouTube OAuth setup, use python -m stoic_shorts --oauth-setup after placing your own Desktop OAuth client JSON at client_secret.json.

## Safety and publishing checklist

- Check the generated script for philosophical accuracy and factual claims.
- Watch the full video and verify narration pronunciation, timing, captions, and visual quality.
- Confirm the upload is **Private** in YouTube Studio.
- Publish manually only after review.
