#!/usr/bin/env python3
"""Small OpenAI-compatible Chat Completions client shared by skills."""

import json
import os
import urllib.error
import urllib.request


class LLMConfigError(RuntimeError):
    pass


class LLMRequestError(RuntimeError):
    pass


def resolve_config(provider=None, base_url=None, api_key=None, model=None):
    provider = provider or os.getenv("LLM_PROVIDER", "openai_compatible")
    base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    api_key = api_key or os.getenv("LLM_API_KEY", "")
    model = model or os.getenv("LLM_MODEL", "gpt-5.5")

    provider = provider.strip().lower()
    base_url = base_url.strip().rstrip("/")
    api_key = api_key.strip()
    model = model.strip()

    if provider != "openai_compatible":
        raise LLMConfigError(
            f"Unsupported LLM_PROVIDER={provider!r}. Set LLM_PROVIDER=openai_compatible."
        )
    if not base_url:
        raise LLMConfigError("LLM_BASE_URL is empty. Example: https://api.openai.com/v1")
    if not model:
        raise LLMConfigError("LLM_MODEL is empty. Example: gpt-5.5")
    if not api_key:
        raise LLMConfigError(
            "LLM_API_KEY is not set. Set it in the environment; do not write API keys into code or files."
        )
    return {
        "provider": provider,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
    }


def chat_completion(prompt, provider=None, base_url=None, api_key=None, model=None, temperature=0.2, timeout=180):
    config = resolve_config(provider=provider, base_url=base_url, api_key=api_key, model=model)
    url = config["base_url"] + "/chat/completions"
    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": temperature,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": "Bearer " + config["api_key"],
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise LLMRequestError(f"LLM HTTP {e.code}: {body}") from e
    except urllib.error.URLError as e:
        raise LLMRequestError(f"LLM request failed: {e}") from e

    try:
        parsed = json.loads(raw)
        content = parsed["choices"][0]["message"]["content"]
    except Exception as e:
        raise LLMRequestError(f"Could not parse OpenAI-compatible response: {raw[:1000]}") from e
    return content or ""
