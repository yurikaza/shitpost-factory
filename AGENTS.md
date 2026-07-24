# AGENTS.md

Project context for shitpost-factory — automated faceless short-form video pipeline.

## What this is

Automated content generation for TikTok/Instagram Reels/YouTube Shorts. Sources viral
Reddit clips, writes shitpost text with MiMo LLM, renders vertical videos with text
overlays and montage effects, publishes via GitHub Actions.

Status: **working pipeline.** Renders videos end-to-end. Publishing requires social
media API keys.

Language: English. All content is in English.

## Architecture

```
social-media-pipeline/          ← brand folders (one per channel)
  shitpostfactoryhq/            ← first brand
    config/concepts/            ← concept YAML files
    output/                     ← rendered videos (temp)
    work/                       ← temp files
  [future-brand]/               ← add more brands here

src/factory/                    ← shared pipeline code
  cli.py                        ← entrypoint (--brand flag selects brand)
  pipeline.py                   ← orchestrates stages
  config.py                     ← loads brand-specific or default configs
  sourcing/                     ← Reddit video (pullpush.io + yt-dlp), Pexels
  scripting/                    ← MiMo LLM text generation
  render/                       ← Pillow text overlay, FFmpeg montage, compose
  audio/                        ← Edge-TTS narration (optional)
  publish/                      ← social media publishing (TODO)

.github/workflows/              ← GitHub Actions (free for public repos)
  render.yml                    ← reusable workflow template
  meme-bombs.yml                ← every 4 hours
  cursed-edits.yml              ← every 4 hours (30min offset)
  wholesome-unhinged.yml        ← every 4 hours (15min offset)
```

## Key concepts

- **Brand** = a social media channel (e.g., shitpostfactoryhq). Has its own concept configs.
- **Concept** = a content format (e.g., meme-bombs). Defined in YAML under brand folder.
- **Pipeline** = source → script → render → publish. Shared across all brands.

## How to run

```bash
# Single concept for a brand
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run --concept meme-bombs

# All concepts for a brand
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run-all

# With cleanup (delete output after rendering — for CI)
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run --concept meme-bombs --cleanup

# Without brand (uses root config/concepts/)
PYTHONPATH=src python -m factory.cli run --concept fact-bombs
```

## API Keys (shared across all brands)

| Key | Env Var | Purpose |
|-----|---------|---------|
| MiMo token plan | `MIMO_API_KEY` | LLM text generation |
| MiMo endpoint | `MIMO_BASE_URL` | `https://token-plan-sgp.xiaomimimo.com/v1` |
| MiMo model | `MIMO_MODEL` | `mimo-v2.5` |
| Pexels | `PEXELS_API_KEY` | Stock footage (optional) |

## Non-negotiables

1. No reposting — Reddit clips are transformative with text overlay
2. No AI-generated video — AI writes text only
3. CPU-only rendering, free-tier hosting (GitHub Actions)
4. Every video must be transformative

## Adding a brand

1. Create `social-media-pipeline/<brand>/config/concepts/`
2. Add concept YAML files
3. Create GitHub Actions workflows
4. Set up social media accounts
5. Add publishing API keys to GitHub Secrets

## Adding a concept

Add a YAML file to `social-media-pipeline/<brand>/config/concepts/`. The pipeline
auto-discovers all enabled concepts.

## Stack

- Python 3.12
- MiMo (Xiaomi) — LLM for text generation (free token plan)
- Pillow — text overlay rendering
- FFmpeg — video composition, montage effects
- pullpush.io — Reddit content discovery (no API key)
- yt-dlp — video downloading
- Edge-TTS — text-to-speech (free)
- GitHub Actions — free automated scheduling

## Conventions

- Concepts are config, not code — adding a new account = adding a YAML file
- Config precedence: brand concept YAML > root concept YAML > settings.yaml > defaults
- Every stage takes a dataclass in and returns a dataclass out
- Every external call has a dry-run mode that returns fixtures
- Never commit secrets — use .env and GitHub Secrets
- Log to logs/ as JSON lines

## Definition of done for a video

9:16, 1080x1920, H.264, 12-15s (shitpost) or 35-60s (narration), text overlay readable,
audio normalized to -14 LUFS, no black frames, filename includes concept + UTC timestamp.
