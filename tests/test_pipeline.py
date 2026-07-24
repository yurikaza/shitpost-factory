"""Integration tests for the full pipeline in fixture/dry-run mode."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from factory.pipeline import produce, produce_all
from factory.config import load_env


@pytest.fixture(autouse=True)
def setup_env(tmp_path):
    """Ensure DRY_RUN=true and clean state for all pipeline tests."""
    os.environ["DRY_RUN"] = "true"
    load_env()
    # Clear state.db to prevent dedupe leaking between tests
    state_db = Path("state.db")
    if state_db.exists():
        state_db.unlink()
    yield
    os.environ.pop("DRY_RUN", None)
    if state_db.exists():
        state_db.unlink()


class TestProduce:
    def test_text_pov_dry_run(self, tmp_path):
        """Full pipeline: text-pov (generated mode)."""
        result = produce("text-pov", publish=False, dry_run=True)
        assert result["error"] is None
        assert result["video"] is not None
        assert result["video"].concept_id == "text-pov"
        assert result["video"].duration_s > 0
        assert result["video"].path.exists()

    def test_fact_bombs_dry_run(self, tmp_path):
        """Full pipeline: fact-bombs (stock mode with fixture clips)."""
        result = produce("fact-bombs", publish=False, dry_run=True)
        assert result["error"] is None
        assert result["video"] is not None
        assert result["video"].concept_id == "fact-bombs"
        assert result["video"].duration_s > 0

    def test_disabled_concept_skipped(self):
        """Disabled concept returns error without crashing."""
        result = produce("reddit-stories", publish=False, dry_run=True)
        assert result["error"] == "disabled"
        assert result["video"] is None

    def test_nonexistent_concept(self):
        """Nonexistent concept returns error."""
        result = produce("nonexistent", publish=False, dry_run=True)
        assert result["error"] is not None

    def test_publish_dry_run(self, tmp_path):
        """Pipeline with publish=True in dry-run mode."""
        result = produce("text-pov", publish=True, dry_run=True)
        assert result["error"] is None
        assert result["video"] is not None
        # Dry-run publish should return fixture results
        assert len(result["publish_results"]) > 0


class TestProduceAll:
    def test_produce_all_dry_run(self, tmp_path):
        """Run all enabled concepts."""
        results = produce_all(publish=False, dry_run=True)
        assert len(results) == 2  # text-pov + fact-bombs
        succeeded = [r for r in results if r["error"] is None]
        assert len(succeeded) == 2
