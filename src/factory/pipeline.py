"""Stage orchestration. The only place that knows the full order of operations.

    source -> script -> audio -> render -> publish

Each stage is swappable and independently testable. Failures are recorded to the
run ledger so a partial run can be resumed rather than restarted.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from factory.audio.mixer import duck_music_under_narration, mix_sfx
from factory.audio.sfx import find_music, find_sfx_batch
from factory.audio.tts import build_tts
from factory.config import load_concept, load_settings, list_enabled_concepts
from factory.publish.base import Publisher
from factory.publish.instagram import InstagramPublisher
from factory.publish.postiz import PostizPublisher
from factory.publish.r2_upload import R2Uploader
from factory.publish.tiktok import TikTokPublisher
from factory.publish.youtube import YouTubePublisher
from factory.render.compose import compose_video
from factory.scripting.llm_client import build_client
from factory.scripting.writer import write_script
from factory.sourcing.base import FootageProvider
from factory.sourcing.dedupe import DedupeGuard
from factory.sourcing.archive_org import ArchiveOrgProvider
from factory.sourcing.pexels import PexelsProvider
from factory.sourcing.pixabay import PixabayProvider
from factory.sourcing.reddit_text import RedditTextProvider
from factory.state.store import Store
from factory.types import AudioTrack, Concept, SourcedMaterial

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_WORK_DIR = _PROJECT_ROOT / "work"


def _build_provider(name: str, dry_run: bool = False) -> FootageProvider:
    """Build a footage provider by name."""
    providers = {
        "pexels": lambda: PexelsProvider(dry_run=dry_run),
        "pixabay": lambda: PixabayProvider(dry_run=dry_run),
        "archive-org": lambda: ArchiveOrgProvider(dry_run=dry_run),
    }
    builder = providers.get(name)
    if builder is None:
        raise ValueError(f"Unknown footage provider: {name}")
    return builder()


def _build_publishers(concept: Concept, dry_run: bool = False) -> list[Publisher]:
    """Build publishers for a concept's configured platforms."""
    publishers = []
    layer = os.getenv("PUBLISH_LAYER", "direct")  # postiz | direct

    if layer == "postiz":
        publishers.append(PostizPublisher(dry_run=dry_run))
    else:
        platform_map = {
            "youtube": lambda: YouTubePublisher(dry_run=dry_run),
            "tiktok": lambda: TikTokPublisher(dry_run=dry_run),
            "instagram": lambda: InstagramPublisher(
                dry_run=dry_run,
                r2_uploader=R2Uploader(),
            ),
        }
        for platform in concept.publish.platforms:
            builder = platform_map.get(platform)
            if builder:
                publishers.append(builder())

    return publishers


# ---------------------------------------------------------------------------
# Stage 1: Sourcing
# ---------------------------------------------------------------------------

def _stage_source(
    concept: Concept,
    store: Store,
    dedupe: DedupeGuard,
    dry_run: bool = False,
) -> SourcedMaterial:
    """Source footage or text material for one concept."""
    log.info("Stage 1: sourcing for concept=%s mode=%s", concept.id, concept.sourcing.mode)

    if concept.sourcing.mode == "reddit-text":
        reddit = RedditTextProvider(dry_run=dry_run)
        material = reddit.fetch_post(
            subreddit=concept.sourcing.subreddits[0] if concept.sourcing.subreddits else "tifu",
            min_upvotes=concept.sourcing.min_upvotes,
            max_body_chars=concept.sourcing.max_body_chars,
        )
        if material is None:
            raise RuntimeError(f"No Reddit post found for concept={concept.id}")
        # Dedupe the text source
        source_hash = RedditTextProvider.hash_text(material.text_source or "")
        if not dedupe.is_source_new(source_hash):
            raise RuntimeError(f"Reddit source already used: {source_hash}")
        dedupe.mark_source_used(source_hash, concept.id)
        material.concept_id = concept.id
        return material

    if concept.sourcing.mode == "generated":
        # No footage needed — concept generates its own visuals (e.g. gradient background)
        return SourcedMaterial(concept_id=concept.id, clips=[], text_source=None)

    if concept.sourcing.mode == "reddit-video":
        # Fetch short video clips from Reddit subreddits
        from factory.sourcing.reddit_video import RedditVideoProvider
        reddit = RedditVideoProvider(dry_run=dry_run)
        all_clips = []
        subreddits = concept.sourcing.subreddits or ["funny"]
        for sub in subreddits:
            found = reddit.search(
                subreddit=sub,
                limit=concept.sourcing.clips_per_video,
                min_upvotes=concept.sourcing.min_upvotes,
                max_duration_s=concept.sourcing.max_duration_s,
                min_duration_s=getattr(concept.sourcing, 'min_duration_s', 3),
            )
            new_clips = dedupe.filter_new_clips(found, concept.id)
            all_clips.extend(new_clips)
            if len(all_clips) >= concept.sourcing.clips_per_video:
                break

        if not all_clips:
            raise RuntimeError(f'No Reddit video clips found for concept={concept.id}')

        # Download clips
        work_dir = _WORK_DIR / concept.id / "clips"
        work_dir.mkdir(parents=True, exist_ok=True)
        downloaded = []
        for clip in all_clips[:concept.sourcing.clips_per_video]:
            try:
                local = reddit.download(clip, work_dir)
                clip.local_path = local
                downloaded.append(clip)
            except Exception as e:
                log.warning('Download failed for %s: %s', clip.external_id, e)

        if not downloaded:
            raise RuntimeError(f'All Reddit downloads failed for concept={concept.id}')

        dedupe.mark_clips_used(downloaded, concept.id)
        return SourcedMaterial(
            concept_id=concept.id,
            clips=downloaded,
            text_source=None,
            source_ref=None,
        )

    # Stock footage mode: search + download from providers
    clips = []
    queries = concept.sourcing.queries or [concept.description]
    for query in queries[:concept.sourcing.clips_per_video]:
        for provider_name in concept.sourcing.providers:
            provider = _build_provider(provider_name, dry_run=dry_run)
            found = provider.search(query, limit=2)
            # Dedupe
            new_clips = dedupe.filter_new_clips(found, concept.id)
            clips.extend(new_clips)

    if not clips:
        raise RuntimeError(f"No clips found for concept={concept.id}")

    # Download clips
    work_dir = _WORK_DIR / concept.id / "clips"
    work_dir.mkdir(parents=True, exist_ok=True)
    downloaded = []
    for clip in clips[:concept.sourcing.clips_per_video]:
        provider = _build_provider(clip.provider, dry_run=dry_run)
        try:
            local = provider.download(clip, work_dir)
            clip.local_path = local
            downloaded.append(clip)
        except Exception as e:
            log.warning("Download failed for %s: %s", clip.external_id, e)

    if not downloaded:
        raise RuntimeError(f"All downloads failed for concept={concept.id}")

    # Mark as used
    dedupe.mark_clips_used(downloaded, concept.id)

    return SourcedMaterial(
        concept_id=concept.id,
        clips=downloaded,
        text_source=None,
        source_ref=None,
    )


# ---------------------------------------------------------------------------
# Stage 2: Scripting
# ---------------------------------------------------------------------------

def _stage_script(
    concept: Concept,
    material: SourcedMaterial,
    dry_run: bool = False,
):
    """Generate script via LLM."""
    log.info("Stage 2: scripting for concept=%s", concept.id)
    client = build_client(dry_run=dry_run)
    return write_script(concept, material, client)


# ---------------------------------------------------------------------------
# Stage 3: Audio
# ---------------------------------------------------------------------------

def _stage_audio(
    concept: Concept,
    script,
    dry_run: bool = False,
) -> AudioTrack:
    """Generate TTS narration, find music/SFX, mix together."""
    log.info("Stage 3: audio for concept=%s narration=%s", concept.id, concept.audio.narration)

    work_dir = _WORK_DIR / concept.id / "audio"
    work_dir.mkdir(parents=True, exist_ok=True)

    narration_path = None
    music_path = None
    sfx_paths = []

    # TTS narration
    if concept.audio.narration:
        tts = build_tts(dry_run=dry_run)
        narration_text = f"{script.hook}. {script.body}"
        narration_path = work_dir / "narration.wav"
        tts.synthesize(narration_text, narration_path)

    # Music bed
    if concept.audio.music_mood:
        found_music = find_music(concept.audio.music_mood)
        if found_music:
            music_path = work_dir / f"music_{found_music.name}"
            import shutil
            shutil.copy2(found_music, music_path)

    # SFX
    if concept.audio.sfx:
        sfx_paths = find_sfx_batch(concept.audio.sfx)

    # Mix: narration + music
    mixed_path = work_dir / "mixed.wav"
    if narration_path and music_path:
        mixed_path = duck_music_under_narration(
            narration_path, music_path, mixed_path,
            music_gain_db=concept.audio.music_gain_db,
        )
    elif narration_path:
        mixed_path = narration_path
    elif music_path:
        mixed_path = music_path
    else:
        # No audio at all — return empty track
        return AudioTrack(narration_path=None, music_path=None, sfx_paths=[], duration_s=0.0)

    # Overlay SFX
    if sfx_paths:
        final_path = work_dir / "final_audio.wav"
        final_path = mix_sfx(mixed_path, sfx_paths, final_path)
    else:
        final_path = mixed_path

    # Get duration
    from factory.render.ffmpeg_utils import get_duration
    duration = get_duration(final_path) if final_path.exists() else 0.0

    return AudioTrack(
        narration_path=narration_path,
        music_path=final_path,
        sfx_paths=sfx_paths,
        duration_s=duration,
    )


# ---------------------------------------------------------------------------
# Stage 4: Render
# ---------------------------------------------------------------------------

def _stage_render(
    concept: Concept,
    material: SourcedMaterial,
    script,
    audio: AudioTrack,
) -> "RenderedVideo":
    """Compose final video."""
    log.info("Stage 4: rendering for concept=%s", concept.id)
    return compose_video(material, script, audio, concept)


# ---------------------------------------------------------------------------
# Stage 5: Publish
# ---------------------------------------------------------------------------

def _stage_publish(
    concept: Concept,
    video: "RenderedVideo",
    script,
    dry_run: bool = False,
) -> list:
    """Publish to configured platforms."""
    log.info("Stage 5: publishing for concept=%s platforms=%s",
             concept.id, concept.publish.platforms)

    publishers = _build_publishers(concept, dry_run=dry_run)
    results = []
    for pub in publishers:
        try:
            result = pub.publish(video, script)
            results.append(result)
            log.info("  %s: ok=%s", pub.platform, result.ok)
        except Exception as e:
            log.error("  %s: failed: %s", pub.platform, e)
        finally:
            pub.close()

    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def produce(
    concept_id: str,
    publish: bool = False,
    dry_run: bool | None = None,
) -> dict:
    """Run all five stages for one concept and produce exactly one video.

    Args:
        concept_id: The concept to produce.
        publish: Whether to actually publish (or just render).
        dry_run: Override DRY_RUN env var. None = use env.

    Returns:
        Dict with keys: concept, video (RenderedVideo or None), publish_results, error.
    """
    import os
    from factory.config import load_env

    load_env()
    settings = load_settings()
    try:
        concept = load_concept(concept_id, settings)
    except FileNotFoundError:
        return {"concept": concept_id, "video": None, "publish_results": [], "error": f"concept not found: {concept_id}"}

    if not concept.enabled:
        log.warning("Concept %s is disabled, skipping", concept_id)
        return {"concept": concept_id, "video": None, "publish_results": [], "error": "disabled"}

    if dry_run is None:
        dry_run = os.getenv("DRY_RUN", "true").lower() in ("true", "1", "yes")

    store = Store(_PROJECT_ROOT / "state.db")
    dedupe = DedupeGuard(store, window_days=concept.sourcing.dedupe_window_days)
    run_id = store.start_run(concept_id)

    try:
        # Stage 1: Source
        material = _stage_source(concept, store, dedupe, dry_run=dry_run)

        # Stage 2: Script
        script = _stage_script(concept, material, dry_run=dry_run)

        # Stage 3: Audio
        audio = _stage_audio(concept, script, dry_run=dry_run)

        # Stage 4: Render
        video = _stage_render(concept, material, script, audio)

        store.finish_run(run_id, "rendered")

        # Stage 5: Publish
        publish_results = []
        if publish:
            publish_results = _stage_publish(concept, video, script, dry_run=dry_run)
            store.finish_run(run_id, "published")
        else:
            store.finish_run(run_id, "rendered")

        log.info(
            "Pipeline complete: concept=%s video=%s duration=%.1fs",
            concept_id, video.path.name, video.duration_s,
        )

        return {
            "concept": concept_id,
            "video": video,
            "publish_results": publish_results,
            "error": None,
        }

    except Exception as e:
        log.error("Pipeline failed at concept=%s: %s", concept_id, e, exc_info=True)
        store.finish_run(run_id, "failed", error=str(e))
        return {
            "concept": concept_id,
            "video": None,
            "publish_results": [],
            "error": str(e),
        }
    finally:
        store.close()


def produce_all(publish: bool = False, dry_run: bool | None = None) -> list[dict]:
    """Run the pipeline for every enabled concept. What cron calls.

    Iterates concepts sequentially to respect CPU/memory budget on 2-vCPU hardware.
    """
    import os
    from factory.config import load_env

    load_env()
    enabled = list_enabled_concepts()
    log.info("produce_all: %d enabled concepts: %s", len(enabled), enabled)

    results = []
    for concept_id in enabled:
        result = produce(concept_id, publish=publish, dry_run=dry_run)
        results.append(result)

        # Rate limit: stagger between concepts
        if result["error"] is None and concept_id != enabled[-1]:
            stagger = int(load_settings().get("publishing", {}).get("stagger_minutes", 5))
            if stagger > 0 and publish:
                log.info("Staggering %d minutes before next concept", stagger)
                time.sleep(stagger * 60)

    # Summary
    succeeded = sum(1 for r in results if r["error"] is None)
    log.info("produce_all complete: %d/%d succeeded", succeeded, len(results))
    return results
