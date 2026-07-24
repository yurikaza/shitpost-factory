# 2. FFmpeg subprocess as the primary render path

Date: 2026-07-24
Status: accepted

## Context

Two options for programmatic video assembly: MoviePy (Pythonic, high level) or
direct FFmpeg subprocess calls. Target hardware is a free-tier 2-vCPU box with
no GPU, and the render budget is ~5 minutes for a 60s vertical video.

MoviePy 2.x also broke its entire v1 API with no compatibility shim, and its
TextClip requires an explicit font file path with no system font resolution on
Linux - a class of bug that only appears on the deployment box.

## Decision

FFmpeg via subprocess is the primary path. MoviePy stays in requirements for
compositing experiments but is not on the critical path.

## Consequences

More verbose filter graphs. In exchange: predictable memory, much faster renders,
and failures that reproduce locally because we log the exact command.
