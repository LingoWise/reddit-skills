"""Shared LLM client for all reddit-skills.

Every skill loads this module via importlib from the project-root ``lib/``
directory — the same pattern used for cross-skill imports like ``reddit-auth``.

Environment variables (read from the shell, NOT from ``.env``):
  - ``OPENAI_API_KEY``     — OpenAI API key (required if no OpenRouter key).
  - ``OPENROUTER_API_KEY`` — OpenRouter API key (alternative provider).
  - ``OPENAI_BASE_URL``    — Override the API base URL (optional).
  - ``OPENAI_MODEL``       — Model name for OpenAI calls.
  - ``OPENROUTER_MODEL``   — Model name for OpenRouter calls (falls back to ``OPENAI_MODEL``).
"""

import json
import os


def client():
    """Return an ``OpenAI`` client configured from environment variables.

    Raises ``RuntimeError`` if neither ``OPENAI_API_KEY`` nor
    ``OPENROUTER_API_KEY`` is set, or if the ``openai`` package is missing.
    """
    from openai import OpenAI

    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if not openai_key and not openrouter_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY or OPENROUTER_API_KEY in the shell environment "
            "before running AI analysis."
        )

    if openrouter_key:
        return OpenAI(
            api_key=openrouter_key,
            base_url=os.getenv("OPENAI_BASE_URL") or "https://openrouter.ai/api/v1",
        )

    return OpenAI(
        api_key=openai_key,
        base_url=os.getenv("OPENAI_BASE_URL"),
    )


def model():
    """Return the model name based on which provider key is set."""
    if os.getenv("OPENROUTER_API_KEY"):
        return os.getenv("OPENROUTER_MODEL") or os.getenv("OPENAI_MODEL")
    return os.getenv("OPENAI_MODEL")


def available():
    """Check whether an LLM provider is configured and the client package is installed.

    Returns ``(ok, message)``.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openai_key and not openrouter_key:
        return False, "set OPENAI_API_KEY or OPENROUTER_API_KEY for AI-generated analysis (otherwise the agent will supply analysis manually)"
    try:
        import importlib
        importlib.import_module("openai")
    except ImportError:
        return False, "openai package not installed; run `uv pip install openai`"
    return True, "AI client ready"


def chat_json(messages, model_name=None, temperature=0.2, client_obj=None):
    """Call the LLM and return parsed JSON.

    ``messages`` is a list of ``{"role": ..., "content": ...}`` dicts.
    Strips markdown code fences from the response before parsing.
    """
    if client_obj is None:
        client_obj = client()
    if model_name is None:
        model_name = model()

    response = client_obj.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=temperature,
    )
    content = response.choices[0].message.content.strip()
    if content.startswith("```"):
        content = content.strip("`").strip("json").strip()
    return json.loads(content)
