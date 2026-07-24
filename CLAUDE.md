# CLAUDE.md

Project context for Claude Code. Auto-loaded every session. Keep it short and current.

## What this is

`shitpost-factory` — an automated faceless short-form video pipeline. Sources royalty-free
footage, writes a script with an LLM, renders a 9:16 vertical video with burned-in captions,
and publishes to TikTok / Instagram Reels / YouTube Shorts on a schedule.

Runs unattended every 8 hours. 3 videos/day per account. Multiple accounts, one per "concept".

Language of all published content: English.
Status: greenfield. Nothing is implemented yet.

## Read this first

`docs/research-2026.md` is the full feasibility research behind this project. It contains the
platform policy constraints, API quota numbers, library version gotchas, and the ranked list of
content concepts. **Read it before making architectural decisions.** Do not re-derive things it
already settled.

## Hard constraints (these are not preferences)

1. **No reposting other people's videos.** All three platforms penalise unoriginal/mass-produced
   content. Footage comes from Pexels/Pixabay (CC0) or self-recorded gameplay. Never build on
   yt-dlp scraping of YouTube/TikTok.
2. **No AI-generated video.** Cost and quality. AI is for text (scripts, hooks, hashtags) and TTS only.
3. **CPU-only rendering.** Target hardware is a free-tier VM with ~2 vCPU / 2–4 GB RAM. No GPU.
   If a change makes a render exceed ~5 min for a 60s clip, it is too slow.
4. **Free-tier only.** No paid hosting, no paid APIs beyond negligible LLM token spend.
5. **Every video must be transformative.** Own narration, own captions, own edit. This is what
   keeps accounts monetisable and un-shadowbanned.

## Stack

- Python 3.11+
- **FFmpeg via subprocess** for the final render — this is the primary path, not MoviePy.
  MoviePy 2.x is available for compositing experiments only; note v2 broke the v1 API entirely
  (`from moviepy import ...`, `.with_position()` not `.set_position()`, `TextClip` needs an
  explicit `font=` path to a real .ttf on disk).
- `faster-whisper` for word-level caption timing (use `base` or `small` on CPU).
- Captions burned in via FFmpeg `ass=` filter, generated as `.ass` with `PlayResX=1080`,
  `PlayResY=1920`, thick outline, `margin-v` 120–180 to clear platform UI.
- **Postiz** (self-hosted, already available) is the publishing layer. Prefer calling Postiz over
  implementing TikTok/Meta/YouTube APIs directly.
- LLM: provider-agnostic behind `scripting/llm_client.py`. Default Gemini free tier;
  Xiaomi MiMo (OpenAI-compatible, `https://api.xiaomimimo.com/v1`) is a supported alternative.

## Layout

```
src/factory/
  pipeline.py       orchestrates the 5 stages end to end
  config.py         loads config/settings.yaml + concept YAML + .env
  cli.py            entrypoint: run one concept, one video
  sourcing/         stage 1 — find raw footage / story material
  scripting/        stage 2 — LLM writes hook, script, caption, hashtags
  audio/            stage 3 — TTS narration + SFX/music bed
  render/           stage 4 — FFmpeg compose, captions, 9:16
  publish/          stage 5 — Postiz (primary), direct API clients (fallback)
  state/            dedupe ledger, post history, per-concept metrics
config/concepts/    one YAML per account/concept — the format is data, not code
docs/               research, ADRs
assets/             fonts, background loops, SFX, music (gitignored except .gitkeep)
work/               scratch render dir, cleared after each run (gitignored)
output/             finished MP4s (gitignored)
```

## Conventions

- **Concepts are config, not code.** Adding a new account = adding a YAML file in
  `config/concepts/`. If a new concept requires new Python, the abstraction is wrong.
- Config precedence: concept YAML > `config/settings.yaml` > hardcoded defaults. The
  settings file is gitignored — copy from `config/settings.example.yaml`.
- Every stage takes a dataclass in and returns a dataclass out. No dicts across stage boundaries.
- Every external call (Pexels, LLM, TTS, Postiz) goes through a client module with retry +
  a `--dry-run` mode that returns fixtures. The pipeline must be runnable offline.
- Never commit secrets. Everything sensitive lives in `.env`, mirrored in `.env.example`.
- `state/store.py` must dedupe: never source the same clip or story twice across all concepts.
- Log to `logs/` as JSON lines, one file per run, so failures are debuggable after the fact.

## Publishing gotchas (already researched, do not rediscover)

- TikTok: unaudited apps can only post `SELF_ONLY` (private). Audit takes 2–6 weeks.
  Use Postiz or Creator-Draft mode until approved.
- YouTube: upload quota is ~100 units/call now (not 1600), ~100 uploads/day. But unverified
  apps upload as **private** until the compliance audit passes.
- Instagram: requires a **Business** account (not Creator) + linked Facebook Page + app review
  for `instagram_business_content_publish`. Video must be at a public URL at post time.
  Assume 25 posts/24h.

## Commands

```bash
make setup          # venv + deps + ffmpeg check
make run CONCEPT=x  # produce one video for a concept, no publish
make publish CONCEPT=x
make test
make lint
```

## Deployment

Primary: Oracle Cloud Always Free ARM VM (`scripts/setup_vm.sh`), real cron, Postiz on the
same box. Fallback: `.github/workflows/produce.yml` — note GitHub cron drifts 15–45 min and
scheduled workflows pause after 60 days without a push.

## Definition of done for a video

9:16, 1080x1920, H.264, 15–60s, burned captions readable with sound off, audio normalised to
about -14 LUFS, no black frames at either end, filename includes concept + UTC timestamp.
