"""Quality-first Gemini script generation for StoicShorts.

Gemini is the only provider. A second Gemini editorial pass improves each draft.
No lower-quality provider or local script bank is used as a silent fallback.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import date

DEFAULT_MODEL = "gemini-3.8-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:700]
        if exc.code == 429:
            raise RuntimeError("Gemini quota/rate limit reached (HTTP 429). No fallback was used; retry after the quota resets.") from None
        raise RuntimeError(f"Gemini API returned HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Gemini API: {exc.reason}") from None


def _call_gemini(prompt, max_output_tokens=1400):
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to GitHub Actions repository secrets.")
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    payload = {
        "systemInstruction": {
            "parts": [{
                "text": (
                    "You are a demanding senior editor for an educational Stoicism channel. "
                    "Prioritize accuracy, originality, natural spoken Hinglish, and viewer value. "
                    "Never invent historical claims or quotations. Follow the JSON schema exactly."
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
Create one high-quality, original YouTube Short for an Indian audience.
Channel: practical Stoicism. Today's theme: {theme}.
Avoid repeating or lightly rewording these recent titles:
{json.dumps(recent_titles, ensure_ascii=False)}

Audience: Indian teens and young adults. Language: conversational Hinglish in Latin/Roman script.
Voice: thoughtful, direct, grounded, modern and human — not preachy, robotic, overly dramatic,
or like a generic motivational quote page.

Return ONLY one valid JSON object with exactly these keys:
{{
  "title": "clear, curiosity-building title; maximum 8 words",
  "hook": "one sharp opening sentence in Hinglish",
  "scenes": ["scene card 1", "scene card 2", "scene card 3"],
  "narration": "complete narration in Hinglish"
}}

Editorial requirements:
- Narration must be 75–110 words, naturally speakable in 30–60 seconds.
- Start with a relatable tension, question, or specific everyday moment in the first sentence.
- Build one clear idea: situation → Stoic principle → practical response.
- Include one concrete everyday example (study pressure, criticism, distraction, friendship,
  expectations, mistakes, or social media) without inventing personal testimony.
- Give one small action the viewer can actually try today.
- Explain the principle accurately; distinguish what a person controls from what they do not.
- Do not imply Stoicism means suppressing emotions, tolerating mistreatment, or never asking for help.
- Avoid clichés, empty hype, repeated phrases, fake urgency, and generic "be strong" advice.
- Never invent quotations, book passages, page numbers, historical anecdotes, or philosopher attributions.
- Do not imitate a named creator or reproduce recognizable wording from existing videos.
- Exactly three short visual scene captions, each no more than 90 characters.
- No markdown, hashtags, emojis, or production directions in narration.
"""


def generate_script(day, history):
    """Generate and editorially refine a script with Gemini; fail rather than downgrade."""
    prompt = _base_prompt(day, history)
    draft = _call_gemini(prompt)

    review_prompt = f"""
You are the final quality editor. Review this proposed short-form educational script.
Return ONLY a corrected final JSON object with exactly these keys:
"title", "hook", "scenes", "narration".

DRAFT:
{json.dumps(draft, ensure_ascii=False)}

Apply this strict checklist:
1. Is the Stoic idea accurate and explained without oversimplification?
2. Is the first line compelling and specific rather than generic clickbait?
3. Does the script sound like natural Indian spoken Hinglish in Roman letters?
4. Is there a concrete everyday example and one useful action?
5. Is every sentence necessary, clear, and easy to narrate aloud?
6. Are there any unsupported historical claims, fabricated quotes, or fake attributions? Remove them.
7. Is the narration 75–110 whitespace-separated words? Rewrite to fit if needed.
8. Are there exactly three concise scene captions, each at most 90 characters?
9. Is the title accurate, concise, and no more than 8 words?
10. Does it avoid shaming, toxic positivity, and telling viewers to suppress emotions?

Improve weak parts rather than merely approving the draft. Preserve its strongest original insight.
Return JSON only, no commentary or markdown.
"""
    final_data = _call_gemini(review_prompt)
    return _validate_script(final_data, day)
