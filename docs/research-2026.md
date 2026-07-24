# Research: Automated Faceless Short-Form Video System (2026)

> Status: settled research. Treat the facts here as decided unless verified otherwise.
> Verify anything marked **[VOLATILE]** before relying on it.

---

## 0. Executive summary

- Viable path: a portfolio of 4–12 **faceless, template-able** accounts built on royalty-free
  footage (Pexels/Pixabay CC0) with **original narration and captions**. Not reposting.
- Two hard blockers in the original plan:
  1. TikTok's Content Posting API only posts **private** videos until a manual audit passes (2–6 weeks).
  2. Free-tier hosting struggles with scheduled CPU video rendering. GitHub Actions is workable;
     Oracle Cloud Always Free ARM is the real answer.
- Monetisation is realistically 3–18 months out and gated on "originality" rules that specifically
  target mass-produced minimal-edit content. Build for fun now; add transformation to monetise later.

---

## 1. Viral content landscape

### 1.1 Macro numbers

| Metric | Value | Source / date |
|---|---|---|
| YouTube Shorts daily views | 200B+ | Neal Mohan, Cannes Lions, Jun 2025 (up 186% from 70B in Mar 2024) |
| TikTok time/day (global avg) | ~95 min | FT, Q4 2023 |
| TikTok time/day (US adults) | ~52 min | eMarketer, Apr 2025 |
| Reels share of IG time | ~50% | Meta |
| Engagement rate | TikTok ~2.8% · Reels ~0.65% · Shorts ~0.30% | 2024 baselines |
| Multi-platform reach multiplier | 4–5x vs single platform | industry reports |

"Brain rot" was Oxford's 2024 Word of the Year (Dec 2, 2024; 37,000+ votes; +230% usage YoY).

**[VOLATILE]** Some commentary argues absurdist brainrot peaked in 2025 and 2026 is seeing a
partial "intellectual revival" (Substack, longer content, BookTok). Treat absurdist formats as
high-variance and rotate them.

### 1.2 Active niches

- **Italian Brainrot** (Tralalero Tralala, Bombardiro Cocodrilo, Tung Tung Tung Sahur) — surreal
  animal/object hybrids, pseudo-Italian rhyming narration. Canonical versions are AI-generated,
  but the *format* (absurd recurring character + nonsense rhyme + caption) is imitable with
  stock or illustration.
- **"6 7" / "67"** — nonsense catchphrase, big with Gen Alpha.
- **Skibidi Toilet** (DaFuq!?Boom!) — meme-fuelled animated series.
- Low-prop participation trends: "parents reading brainrot words", "propaganda I'm not falling
  for", "the chair".

### 1.3 Faceless account benchmarks

| Account | Scale | Format |
|---|---|---|
| Noah Morris (18 channels) | ~2.5M subs total | faceless automation, sports/crime/celebrity |
| The Infographics Show | ~15M subs | animated explainers |
| WatchMojo | ~26M subs | list videos |
| "Am I the Jerk?" | 1.2M+ subs | Reddit AITA narration + simple visuals |
| @texty.stories.daily | 500k+ followers, 25M+ likes | text-based videos |

Reddit-story channels commonly reach 100k–1M+ subs within a year; individual videos cross 5M
views with 65–80% watch-through.

### 1.4 Automatability tiers

**Highly automatable** — Reddit story → TTS → gameplay background + captions · satisfying loops ·
ranking/"top 5" · text-POV / greentext cards · fact bombs over B-roll · comparison videos.

**Semi-automatable** — meme caption over clip (needs taste + safe source) · reaction-style
(needs commentary to be transformative) · trend-jacking (needs speed + judgement).

**Not automatable** — original skits, opinion/commentary with a voice, character-driven series.

### 1.5 Candidate concepts

| # | Concept | Automatable | Raw material | Originality risk |
|---|---|---|---|---|
| 1 | Reddit stories over gameplay | very high | Reddit text + free-to-use gameplay | **HIGH** — the canonical "minimal transformation" target |
| 2 | Oddly-satisfying loops | high | Pexels/Pixabay CC0 | MEDIUM — saturated |
| 3 | Ranking / Top 5 over B-roll | high | stock + LLM script | MEDIUM |
| 4 | Greentext / text-POV cards | very high | LLM or curated text | LOW–MEDIUM |
| 5 | "Did you know" fact bombs | high | stock B-roll + LLM | LOW–MEDIUM |
| 6 | Original absurdist character series | medium | illustration / CC stock | LOW |
| 7 | Quotes over cinematic stock | very high | stock + music | MEDIUM — saturated |
| 8 | Micro-tutorials / life hacks | med-high | stock or screen record | LOW |
| 9 | "This vs That" comparisons | high | stock + data | LOW–MEDIUM |
| 10 | Screen-recorded internet finds | medium | needs commentary | MEDIUM |

**Launch set: #1, #2, #4, #5** — highest automatability, no filming, defensible originality
provided narration/captions/edit are your own.

---

## 2. Platform policy reality

### 2.1 YouTube — "inauthentic content", July 15, 2025

YouTube updated guidelines "to better identify mass-produced and repetitious content".
Creator Liaison Rene Ritchie framed it as "a minor update to YouTube's longstanding YPP policies".
Explicit target: channels uploading narrated stories with only superficial differences, or
slideshows sharing the same narration. This content was already ineligible for monetisation.

**No change to the reused-content policy** — commentary, clips, compilations and reaction videos
remain permitted. Transformation is the dividing line. AI is not banned; AI-assisted content is
monetisable if it carries unique human value.

A July 2026 clarification added "unsatisfying/offputting content" and "AI personas related to
sensitive topics".

### 2.2 TikTok — Originality Policy

Unoriginal content (copied, or with "minimal original input or edits") is ineligible for the
For You feed and for Creator Rewards, where originality is a scoring input. Reported enforcement
triggers: deleting and reposting your own video, compilations, screen recordings, slideshows,
lightly-edited re-uploads. "Low quality" (split screens, meaningless reactions, slideshows) is
explicitly called out. Repeated flags can permanently revoke monetisation.

### 2.3 Instagram

Penalises aggregators/reposters; down-ranks watermarked content from other apps.
API publishing cap cited as both **25** and **100** posts/24h — plan against 25.
Post 1–3 Reels/day for algorithmic trust.

### 2.4 AI disclosure

| Platform | Requirement | Applies to this project? |
|---|---|---|
| TikTok | C2PA Content Credentials since Jan 2025. Label required for synthetic faces/voices/realistic scenes. **AI-assisted text (scripts, captions, hashtags) is exempt.** | Mostly no |
| YouTube | Disclose "realistic altered or synthetic content". Standard editing/text/AI-assist doesn't trigger. | No |
| Meta/IG | "AI info" labels via C2PA. | No |

TikTok's Fifth Transparency Report: 51,618+ synthetic media videos removed in H2 2025 (+340% YoY);
1.3B+ AI-generated videos labelled.

Since we generate no AI video, disclosure mostly doesn't apply. TTS narration over non-realistic
footage generally does not require the synthetic-media label — but does if you clone a real voice.

### 2.5 What actually happens

Bans are rare for benign meme content. Real consequences are:
(a) demonetisation / rewards ineligibility, (b) reduced distribution ("shadowban"),
(c) removal only for copyright or community-guideline violations.

Aggregators survive by not depending on platform ad revenue (shoutouts, affiliates, driving to a
product) and by adding transformation.

### 2.6 Copyright

- **YouTube Content ID** scans every upload; matches block, mute, or divert monetisation.
- **TikTok** has its own audio/copyright detection; a track cleared on TikTok may be blocked on Reels.
- **"Transformative"** in practice = substantial new expression (narration, commentary, an edit that
  changes purpose). Captions on someone else's clip is not transformative.
- Fair use is a legal defence, not protection from takedown. Platforms enforce more conservatively
  than courts. 3 YouTube strikes = termination.

### 2.7 Automated posting

Permitted via the sanctioned APIs after their reviews. Unofficial automation and watermark-removal
repost tools violate ToS.

---

## 3. Publishing APIs

### 3.1 TikTok Content Posting API

- Needs a developer app **plus** a separate Content Posting audit.
- **Unaudited apps post `SELF_ONLY` (private) only.** Account must be private at post time; owner
  manually flips account and each post to public. True unattended public posting is impossible
  pre-audit.
- Unaudited caps: 5 users / 24h; **6 requests/min** per user token. Access token 24h,
  refresh token 365 days.
- Audit: typically 2–6 weeks (some report 1–2). Clear documented use cases (schedulers, dashboards)
  get approved; vague ones get rejected, adding 1–2 weeks each.
- **No native scheduling parameter** — publish now or draft. Build your own queue.
- Video only, no photo carousels.
- Two modes: **Direct Post** (needs audit for public) and **Creator Draft** (lands in TikTok inbox
  for a human to publish — works without audit).

### 3.2 YouTube Data API v3

- **[VOLATILE]** Dec 4, 2025 revision: upload quota cost dropped from ~1600 units to **~100 units**;
  default allocation ~**100 `videos.insert` calls/day** in a dedicated bucket separate from the
  shared 10,000-unit pool (as of ~Jun 2026). Many 2026 guides still quote 1600 — confirm in your
  own Cloud Console.
- Default 10,000 units/day per project, resets midnight PT. `search` costs 100 units each — avoid.
- **Unverified apps upload as private** until the Audit and Quota Extension passes (manual review,
  weeks–months).
- No monetary cost; quota cannot be purchased, only audited for.

### 3.3 Instagram / Meta Graph API (Reels)

- Requires **Instagram Business** account (Creator accounts are NOT supported — common gotcha),
  linked Facebook Page, Meta developer app, and approved `instagram_business_content_publish`
  (replaced older scopes Jan 27, 2025).
- App review 2–4 weeks per submission, with a screencast of the full flow.
- Container model: `POST /{ig-user-id}/media` (media_type=REELS, public `video_url`) → poll
  container status until FINISHED → `POST /{ig-user-id}/media_publish`.
- Media must sit at a **publicly accessible URL** at post time.
- Reels eligibility: 9:16, 5–90s, H.264/HEVC.
- Rate limit 25 (some sources 100) posts/24h; Reels+Stories+Feed share the bucket.

### 3.4 Third-party posting layers

**Postiz** — open source (AGPL-3.0), self-hostable with no feature gap vs hosted, ~29–32k GitHub
stars. Supports 30+ platforms including TikTok, Instagram, YouTube, Facebook, Reddit, Threads, X,
Pinterest, Bluesky, Mastodon, Discord. Has a public API, NodeJS SDK, n8n node, Make.com integration,
and an **MCP server**. Self-hosted is genuinely free.

It uses official platform OAuth, so it does **not** bypass TikTok's audit or Meta's app review —
but it removes the burden of implementing each API, chunked uploads, token refresh, and multi-step
flows. Paid tier channel counts: Standard 5, Team 10, Pro 30, Ultimate 100.

Alternatives: Upload-Post (unlimited posts, tight profile limits), Ayrshare (per-profile),
Blotato, Post for Me (~$10/1,000 posts), Zernio/PostEverywhere. Pre-audited platforms are
effectively "rent someone else's approved TikTok app" — fastest route to public posting.

**Decision: use self-hosted Postiz as the publishing layer.**

---

## 4. Sourcing

### 4.1 Recommended sources

| Source | License | Limits |
|---|---|---|
| **Pexels API** | Pexels License (CC0-style), commercial OK, no attribution | 200 req/hr, 20,000/mo (liftable free with attribution) |
| **Pixabay API** | Pixabay License, commercial OK, no attribution | unlimited advertised; must download to your own server, no permanent hotlinking |
| Videvo / Mixkit / Coverr | per-clip tiers — check | — |
| Internet Archive | public domain (verify per item) | good for retro/absurdist montage |
| Wikimedia Commons | PD/CC, needs attribution handling | rich metadata |

**Primary source: Pexels. Secondary: Pixabay.**

### 4.2 Reddit

Posting to Reddit does **not** transfer copyright — the uploader (or a third party) still owns it.
Reddit's user agreement grants Reddit a license, not you. Using Reddit *video* without permission
is exactly what gets flagged and DMCA'd. Reddit *text* is lower risk (still credit; some subs
require permission) but must still be transformed via your own narration and captions.

### 4.3 Gameplay backgrounds

Minecraft parkour / Subway Surfers / GTA loops are widely published as free-to-use for exactly this
purpose. Use clips explicitly labelled free-to-use / no-copyright, or record your own.

### 4.4 Trend discovery

No clean official API. Practical: TikTok Creative Center, YouTube trending pages, Reddit API
(`/r/<sub>/top`), tools like Virlo. Scraping TikTok/YouTube beyond official APIs violates ToS.

### 4.5 yt-dlp — stated plainly

yt-dlp is legal open-source software (Unlicense). Downloading from YouTube **violates YouTube's
ToS** — a contract matter (remedy: ban or civil action), not automatically criminal. The real
exposure is **copyright**: re-publishing others' video without permission is infringement
(US statutory damages up to $150k/work if wilful). Safe uses: your own content, public domain,
explicit CC with attribution.

Also technically fragile: YouTube's 2025 anti-download measures (PoToken/SABR) frequently break
yt-dlp, requiring cookies/token-provider plugins.

**Do not build the pipeline on yt-dlp scraping. Use stock APIs.**

---

## 5. Rendering

### 5.1 Library choice

- **MoviePy 2.0** — current, and it broke the v1 API completely. No compatibility shim.
  Effects moved from functions to classes. Import path is now `from moviepy import ...`
  (not `moviepy.editor`). `TextClip` requires an explicit `font=` path to a real OpenType file on
  disk — **on Linux there is no system font resolution, you must ship a .ttf**. Renames:
  `.set_position` → `.with_position`, `.set_duration` → `.with_duration`.
- **ffmpeg-python** — thin Pythonic wrapper; fine for transcode/filters.
- **Direct FFmpeg subprocess** — most reliable and fastest. Most production pipelines end up here.
  **This is our primary path.**

### 5.2 Captions

**faster-whisper** (CTranslate2 reimplementation of Whisper, ~4x faster, lower memory, runs on CPU
with `--device cpu`).

Pipeline: FFmpeg extracts audio → faster-whisper transcribes with word timestamps → generate `.ass`
→ FFmpeg burns in with `-vf "ass=captions.ass"`.

For word-by-word "brainrot captions": ASS file with `PlayResX=1080`, `PlayResY=1920`, white text,
thick black outline (outline 7–9), `margin-v` 120–180 to clear platform UI.

On CPU use `base` or `small`. Whisper `turbo` (~8x faster than large-v3) is the sweet spot with GPU.

### 5.3 Resource envelope

A 30–60s 1080x1920 render with burned captions on CPU: **~1–5 minutes** depending on cores and
complexity. faster-whisper on `base`/`small` transcribes ~1 min of audio in well under a minute on
CPU. RAM ~1–2 GB baseline, spikes with MoviePy compositing + Whisper.

**Target: ≥2 GB RAM, 2 vCPU. No GPU required.** Fits GitHub Actions runners (7 GB / 2 vCPU) and
Oracle ARM comfortably.

### 5.4 Audio

| Source | License | Note |
|---|---|---|
| Pixabay | Pixabay License, commercial OK, no attribution | **primary — music + SFX** |
| Mixkit | free SFX/music | |
| Freesound | per-sound CC — some CC0, some require attribution | check each |
| YouTube Audio Library | free, some require attribution | |
| Uppbeat / Free Music Archive | per-track terms | |

"Royalty-free" ≠ cleared on every platform. Prefer CC0/Pixabay and bake pre-cleared audio into the
render — platform-native audio libraries are not available via API.

---

## 6. Hosting

Workload: CPU-heavy render + network I/O, ~3 runs/day per account.

| Option | Verdict |
|---|---|
| **Oracle Cloud Always Free (ARM Ampere A1)** | **Best.** Up to 4 OCPU / 24 GB RAM free forever. Real always-on VM, real cron, install ffmpeg. Caveat: notorious "out of capacity" for ARM in popular regions — use a creation-retry script. |
| **GitHub Actions** | **Best zero-setup free option.** 2,000 min/mo private, unlimited on public repos. `schedule:` cron, 6h job limit. ffmpeg installable. **Caveats: cron is imprecise (15–45+ min delays) and scheduled workflows auto-pause after 60 days without a push.** ~35 min/day for 3 accounts fits easily. |
| **Google Cloud Run Jobs** | Good serverless route. Generous free tier, Cloud Scheduler for cron, ffmpeg works in your container. Watch egress. |
| Fly.io / Heroku | No real free tier anymore. |
| Railway / Render | Credit/trial based; Render free has cold starts and limited hours. Built-in cron but constrained CPU. |
| PythonAnywhere | Free tier is **daily only** (not every 8h) + manual 3-month renewal. Unsuitable. |
| Hugging Face Spaces | Demo-oriented, sleeps, ToS mismatch. Poor fit. |
| Replit | Always-on requires paid. |

**Recommended architecture: one Oracle ARM VM running (a) the Python render script on cron and
(b) self-hosted Postiz. All free. GitHub Actions as fallback if Oracle capacity is unavailable.**

---

## 7. LLM choice

### 7.1 Xiaomi MiMo

Family launched Apr 2025 (MiMo-7B). V2 series deprecated ~Jun 30, 2026. Current API lineup:

| Model | Params | Context | Price (in/out per M) |
|---|---|---|---|
| MiMo-V2.5-Pro | ~1.02T total / 42B active (sparse MoE) | 1M | $0.435 / $0.87 |
| MiMo-V2.5 | 310B total / 15B active, **omnimodal** (text/image/video/audio) | 1M | $0.14 / $0.28 |
| MiMo-V2.5-ASR | speech recognition | — | — |
| MiMo TTS series | **[VOLATILE]** free for a limited time | — | — |

Prices reflect a May 27, 2026 cut. Historical figures that still circulate: $1/$3 was the
deprecated **V2-Pro**; $0.10/$0.30 was **V2-Flash** at its Dec 16, 2025 launch.

Open weights (MIT): MiMo-7B, MiMo-VL-7B (vision), MiMo-Embodied-7B, V2.5 weights.
Self-hostable via vLLM/SGLang (Xiaomi maintains a vLLM fork; V2.5 has an official SGLang FP8
cookbook). Downloads at `huggingface.co/XiaomiMiMo`.

**Access:** official console `platform.xiaomimimo.com` (login via Xiaomi ID; `sk-...` key).
Base URL `https://api.xiaomimimo.com/v1` (OpenAI-compatible) and `/anthropic`
(Anthropic-compatible). Supported by LiteLLM as `xiaomi_mimo/<model>`.
**`xiaomi-mimo-ai.com` and `mimo-v2.com` are unofficial — do not get keys there.**
Also on OpenRouter (~$0.14/$0.28 for V2.5, ~$0.35/$0.70 for V2.5-Pro).

MiMo-7B runs on ~8 GB+ RAM (INT4 quant available) — could run on the Oracle ARM VM.

### 7.2 Comparison for this task

| Option | Cost | Vision | Verdict for this project |
|---|---|---|---|
| **Gemini free tier (2.x Flash)** | free | yes (image + video) | **Best default.** Free, multimodal, well documented. |
| Xiaomi MiMo V2.5 | $0.14/$0.28 | yes (omnimodal) | Fine and very cheap. Use if you want MiMo. |
| Groq | free/cheap | limited | Extremely fast for high-throughput caption/hook generation. |
| DeepSeek | very cheap | no | Strong text/reasoning. |
| Qwen | cheap / self-host | yes (Qwen-VL) | Solid alternative. |
| Local via Ollama | free | varies | Zero marginal cost on the Oracle VM, no rate limits, private. Slower/weaker but fine for captions and hooks. |

Captions, hooks, hashtags and concept selection are easy text tasks — any of these is capable.
At 3 videos/day across a few accounts, token spend is negligible regardless of choice.

**Verdict:** Gemini free tier as primary, local Ollama as zero-cost fallback, MiMo as a supported
option. There is no capability reason MiMo is required — it's a cost-justified preference.
Keep the LLM behind an interface so this is a config change.

---

## 8. Rollout plan

**Stage 0 — model the problem.** "Single script, fully unattended, all 3 platforms, free hosting"
is achievable but not on day one, because of the TikTok audit and Meta app review. Also: prefer a
small modular pipeline over one script — far easier to debug and to run per-account.

**Stage 1 — build and test locally (week 1–2).**
Pick 4 concepts (#1 Reddit-story, #2 satisfying loops, #4 text-POV, #5 fact bombs). Build
source → script → TTS → render → captions. Render locally, measure time and quality.

**Stage 2 — publishing (week 2–4).**
YouTube first (easiest API; complete the audit). Instagram next (Business account + Page + app
review). TikTok via Creator-Draft or Postiz while your own audit is pending.

**Stage 3 — deploy (week 3–4).**
Oracle ARM VM: ffmpeg + Python + Postiz + cron every 8h. GitHub Actions if Oracle capacity fails.

**Stage 4 — scale and measure.**
One account per concept, 3 posts/day for 3–4 weeks.
**Kill/keep after ~30 posts:** keep if median >2,000–5,000 views or any post >50k.
Kill if median <500. Watch for unoriginal-content flags as a transformation signal.

**Stage 5 — monetisation (month 3+).**
Only for accounts that cleared the view threshold *and* pass originality. Diversify beyond ad
revenue (affiliate, shoutouts, own product) — ad revenue is the most originality-gated.

**Thresholds that change the plan:**
- TikTok audit rejected twice → commit to Postiz/third-party or Creator-Draft only.
- Render >10 min/video or RAM ceiling hit → smaller Whisper model, pre-cache stock, move to Oracle.
- "Inauthentic/unoriginal" strike → increase transformation immediately or retire the concept.

---

## 9. Caveats

- **[VOLATILE] numbers.** The YouTube quota change (1600 → ~100 units, Dec 4 2025; dedicated upload
  bucket ~Jun 2026) is in Google's official revision history, but 2026 guides still cite 1600 —
  confirm in your Cloud Console. Instagram's per-day cap is cited as both 25 and 100 — verify via
  the `content_publishing_limit` endpoint.
- **MiMo churn.** Lineup and prices changed several times in 12 months. Verify at
  platform.xiaomimimo.com before committing. Some performance claims are Xiaomi marketing.
- **Originality enforcement is opaque.** False-positive flags on 100% original content are
  reported; appeals are inconsistent. Treat monetisation as uncertain.
- **Third-party posting tools track shifting APIs.** Postiz maintainers describe TikTok/Instagram
  integrations as "a moving target".
- **Legal.** Reposting others' clips and yt-dlp scraping both violate ToS and risk copyright
  liability. Stock-API + original narration is the defensible path.
- **Not legal advice.** If revenue becomes material, consult a media/IP attorney.
