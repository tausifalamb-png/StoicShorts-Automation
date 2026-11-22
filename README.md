# StoicShorts Automation

A private-first Hinglish YouTube Shorts generator using Python, eSpeak NG, Pillow, FFmpeg, and GitHub Actions.

## Automation
No separate app is needed. Open **Actions** in this repository and enable workflows if GitHub prompts you. The daily workflow runs at **19:00 Asia/Kolkata** (13:30 UTC) and can also be started manually. GitHub scheduled workflows run from the default branch; public repositories with no activity for 60 days can have schedules disabled.

## YouTube OAuth setup — do this once
1. Open Google Cloud Console and create/select a project.
2. In **APIs & Services → Library**, enable **YouTube Data API v3**.
3. Open **Google Auth Platform → Branding** and provide an app name and support email.
4. Under **Audience**, choose **External** for a personal Google account. During development, add the Google account that owns/manages the YouTube channel as a test user.
5. Under **Data Access**, request only this scope: `https://www.googleapis.com/auth/youtube.upload`.
6. Under **Clients**, create an OAuth client of type **Desktop app** and download its JSON file. Rename it to `client_secret.json` and place it in the repository folder on your own computer. The file is ignored by Git; never upload it or paste its contents into chat.
7. On your computer, install Python 3.11+, FFmpeg and eSpeak NG. In the repository folder run:
   ```bash
   python -m pip install -r requirements.txt
   python -m stoic_shorts --oauth-setup
   ```
   A browser window opens. Sign in with the Google account that owns the target channel and approve upload access. The terminal prints three values.
8. In GitHub open **Settings → Secrets and variables → Actions → New repository secret**. Add:
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`
   - `YOUTUBE_REFRESH_TOKEN`
   Paste each matching value from the local terminal. Do not share these values with anyone.
9. Open **Actions → Build and upload private Short → Run workflow**. Review the run and confirm the resulting video is **Private** in YouTube Studio.

**OAuth warning:** If the Google Auth Platform app remains in **Testing**, Google says authorizations for non-basic scopes expire after seven days, including refresh tokens. That means the automation will stop uploading until you authorize again. For longer-running personal use, review Google's production/personal-use and verification requirements; do not assume that simply switching to Production guarantees approval. A warning screen may appear for an unverified app. Google controls this, not this repository.

## Free LLM script generation (Gemini primary, Groq fallback)

The workflow can generate one fresh Hinglish script per run. It uses **Gemini 3.8 Flash** first and falls back to **OpenAI GPT-OSS 120B on Groq** if Gemini fails and both keys are configured.

### Primary: Gemini 3.8 Flash

Google's current pricing page lists Gemini 3.8 Flash standard input and output as free of charge on the Free tier. Free-tier content may be used by Google to improve its products, so do not send private, personal, or sensitive information in prompts. The current prompt only includes a Stoic theme and recent public video titles. Free-tier model availability and quotas can change; check your AI Studio project's live rate limits.

1. Create an eligible API key in [Google AI Studio](https://aistudio.google.com/api-keys).
2. In this repository open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add `GEMINI_API_KEY` with the key. The workflow selects `gemini-3.8-flash` by default.

### Fallback: Groq GPT-OSS 120B

Groq's published Free Plan limits for `openai/gpt-oss-120b` are 30 requests/minute, 1,000 requests/day, 8,000 tokens/minute, and 200,000 tokens/day. Limits are organization-level and may change; check the live Limits page.

1. Create an eligible key at [GroqCloud API Keys](https://console.groq.com/keys).
2. Add a second GitHub Actions secret named `GROQ_API_KEY`.
3. The workflow uses `openai/gpt-oss-120b` as the fallback model.

If neither key is present, the project uses the six-script local fallback bank. One Short per day is a small workload, but no provider offers unlimited free capacity. The account holder must follow each provider's current age and account terms; do not misstate age or bypass verification. If adult account ownership is required, a parent/guardian must create and manage that account and its security settings.

The LLM is instructed not to invent Stoic quotations or historical attributions. Still review every generated script and the final video before publishing. A valid API response does not prove factual accuracy or YouTube monetization eligibility.

## What the workflow does
- Selects one original Hinglish script from `content/scripts.json`.
- Generates synthetic narration with eSpeak NG and original procedural scene cards with Pillow.
- Renders an H.264/AAC MP4 at 1080×1920 and checks duration, video, and audio streams.
- Uploads as **PRIVATE only** when all three YouTube secrets exist. Without them, it builds a review artifact and skips upload.
- Saves run history to prevent same-day duplicate uploads.
- Stores MP4, thumbnail, script, and metadata as a 14-day GitHub Actions artifact.

## Zero-cost reality and limitations
The project uses open-source software, but GitHub Actions has usage limits; it is not unlimited free compute. eSpeak NG voice is robotic, and the current scripts are Latin-script Hinglish, not natural Hindi speech. Six starter scripts are included; add more original scripts in `content/scripts.json` to expand the rotation. This initial implementation has not yet been validated by a successful GitHub Actions run or a real YouTube OAuth upload.

The uploader hard-codes `privacyStatus=private`; there is no public/unlisted override. Review each video manually before publishing. Repetitive templated content is not a monetization guarantee.

## Local commands
```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m stoic_shorts --output output
```
