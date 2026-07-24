"""Tests for scripting layer: LLM client, templates, writer."""
from __future__ import annotations

import pytest

from factory.scripting.llm_client import FixtureLLMClient, build_client
from factory.scripting.templates import get_system_prompt, get_user_prompt
from factory.scripting.writer import write_script
from factory.types import Concept, SourcedMaterial


class TestFixtureLLMClient:
    def test_complete(self, llm_client):
        result = llm_client.complete("system", "user")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_complete_json(self, llm_client):
        result = llm_client.complete_json("system", "user", schema={})
        assert isinstance(result, dict)
        assert "hook" in result
        assert "body" in result
        assert "hashtags" in result


class TestBuildClient:
    def test_fixture_client(self):
        client = build_client(dry_run=True)
        assert isinstance(client, FixtureLLMClient)

    def test_fixture_by_name(self):
        client = build_client(provider="fixture")
        assert isinstance(client, FixtureLLMClient)


class TestTemplates:
    def test_system_prompt_stock(self, fact_bombs_concept):
        prompt = get_system_prompt(fact_bombs_concept)
        assert "hook" in prompt.lower()
        assert "clip_queries" in prompt.lower()

    def test_system_prompt_generated(self, text_pov_concept):
        prompt = get_system_prompt(text_pov_concept)
        assert "hook" in prompt.lower()

    def test_user_prompt_stock(self, fact_bombs_concept):
        prompt = get_user_prompt(fact_bombs_concept)
        assert fact_bombs_concept.description in prompt

    def test_user_prompt_reddit(self, reddit_stories_concept, sample_sourced_material):
        prompt = get_user_prompt(reddit_stories_concept, sample_sourced_material)
        assert "Reddit" in prompt
        assert sample_sourced_material.text_source in prompt


class TestWriter:
    def test_write_script_stock(self, fact_bombs_concept, llm_client):
        material = SourcedMaterial(concept_id="fact-bombs", clips=[])
        script = write_script(fact_bombs_concept, material, llm_client)
        assert script.hook != ""
        assert script.body != ""
        assert len(script.hashtags) > 0

    def test_write_script_generated(self, text_pov_concept, llm_client):
        material = SourcedMaterial(concept_id="text-pov", clips=[])
        script = write_script(text_pov_concept, material, llm_client)
        assert script.hook != ""

    def test_hook_word_limit(self, fact_bombs_concept, llm_client):
        material = SourcedMaterial(concept_id="fact-bombs", clips=[])
        script = write_script(fact_bombs_concept, material, llm_client)
        max_words = fact_bombs_concept.script.hook_max_words
        assert len(script.hook.split()) <= max_words
