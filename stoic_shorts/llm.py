"""Gemini-only, two-pass quality-first Hinglish script generation."""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import date

DEFAULT_MODEL = "gemini-3.8-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _validate_script(data, day):
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object.")
    required = ("title", "hook", "narration")
    if any(not isinstance(data.get(key), str) for key in required):
        raise ValueError("LLM response is missing title, hook, or narration text.")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 3:
        raise ValueError("LLM must return exactly three scene captions.")
    if not all(isinstance(scene, str) and scene.strip() for scene in scenes):
        raise ValueError("Scene captions must be non-empty strings.")

    title = data["title"].strip()
    hook = data["hook"].strip()
    narration = data["narration"].strip()
    words = len(narration.split())
    if not title or len(title.split()) > 8 or len(title) > 90:
        raise ValueError("Title must be clear and no more than eight words.")
    if not hook or len(hook) > 180:
        raise ValueError("Generated hook is empty or too long.")
    if not 75 <= words <= 110:
        raise ValueError(f"Narration must contain 75–110 words; received {words}.")
    if any(len(scene.strip()) > 90 for scene in scenes):
        raise ValueError("Scene captions must be 90 characters or fewer.")
    if len(narration) < 250:
        raise ValueError("Narration is too short for a complete 30–60 second Short.")

    return {
        "id": "ai-" + day.replace("-", ""),
        "title": title,
        "hook": hook,
        "scenes": [scene.strip() for scene in scenes],
        "narration": narration,
        "source": "Original educational reflection on Stoic principles; not a direct quotation.",
    }


def _request_json(url, payload, headers):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:700]
            if exc.code == 429:
                raise RuntimeError(
                    "Gemini quota/rate limit reached (HTTP 429). No lower-quality fallback is enabled."
                ) from None
            if exc.code in (500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"Gemini API returned HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            raise RuntimeError(f"Could not reach Gemini API: {exc.reason}") from None
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini API returned invalid JSON.") from exc
    raise RuntimeError("Gemini request failed after retries.")


def _call_gemini(prompt, max_output_tokens=1800):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from GitHub Actions repository secrets.")
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    payload = {
        "systemInstruction": {
            "parts": [{
                "text": (
                    "You are a rigorous senior editor for a practical Stoicism education channel in India. "
                    "Prioritize philosophical accuracy, original insight, natural Indian language, and viewer utility. "
                    "Never fabricate quotations, citations, historical anecdotes, or attributions. "
                    "Follow the requested JSON schema exactly."
                )
            }]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.65,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": "application/json",
        },
    }
    result = _request_json(
        API_URL.format(model=model),
        payload,
        {"x-goog-api-key": api_key},
    )
    try:
        candidate = result["candidates"][0]
        if candidate.get("finishReason") not in (None, "STOP"):
            raise RuntimeError(f"Gemini stopped generation early: {candidate.get('finishReason')}")
        parts = candidate["content"]["parts"]
        raw = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        return json.loads(raw)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned an unexpected response format.") from exc


def _base_prompt(day, history):
    recent_titles = [
        str(item.get("title", ""))
        for item in history.get("videos", [])[-30:]
        if item.get("title")
    ]
    themes = [
        "control what is within your influence",
        "guarding attention from distraction",
        "discipline without depending on mood",
        "responding calmly to criticism",
        "accepting setbacks and adapting wisely",
        "choosing integrity over approval",
        "using time deliberately",
        "separating facts from assumptions",
        "handling comparison without resentment",
        "keeping promises to yourself",
        "patience when results are slow",
        "choosing a thoughtful response under pressure",
        "learning from a mistake without self-insult",
        "using discomfort as a chance to practise patience",
    ]
    theme = themes[date.fromisoformat(day).timetuple().tm_yday % len(themes)]
    return f"""
Create one original, high-quality YouTube Short for an Indian audience.
Channel: practical Stoicism. Today's theme: {theme}.
Do not repeat or lightly reword these recent titles:
{json.dumps(recent_titles, ensure_ascii=False)}

Audience: Indian teens and young adults.
Language: natural spoken Hinglish. Write Hindi sentences in Devanagari script so a Hindi neural voice
can pronounce them naturally. Keep common English words and terms in Latin script where people
normally say them (for example: focus, pressure, discipline, response, practice).
The title and hook should be in natural Roman Hinglish.
Voice: thoughtful, direct, grounded, modern, human; never preachy or melodramatic.

Return ONLY one valid JSON object with exactly these keys:
{{
  "title": "curiosity-building title, maximum eight words",
  "hook": "one sharp opening sentence in Roman Hinglish",
  "scenes": ["short scene caption 1", "short scene caption 2", "short scene caption 3"],
  "narration": "complete spoken Hinglish narration, Hindi in Devanagari"
}}

Strict editorial requirements:
- Narration must be 75–110 whitespace-separated words and naturally speakable in 30–60 seconds.
- Open with a relatable tension, question, or specific everyday moment.
- Build one clear idea: situation → Stoic principle → practical response.
- Include one concrete everyday example: study pressure, criticism, distraction, friendship,
  expectations, mistakes, or social media. Do not invent personal testimony.
- Give one small, safe action the viewer can try today.
- Explain the principle accurately; distinguish what a person controls from what they do not.
- Stoicism does not mean suppressing emotions, tolerating mistreatment, or refusing help.
- Avoid clichés, empty hype, repeated phrases, fake urgency, and generic motivational slogans.
- Never invent quotations, book passages, page numbers, historical anecdotes, or philosopher attributions.
- Do not imitate a named creator or reproduce recognizable wording from existing videos.
- Exactly three short visual scene captions, each no more than 90 characters.
- No markdown, hashtags, emojis, or production directions in narration.
"""


def generate_script(day, history):
    """Generate a draft and an independent editorial revision; no provider fallback."""
    prompt = _base_prompt(day, history)
    draft = _call_gemini(prompt)
    review_prompt = f"""
Act as a strict final editor for a short educational Stoicism video.
Return ONLY a final JSON object with exactly these keys:
"title", "hook", "scenes", "narration".

DRAFT:
{json.dumps(draft, ensure_ascii=False)}

Rewrite weak sections instead of approving automatically. Check:
1. The Stoic principle is accurate, practical, and not oversimplified.
2. The opening creates curiosity without clickbait.
3. Spoken Hinglish is natural; Hindi remains in Devanagari and common English words in Latin script.
4. There is one specific everyday example and one useful action.
5. The narration is 75–110 whitespace-separated words and easy to speak aloud.
6. No invented quotation, source, philosopher attribution, historical anecdote, or unsupported claim.
7. The title is no more than eight words; there are exactly three concise scene captions.
8. No shaming, toxic positivity, or advice to suppress emotions.
9. Preserve the strongest original insight and remove filler.
Return JSON only, without markdown or commentary.
"""
    final_data = _call_gemini(review_prompt)
    return _validate_script(final_data, day)
