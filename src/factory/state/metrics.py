"""Per-concept performance tracking, for the kill/keep decision.

Rule from docs/research-2026.md section 8: after ~30 posts, keep a concept if
median views > 2,000-5,000 or any post > 50k. Kill if median < 500.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass

from factory.state.store import Store

log = logging.getLogger(__name__)

# Thresholds from research-2026.md section 8
KEEP_THRESHOLD_VIEWS = 3000       # median views to keep
KILL_THRESHOLD_VIEWS = 500        # median views to kill
VIRAL_THRESHOLD_VIEWS = 50000     # any post exceeding this = keep regardless
MIN_POSTS_FOR_DECISION = 30       # need ~30 posts before evaluating


@dataclass
class ConceptMetrics:
    """Aggregated metrics for one concept."""
    concept_id: str
    total_posts: int
    total_views: int
    median_views: float
    max_views: int
    recommendation: str  # "keep" | "kill" | "insufficient_data"


def evaluate_concept(concept_id: str, store: Store) -> ConceptMetrics:
    """Evaluate whether a concept should be kept or killed.

    This is a placeholder — real view counts would come from platform APIs
    (YouTube Analytics, TikTok Insights, Instagram Insights). For now,
    we track post counts and provide the framework.
    """
    # In a real implementation, this would query platform APIs for view counts.
    # For now, we return a metrics object based on post count alone.
    conn = store._get_conn()
    row = conn.execute(
        "SELECT COUNT(*) FROM posts WHERE concept_id = ? AND status != 'failed'",
        (concept_id,),
    ).fetchone()
    total_posts = row[0] if row else 0

    # Placeholder: real data would come from platform analytics
    total_views = 0
    median_views = 0.0
    max_views = 0

    if total_posts < MIN_POSTS_FOR_DECISION:
        recommendation = "insufficient_data"
    elif max_views >= VIRAL_THRESHOLD_VIEWS:
        recommendation = "keep"
    elif median_views >= KEEP_THRESHOLD_VIEWS:
        recommendation = "keep"
    elif median_views < KILL_THRESHOLD_VIEWS and total_posts >= MIN_POSTS_FOR_DECISION:
        recommendation = "kill"
    else:
        recommendation = "insufficient_data"

    return ConceptMetrics(
        concept_id=concept_id,
        total_posts=total_posts,
        total_views=total_views,
        median_views=median_views,
        max_views=max_views,
        recommendation=recommendation,
    )


def evaluate_all(store: Store, concept_ids: list[str]) -> list[ConceptMetrics]:
    """Evaluate all concepts and return metrics + recommendations."""
    results = []
    for cid in concept_ids:
        metrics = evaluate_concept(cid, store)
        log.info(
            "Concept %s: %d posts, recommendation=%s",
            cid, metrics.total_posts, metrics.recommendation,
        )
        results.append(metrics)
    return results
