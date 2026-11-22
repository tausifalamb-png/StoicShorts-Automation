"""Free-tier Groq LLM script generation for StoicShorts.

The API key is read only from the environment; never store it in source control.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import date

API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def _validate_script(data, day):
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object.")
    required = ("title", "hook", "scenes", "narration")
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


def generate_script(day, history):
    """Generate one original 30–60 second Hinglish script using Groq's free plan."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
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
    prompt = f"""
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
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not include request headers or the API key in logs.
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        raise RuntimeError(f"Groq API returned HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Groq API: {exc.reason}") from None

    try:
        raw = result["choices"][0]["message"]["content"]
        data = json.loads(raw)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Groq returned an unexpected response format.") from exc
    return _validate_script(data, day)
