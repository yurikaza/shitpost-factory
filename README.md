# shitpost-factory

Automated faceless short-form video pipeline. Sources viral Reddit clips, writes shitpost
text with MiMo LLM, renders vertical videos with text overlays and montage effects,
publishes to TikTok / Instagram Reels / YouTube Shorts.

Status: **working pipeline.** Renders videos end-to-end via GitHub Actions. Publishing
requires social media API keys.

## How it works

```
1. source   Reddit clips (pullpush.io + yt-dlp) or stock footage
2. script   MiMo LLM writes shitpost text overlay
3. render   Pillow text → FFmpeg montage (zoom/speed/cuts) → 9:16 vertical
4. publish  → TikTok, Instagram, YouTube
```

## Quick start

```bash
cp .env.example .env          # fill in API keys
pip install -r requirements.txt

# Render one concept
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run --concept meme-bombs

# Render all concepts for a brand
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run-all

# Check setup
PYTHONPATH=src python -m factory.cli doctor
```

## Brands

Each brand/channel has its own folder under `social-media-pipeline/`:

```
social-media-pipeline/
├── shitpostfactoryhq/          ← first brand
│   ├── config/concepts/
│   │   ├── meme-bombs.yaml     ← viral Reddit clips + shitpost text
│   │   ├── cursed-edits.yaml   ← bizarre clips + unhinged text
│   │   └── wholesome-unhinged.yaml ← wholesome clips + chaotic text
│   ├── output/
│   └── work/
└── [your-next-brand]/          ← add more brands here
```

## Concepts (shitpostfactoryhq)

| Concept | Source | Tone | Duration |
|---------|--------|------|----------|
| `meme-bombs` | Reddit clips (15 subs) | Unhinged shitpost | 15s |
| `cursed-edits` | Reddit clips (10 subs) | Deeply disturbed | 12s |
| `wholesome-unhinged` | Reddit clips (6 subs) | War documentary on cute things | 15s |

## GitHub Actions (free hosting)

Automated rendering via GitHub Actions — **free for public repos**:

| Workflow | Schedule | Concept |
|----------|----------|---------|
| `meme-bombs.yml` | Every 4 hours | meme-bombs |
| `cursed-edits.yml` | Every 4 hours (30min offset) | cursed-edits |
| `wholesome-unhinged.yml` | Every 4 hours (15min offset) | wholesome-unhinged |

All workflows use `--cleanup` flag — no videos stored in artifacts.

### Required GitHub Secrets

| Secret | Value |
|--------|-------|
| `MIMO_API_KEY` | MiMo token plan API key |
| `MIMO_BASE_URL` | `https://token-plan-sgp.xiaomimimo.com/v1` |
| `MIMO_MODEL` | `mimo-v2.5` |
| `PEXELS_API_KEY` | Pexels API key (optional, for stock footage concepts) |

## Adding a new brand

1. Create folder: `social-media-pipeline/<brand-name>/config/concepts/`
2. Add concept YAML files (copy from shitpostfactoryhq as template)
3. Create GitHub Actions workflow: `.github/workflows/<concept>.yml`
4. Set up social media accounts
5. Add publishing API keys to GitHub Secrets

## Adding a new concept

Add a YAML file to `social-media-pipeline/<brand>/config/concepts/`. The pipeline
auto-discovers all enabled concepts.

## Stack

- **Python 3.12** — pipeline orchestration
- **MiMo (Xiaomi)** — LLM for shitpost text generation (free token plan)
- **Pillow** — text overlay rendering (Impact font, white + black outline)
- **FFmpeg** — video composition, montage effects, format conversion
- **pullpush.io** — Reddit content discovery (no API key needed)
- **yt-dlp** — video downloading from Reddit/Imgur
- **Edge-TTS** — text-to-speech (free, for narration concepts)
- **GitHub Actions** — free automated scheduling and rendering

## Non-negotiables

1. No reposting other people's videos — Reddit clips are transformative with text overlay
2. No AI-generated video — AI writes text only
3. CPU-only rendering, free-tier hosting
4. Every video must be transformative

## Layout

```
.github/workflows/         GitHub Actions (scheduled rendering)
social-media-pipeline/     brand folders (configs, output, work)
src/factory/               shared pipeline code
assets/                    fonts, music (gitignored contents)
config/                    default concept configs (fallback)
docs/                      research, decisions
```

## API Keys

| Key | Purpose | Free? |
|-----|---------|-------|
| MiMo token plan | LLM text generation | ✅ Free tier |
| Pexels | Stock footage | ✅ 200 req/hr |
| Reddit (pullpush.io) | Content discovery | ✅ No key needed |
| Edge-TTS | Text-to-speech | ✅ Free |
