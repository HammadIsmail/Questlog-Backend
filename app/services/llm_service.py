"""
Unified LLM Service supporting Groq, OpenAI, and Anthropic.
Prioritizes ultra-fast inference (Groq) when configured.
"""
import json
import logging
from typing import Optional, Dict, Any, List
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def is_llm_available() -> bool:
    """Check if any LLM API key is configured."""
    return bool(settings.groq_api_key or settings.openai_api_key or settings.anthropic_api_key)


async def complete_chat(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 600,
) -> Optional[str]:
    """Execute a chat completion across the active provider."""
    # 1. Groq (Prioritized for speed)
    if settings.groq_api_key:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.groq_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.warning("Groq API returned error %s: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.error("Groq chat completion failed: %s", e)

    # 2. OpenAI Fallback
    if settings.openai_api_key:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error("OpenAI chat completion failed: %s", e)

    return None


async def complete_json(
    system_prompt: str,
    user_prompt: str,
) -> Optional[Dict[str, Any]]:
    """Execute a structured JSON completion."""
    json_system = system_prompt + "\nIMPORTANT: Return ONLY valid JSON with no markdown backticks or commentary."

    # Groq supports json_object response_format on llama-3.3
    if settings.groq_api_key:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.groq_model,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": json_system},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.2,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return json.loads(content)
        except Exception as e:
            logger.error("Groq JSON completion failed: %s", e)

    # OpenAI Fallback
    if settings.openai_api_key:
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": json_system},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.2,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    return json.loads(content)
        except Exception as e:
            logger.error("OpenAI JSON completion failed: %s", e)

    # Fallback to plain completion and parse
    raw = await complete_chat(json_system, user_prompt, temperature=0.1)
    if raw:
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        try:
            return json.loads(clean.strip())
        except Exception:
            pass

    return None
