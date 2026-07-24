"""Entrypoint.

    python -m factory.cli run --concept fact-bombs
    python -m factory.cli run-all --publish
    python -m factory.cli doctor
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="factory",
    help="Automated faceless short-form video pipeline",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(level: str = "INFO") -> None:
    from factory.logging_config import setup_logging
    setup_logging(level=level)


@app.command()
def run(
    concept: str = typer.Option(..., "--concept", "-c", help="Concept ID to produce"),
    brand: str = typer.Option(None, "--brand", "-b", help="Brand name (uses brands/<brand>/ config)"),
    publish: bool = typer.Option(False, "--publish", "-p", help="Actually publish to platforms"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    cleanup: bool = typer.Option(False, "--cleanup", help="Delete output after rendering"),
) -> None:
    """Produce one video for a single concept."""
    _setup_logging(log_level)
    from factory.pipeline import produce

    # Set brand context
    if brand:
        os.environ["FACTORY_BRAND"] = brand
        console.print(f"[bold]Brand: {brand}[/bold]")

    console.print(f"[bold]Producing concept: {concept}[/bold]")
    result = produce(concept, publish=publish, dry_run=None)

    if result["error"]:
        console.print(f"[red]Failed:[/red] {result['error']}")
        raise typer.Exit(1)

    video = result["video"]
    if video:
        console.print(f"[green]Rendered:[/green] {video.path}")
        console.print(f"  Duration: {video.duration_s:.1f}s")
        size_mb = video.path.stat().st_size / 1024 / 1024
        console.print(f"  Size: {size_mb:.1f} MB")

        # Cleanup: delete output file after rendering (for CI)
        if cleanup:
            video.path.unlink(missing_ok=True)
            console.print("[dim]Cleaned up output file[/dim]")

    if result["publish_results"]:
        console.print("[bold]Publish results:[/bold]")
        for pr in result["publish_results"]:
            status = "[green]ok[/green]" if pr.ok else "[red]failed[/red]"
            console.print(f"  {pr.platform}: {status} (id={pr.post_id})")


@app.command("run-all")
def run_all(
    publish: bool = typer.Option(False, "--publish", "-p", help="Actually publish"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Produce one video for every enabled concept."""
    _setup_logging(log_level)
    from factory.pipeline import produce_all

    console.print("[bold]Producing all enabled concepts...[/bold]")
    results = produce_all(publish=publish, dry_run=None)

    # Summary table
    table = Table(title="Results")
    table.add_column("Concept", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Published")

    for r in results:
        if r["error"]:
            status = f"[red]{r['error'][:30]}[/red]"
            dur = "-"
            pub = "-"
        else:
            video = r["video"]
            status = "[green]ok[/green]"
            dur = f"{video.duration_s:.1f}s" if video else "-"
            pub = str(len(r["publish_results"]))

        table.add_row(r["concept"], status, dur, pub)

    console.print(table)

    failed = sum(1 for r in results if r["error"])
    if failed:
        raise typer.Exit(1)


@app.command()
def doctor() -> None:
    """Check environment: ffmpeg, .env, fonts, config."""
    _setup_logging("WARNING")

    checks = []

    # ffmpeg
    import shutil
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    checks.append(("ffmpeg on PATH", ffmpeg_ok))

    # ffprobe
    ffprobe_ok = shutil.which("ffprobe") is not None
    checks.append(("ffprobe on PATH", ffprobe_ok))

    # .env
    env_ok = Path(".env").exists()
    checks.append((".env exists", env_ok))

    # settings.yaml
    settings_ok = Path("config/settings.yaml").exists()
    checks.append(("config/settings.yaml exists", settings_ok))

    # fonts
    fonts_dir = Path("assets/fonts")
    font_ok = fonts_dir.exists() and any(fonts_dir.glob("*.ttf")) if fonts_dir.exists() else False
    checks.append(("font .ttf in assets/fonts", font_ok))

    # concepts
    from factory.config import list_enabled_concepts
    try:
        enabled = list_enabled_concepts()
        concepts_ok = len(enabled) > 0
        checks.append((f"enabled concepts ({len(enabled)})", concepts_ok))
    except Exception as e:
        checks.append(("enabled concepts", False))

    # Print results
    for label, ok in checks:
        icon = "[green]OK[/green]" if ok else "[red]MISSING[/red]"
        console.print(f"  {icon}  {label}")

    # State DB
    state_db = Path("state.db")
    if state_db.exists():
        console.print(f"  [dim]state.db: {state_db.stat().st_size / 1024:.0f} KB[/dim]")

    all_ok = all(ok for _, ok in checks)
    if not all_ok:
        console.print("\n[yellow]Some checks failed. Run 'make setup' or fix the issues above.[/yellow]")
        raise typer.Exit(1)
    else:
        console.print("\n[green]All checks passed.[/green]")


@app.command()
def concepts() -> None:
    """List all concepts and their status."""
    from factory.config import load_concept, load_settings, list_enabled_concepts

    settings = load_settings()
    enabled_ids = list_enabled_concepts()

    table = Table(title="Concepts")
    table.add_column("ID", style="cyan")
    table.add_column("Enabled")
    table.add_column("Mode")
    table.add_column("Originality")
    table.add_column("Platforms")

    concepts_dir = Path("config/concepts")
    for path in sorted(concepts_dir.glob("*.yaml")):
        try:
            c = load_concept(path.stem, settings)
            enabled = "[green]yes[/green]" if c.enabled else "[dim]no[/dim]"
            table.add_row(
                c.id,
                enabled,
                c.sourcing.mode,
                c.originality_risk,
                ", ".join(c.publish.platforms),
            )
        except Exception as e:
            table.add_row(path.stem, "[red]error[/red]", "-", "-", "-")

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
