import json
import requests

from app.config import GROQ_API_KEY, GROQ_API_URL, logger

MODELS_TO_TRY = [
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


def generate_ai_response(prompt: str) -> dict:
    """Send a prompt to Groq and return the parsed JSON response."""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_key_here":
        raise ValueError(
            "GROQ_API_KEY is not configured. Set it in the .env file."
        )

    logger.info("Groq API key loaded (ends with ...%s)", GROQ_API_KEY[-4:])

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    for model in MODELS_TO_TRY:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a ticket analysis assistant. "
                        "Always respond with valid JSON only. No extra text."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 512,
        }

        logger.info("Trying Groq model: %s", model)

        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code >= 400:
            logger.error("Groq error with %s — %s: %s", model, response.status_code, response.text)
            continue

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        logger.info("Groq responded successfully with model: %s", model)

        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            content = content.rsplit("```", 1)[0].strip()

        return json.loads(content)

    raise RuntimeError("All Groq models failed")
