"""Stage 2. Turns SourcedMaterial + Concept into a Script.

Produces: hook, body, title, description, hashtags, and (for stock concepts) one
footage search query per beat.

Hook rules live in the concept yaml, not here. This module is format-agnostic.
"""
from __future__ import annotations

import logging

from factory.scripting.llm_client import LLMClient
from factory.scripting.templates import get_system_prompt, get_user_prompt
from factory.types import Concept, Script, SourcedMaterial

log = logging.getLogger(__name__)

# JSON schema the LLM must conform to
_SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "body": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "clip_queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["hook", "body", "title", "description", "hashtags"],
}


def write_script(
    concept: Concept,
    material: SourcedMaterial | None,
    client: LLMClient,
) -> Script:
    """Generate a script for one concept using the LLM client.

    Args:
        concept: The parsed concept config.
        material: Stage 1 output (may be None for generated concepts).
        client: LLM client (fixture or real).

    Returns:
        A Script dataclass with hook, body, title, description, hashtags,
        and (for stock concepts) clip_queries.
    """
    system = get_system_prompt(concept)
    user = get_user_prompt(concept, material)

    log.info("Writing script for concept=%s mode=%s", concept.id, concept.sourcing.mode)
    raw = client.complete_json(system, user, schema=_SCRIPT_SCHEMA)

    # Validate and build Script
    script = Script(
        hook=raw.get("hook", ""),
        body=raw.get("body", ""),
        title=raw.get("title", concept.id),
        description=raw.get("description", ""),
        hashtags=raw.get("hashtags", []),
        clip_queries=raw.get("clip_queries", []),
    )

    # Enforce hook length
    max_hook = concept.script.hook_max_words
    words = script.hook.split()
    if len(words) > max_hook:
        script.hook = " ".join(words[:max_hook])

    log.info(
        "Script written: hook=%d words, body=%d words, %d hashtags, %d clip_queries",
        len(script.hook.split()),
        len(script.body.split()),
        len(script.hashtags),
        len(script.clip_queries),
    )
    return script
