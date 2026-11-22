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

## Quality-first LLM script generation (Gemini only)

The workflow uses **Gemini 3.8 Flash** as the only script model. It makes two calls per Short: the first drafts the script; the second performs a strict editorial review and rewrites weak parts. This spends more of the free quota in exchange for a stronger result. There is deliberately **no Groq or local-script fallback**: if Gemini is unavailable, rate-limited, or the output fails validation, the run stops rather than silently lowering quality or publishing a recycled script.

1. Create an eligible API key in [Google AI Studio](https://aistudio.google.com/api-keys).
2. In this repository open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add a secret named `GEMINI_API_KEY` with your own key. The workflow selects the stable model ID `gemini-3.8-flash` by default.
4. Run **Actions → Build and upload private Short → Run workflow**. If the free-tier quota is exhausted, wait for the provider's quota reset and retry.

Google's current model documentation lists Gemini 3.8 Flash as a stable model. Free-tier availability, quotas, and data-use terms can change; check the current AI Studio project limits and pricing before relying on it. Do not send private or sensitive information in free-tier prompts. The prompt uses channel topics and recent video titles only.

The second pass checks accuracy of the Stoic principle, hook strength, natural Hinglish, specificity, originality, narration length, and unsupported quotations or historical claims. Automated review is not fact-checking: review the script and rendered video before publishing. No model can guarantee virality, accuracy, or monetization.

The account holder must follow the provider's current age and account terms. Do not misstate age or bypass verification; if adult account ownership is required, a parent/guardian must create and manage the account and its security settings.

## What the workflow does
- Generates and editorially reviews one original Hinglish script using Gemini (two API calls).
- Generates synthetic narration with eSpeak NG and original procedural scene cards with Pillow.
- Renders an H.264/AAC MP4 at 1080×1920 and checks duration, video, and audio streams.
- Uploads as **PRIVATE only** when all three YouTube secrets exist. Without them, it builds a review artifact and skips upload.
- Saves run history to prevent same-day duplicate uploads.
- Stores MP4, thumbnail, script, and metadata as a 14-day GitHub Actions artifact.

## Zero-cost reality and limitations
The project uses open-source software, but GitHub Actions has usage limits; it is not unlimited free compute. eSpeak NG voice is robotic, and the current scripts are Latin-script Hinglish, not natural Hindi speech. The old starter script bank is not used by the quality-first pipeline. This initial implementation has not yet been validated by a successful GitHub Actions run or a real YouTube OAuth upload.

The uploader hard-codes `privacyStatus=private`; there is no public/unlisted override. Review each video manually before publishing. Repetitive templated content is not a monetization guarantee.

## Local commands
```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m stoic_shorts --output output
```
