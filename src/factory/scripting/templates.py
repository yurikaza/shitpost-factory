"""Reusable instruction fragments for the LLM, keyed by concept format.

Kept as data so a new concept needs a yaml entry, not new Python.
"""
from __future__ import annotations

# System prompts per concept type. The writer picks the right one based on
# concept.sourcing.mode or concept.id.
SYSTEM_PROMPTS: dict[str, str] = {
    "stock": (
        "You write short-form video scripts for TikTok/Reels/Shorts. "
        "Your scripts go VIRAL because they sound unhinged, not because they're informative. "
        "Hook the viewer with something that sounds wrong, cursed, or threatening. "
        "The body should feel like you're delivering forbidden knowledge at gunpoint. "
        "NEVER sound like a teacher, documentary, or \"did you know\" channel. "
        "Write a hook (max {hook_max_words} words), a body ({target_words} words), "
        "a title (max 60 chars), a description (max 150 chars), "
        "and exactly {hashtags_count} hashtags. Tone: {tone}. "
        "Also produce exactly {clips_per_video} short search queries (2-4 words each) "
        "for stock footage — make them match the vibe of each beat, not literal descriptions. "
        "Respond as JSON with keys: hook, body, title, description, hashtags, clip_queries."
    ),
    "reddit-video": (
        "You write shitpost text overlays for funny video clips. "
        "The video is already funny — your job is to make it FUNNIER with text. "
        "Write a hook (top of screen, max {hook_max_words} words) and a body "
        "(bottom of screen, {target_words} words max, ONE short sentence). "
        "The text should feel like the obvious thing everyone's thinking but said in a cursed way. "
        "NEVER explain the video. NEVER be wholesome. Sound like a degenerate shitposter. "
        "Also write a title, description, and {hashtags_count} hashtags. "
        "Respond as JSON with keys: hook, body, title, description, hashtags."
    ),
    "reddit-text": (
        "You are a short-form video scriptwriter. Rewrite the following Reddit story "
        "into a narration script. DO NOT copy the original text verbatim — that is the "
        "transformation that keeps the video monetisable. "
        "Write a hook (max {hook_max_words} words), a body ({target_words} words), "
        "a title (max 60 chars), a description (max 150 chars), and exactly "
        "{hashtags_count} hashtags. Tone: {tone}. "
        "Respond as JSON with keys: hook, body, title, description, hashtags."
    ),
    "generated": (
        "You are a short-form video scriptwriter. Write a hook (max {hook_max_words} "
        "words), a body ({target_words} words), a title (max 60 chars), a description "
        "(max 150 chars), and exactly {hashtags_count} hashtags. "
        "Tone: {tone}. "
        "Respond as JSON with keys: hook, body, title, description, hashtags."
    ),
}

# Template for the user message that wraps source material
USER_TEMPLATES: dict[str, str] = {
    "stock": "Write a script about: {description}",
    "reddit-video": "Write shitpost text overlay for a funny video. Theme: {description}",
    "reddit-text": (
        "Here is a Reddit post to rewrite:\n\n"
        "Title: {source_title}\n"
        "Body:\n{text_source}\n\n"
        "Rewrite it as a narration script. Keep the core story, change the wording."
    ),
    "generated": "Write a script about: {description}",
}


def get_system_prompt(concept) -> str:
    """Return the system prompt for a concept, with fields filled from concept config."""
    mode = concept.sourcing.mode if hasattr(concept, "sourcing") else "stock"
    template = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS["stock"])

    # Gather template vars from concept
    script_cfg = getattr(concept, "script", None)
    publish_cfg = getattr(concept, "publish", None)
    sourcing_cfg = getattr(concept, "sourcing", None)

    vars_ = {
        "hook_max_words": getattr(script_cfg, "hook_max_words", 8) if script_cfg else 8,
        "target_words": getattr(script_cfg, "target_words", 100) if script_cfg else 100,
        "tone": getattr(script_cfg, "tone", "confident, short sentences") if script_cfg else "confident, short sentences",
        "hashtags_count": getattr(publish_cfg, "hashtags_count", 5) if publish_cfg else 5,
        "clips_per_video": getattr(sourcing_cfg, "clips_per_video", 3) if sourcing_cfg else 3,
    }
    return template.format(**vars_)


def get_user_prompt(concept, material=None) -> str:
    """Return the user prompt, optionally wrapping source material."""
    mode = concept.sourcing.mode if hasattr(concept, "sourcing") else "stock"
    template = USER_TEMPLATES.get(mode, USER_TEMPLATES["stock"])

    vars_ = {"description": concept.description}
    if material and hasattr(material, "text_source") and material.text_source:
        vars_["text_source"] = material.text_source
        vars_["source_title"] = getattr(material, "source_ref", "") or ""
    return template.format(**vars_)
