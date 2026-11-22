"""Free-tier LLM script generation for StoicShorts.

Gemini 3.8 Flash is the primary provider; Groq GPT-OSS 120B is the fallback.
API keys are read only from environment variables / GitHub Actions secrets.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import date

GEMINI_DEFAULT_MODEL = "gemini-3.8-flash"
GROQ_DEFAULT_MODEL = "openai/gpt-oss-120b"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _validate_script(data, day):
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object.")
    if any(not isinstance(data.get(k), str) for k in ("title", "hook", "narration")):
        raise ValueError("LLM response is missing title, hook, or narration text.")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 3 or not all(isinstance(x, str) and x.strip() for x in scenes):
        raise ValueError("LLM must return exactly three non-empty scene captions.")
    title, hook, narration = (data[k].strip() for k in ("title", "hook", "narration"))
    words = len(narration.split())
    if not title or len(title) > 90 or not hook or len(hook) > 180:
        raise ValueError("Generated title or hook is empty or too long.")
    if not 75 <= words <= 110:
        raise ValueError(f"Narration must contain 75–110 words; received {words}.")
    if any(len(x.strip()) > 90 for x in scenes):
        raise ValueError("Scene captions must be 90 characters or fewer.")
    return {
        "id": "ai-" + day.replace("-", ""),
        "title": title,
        "hook": hook,
        "scenes": [x.strip() for x in scenes],
        "narration": narration,
        "source": "Original reflection on Stoic principles; not a direct quotation.",
    }


def _request_json(url, payload, headers):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        raise RuntimeError(f"LLM provider returned HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach LLM provider: {exc.reason}") from None


def _prompt(day, history):
    recent_titles = [
        str(item.get("title", ""))
        for item in history.get("videos", [])[-20:]
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
    ]
    theme = themes[date.fromisoformat(day).timetuple().tm_yday % len(themes)]
    return f"""
Create one original YouTube Shorts script for an Indian audience in natural Hinglish
written in Latin/Roman script. Channel topic: practical Stoicism. Today's theme: {theme}.
Avoid repeating these recent titles: {json.dumps(recent_titles, ensure_ascii=False)}.

Return ONLY a valid JSON object with exactly these keys:
{{
  "title": "short title, maximum 8 words",
  "hook": "one strong opening sentence in Hinglish",
  "scenes": ["short scene caption 1", "short scene caption 2", "short scene caption 3"],
  "narration": "complete narration in Hinglish"
}}

Requirements:
- Narration must be 75 to 110 whitespace-separated words, suitable for a 30–60 second Short.
- Use simple, natural spoken Hinglish; write Hindi words in Latin script.
- Make the idea concrete with one everyday example and one practical action.
- Be original, useful, balanced, and non-preachy.
- Do not invent quotes, book passages, page numbers, historical facts, or attribute wording to Stoic philosophers.
- Do not copy or closely imitate a modern creator's wording.
- No markdown fences, hashtags, emojis, or production directions in the narration.
- Exactly three scene captions, each concise and suitable for a vertical text card.
"""


def _call_gemini(prompt):
    api_key = os.environ["GEMINI_API_KEY"].strip()
    model = os.environ.get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL).strip() or GEMINI_DEFAULT_MODEL
    payload = {
        "systemInstruction": {
            "parts": [{"text": "You write accurate, original, concise educational scripts. Follow the requested JSON schema exactly."}]
        },
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1100,
            "responseMimeType": "application/json",
        },
    }
    result = _request_json(
        GEMINI_URL.format(model=model),
        payload,
        {"x-goog-api-key": api_key},
    )
    try:
        parts = result["candidates"][0]["content"]["parts"]
        raw = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        return json.loads(raw)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned an unexpected response format.") from exc


def _call_groq(prompt):
    api_key = os.environ["GROQ_API_KEY"].strip()
    model = os.environ.get("GROQ_MODEL", GROQ_DEFAULT_MODEL).strip() or GROQ_DEFAULT_MODEL
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You write accurate, original, concise educational scripts. Follow the requested JSON schema exactly."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_completion_tokens": 1100,
        "response_format": {"type": "json_object"},
    }
    result = _request_json(
        GROQ_URL,
        payload,
        {"Authorization": "Bearer " + api_key},
    )
    try:
        raw = result["choices"][0]["message"]["content"]
        return json.loads(raw)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Groq returned an unexpected response format.") from exc


def generate_script(day, history):
    """Prefer Gemini 3.8 Flash; fall back to Groq GPT-OSS 120B when configured."""
    prompt = _prompt(day, history)
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()

    if gemini_key:
        try:
            return _validate_script(_call_gemini(prompt), day)
        except Exception as exc:
            if not groq_key:
                raise RuntimeError(f"Gemini generation failed: {exc}") from exc
            print(f"Gemini generation failed; trying configured Groq fallback ({type(exc).__name__}).")

    if groq_key:
        return _validate_script(_call_groq(prompt), day)

    raise RuntimeError("No LLM key configured. Add GEMINI_API_KEY or GROQ_API_KEY to GitHub Actions secrets.")
