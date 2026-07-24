# 1. Record architecture decisions

Date: 2026-07-24
Status: accepted

## Context

This project has several decisions that are expensive to revisit and easy to
forget the reasoning for (footage sourcing, render library, publishing layer,
hosting). Claude Code sessions start fresh; without a written record it will
re-litigate settled questions.

## Decision

Use lightweight ADRs in `docs/decisions/`. One file per decision, numbered.
Never delete one - supersede it.

## Consequences

`CLAUDE.md` stays short and points here for reasoning.
