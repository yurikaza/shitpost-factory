# Social Media Pipeline

Automated content generation for multiple social media brands/channels.

Each brand has its own folder with concept configs, output directory, and schedule.

## Brands

| Brand | Platform | Status | Concepts |
|-------|----------|--------|----------|
| [shitpostfactoryhq](./shitpostfactoryhq/) | TikTok, IG, YouTube | 🟢 Active | meme-bombs, cursed-edits, wholesome-unhinged |

## How it works

```
social-media-pipeline/
├── shitpostfactoryhq/           ← brand folder
│   ├── config/concepts/         ← concept definitions (YAML)
│   │   ├── meme-bombs.yaml
│   │   ├── cursed-edits.yaml
│   │   └── wholesome-unhinged.yaml
│   ├── output/                  ← rendered videos (temp, cleaned after publish)
│   └── work/                    ← temp files during rendering
├── [future-brand]/              ← add more brands here
│   ├── config/concepts/
│   ├── output/
│   └── work/
└── README.md                    ← this file
```

## Shared resources

All brands share:
- **Source code** (`src/factory/`) — pipeline, rendering, text overlay
- **API keys** (via GitHub Secrets) — MiMo LLM, Pexels
- **GitHub Actions** (`.github/workflows/`) — scheduled rendering
- **Assets** (`assets/`) — fonts, music

## Adding a new brand

1. Create folder: `social-media-pipeline/<brand-name>/`
2. Add concept configs: `config/concepts/*.yaml`
3. Create GitHub Actions workflow: `.github/workflows/<concept>.yml`
4. Add social media account handles to concept YAML
5. Set up publishing API keys in GitHub Secrets

## Running locally

```bash
# Single concept
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run --concept meme-bombs

# All concepts for a brand
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run-all

# With cleanup (delete output after rendering)
PYTHONPATH=src FACTORY_BRAND=shitpostfactoryhq python -m factory.cli run --concept meme-bombs --cleanup
```

## GitHub Actions

Each concept has its own workflow with a cron schedule:
- `meme-bombs.yml` — every 4 hours
- `cursed-edits.yml` — every 4 hours (30min offset)
- `wholesome-unhinged.yml` — every 4 hours (15min offset)

All workflows use `--cleanup` flag to avoid storing videos in artifacts.

## API Keys (shared)

All brands use the same API keys, stored in GitHub Secrets:
- `MIMO_API_KEY` — Xiaomi MiMo LLM (token plan)
- `MIMO_BASE_URL` — MiMo API endpoint
- `MIMO_MODEL` — MiMo model name
- `PEXELS_API_KEY` — Pexels stock footage (optional)
