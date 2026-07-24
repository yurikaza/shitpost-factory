# shitpost-factory

Automated faceless short-form video pipeline. Sources royalty-free footage, writes a script
with an LLM, renders a 9:16 vertical video with burned-in captions, publishes to TikTok /
Instagram Reels / YouTube Shorts every 8 hours.

Status: **working pipeline.** Renders videos end-to-end. Publishing requires API keys and
Postiz setup.

## The five stages

```
1. source   Pexels / Pixabay CC0 footage, or Reddit text        sourcing/
2. script   LLM writes hook, body, title, hashtags              scripting/
3. audio    TTS narration + CC0 music bed + SFX                 audio/
4. render   FFmpeg -> 1080x1920 H.264 + burned captions         render/
5. publish  Postiz -> TikTok, Instagram, YouTube                publish/
```

## Quick start

```bash
cp .env.example .env          # fill in keys
# optionally drop a .ttf into assets/fonts/ for custom caption font
make setup
make check
make run CONCEPT=text-pov     # renders, does not publish
```

## What works

- **text-pov** — generated gradient background + TTS narration + word-by-word captions
- **fact-bombs** — stock footage (Pexels/Pixabay) + TTS facts + burned captions
- **reddit-stories** — Reddit-sourced text over gradient background (disabled by default)
- **satisfying-loops** — stock footage loops (disabled by default)
- Edge-TTS narration (free, no API key)
- FFmpeg-based 9:16 rendering with caption burn-in via ASS subtitles
- Audio normalization to -14 LUFS
- Deduplication across runs (SQLite state store)
- Dry-run mode — renders with fixture data, no network calls needed

## Adding an account

Add a YAML file to `config/concepts/`. That's it. If a new concept needs new Python,
the abstraction is wrong.

## Non-negotiables

1. No reposting other people's videos — CC0 stock or self-recorded only.
2. No AI-generated video — AI writes text and speaks, that's all.
3. CPU-only rendering, free-tier hosting.
4. Every video must be transformative (own narration, own captions, own edit).

Reasoning in `docs/research-2026.md` and `docs/decisions/`.

## Stack

- Python 3.11+
- FFmpeg for rendering (subprocess, not MoviePy)
- faster-whisper for word-level caption timing
- edge-tts for narration (free, no key)
- Postiz for publishing (self-hosted)
- Gemini / MiMo / Ollama for script generation

## Configuration

| Variable | Purpose |
|----------|---------|
| `DRY_RUN` | `true` = render with fixtures, never publish (default) |
| `LLM_PROVIDER` | `gemini` / `mimo` / `ollama` / `groq` |
| `TTS_PROVIDER` | `edge` (free) / `piper` / `mimo` |
| `PEXELS_API_KEY` | 200 req/hr free tier |
| `PIXABAY_API_KEY` | Free tier |
| `POSTIZ_API_KEY` | Self-hosted Postiz instance |

## Deployment

Primary: Oracle Cloud Always Free ARM VM (`scripts/setup_vm.sh`), real cron, Postiz on the
same box. Fallback: `.github/workflows/produce.yml` — note GitHub cron drifts 15–45 min and
scheduled workflows pause after 60 days without a push.

## Layout

```
CLAUDE.md              project context, auto-loaded by Claude Code
docs/research-2026.md  the research this is built on — read before deciding anything
docs/decisions/        ADRs
config/concepts/       one YAML per account
src/factory/           the pipeline
assets/                fonts, backgrounds, sfx, music (contents gitignored)
work/ output/ logs/    runtime, gitignored
```
