"""CLI entry point for the Manim renderer.

Usage
-----
  python -m mathstudio_renderer health
  python -m mathstudio_renderer list-templates
  python -m mathstudio_renderer validate fixtures/hello.json
  python -m mathstudio_renderer render fixtures/hello.json
  python -m mathstudio_renderer inspect-output output/hello
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import orjson
import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import config
from .errors import RenderError
from .logging import configure_logging
from .registry import REGISTRY
from .schemas import RenderRequest

app = typer.Typer(
    name="mathstudio-renderer",
    help="Dockerized Manim Renderer Runtime — M2-B3.1",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True, style="bold red")


def _setup_logging(json_logs: bool = False) -> None:
    configure_logging(config.log_level, "json" if json_logs else config.log_format)


@app.callback()
def main(
    json_logs: Annotated[bool, typer.Option("--json-logs", help="Force JSON log output")] = False,
) -> None:
    _setup_logging(json_logs)


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------
@app.command()
def health(
    deep: Annotated[bool, typer.Option("--deep", help="Run deep smoke render")] = False,
) -> None:
    """Check renderer health: Python, Manim, FFmpeg, LaTeX, fonts, disk."""
    from .health import run_health_checks

    ok, results = run_health_checks(deep=deep)

    table = Table(title=f"Renderer Health  [v{__version__}]", expand=True)
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Detail")

    for r in results:
        status_style = "green" if r["status"] == "ok" else "red"
        table.add_row(
            r["name"],
            f"[{status_style}]{r['status']}[/{status_style}]",
            str(r.get("detail", "")),
        )

    console.print(table)

    if not ok:
        # Some hard checks failed
        hard_fails = [
            r
            for r in results
            if r["status"] != "ok" and r["name"] not in {"latex", "dvisvgm", "font_noto_sans"}
        ]
        if hard_fails:
            err_console.print("\n[FAIL] Critical health checks failed.")
            raise typer.Exit(1)
        else:
            console.print(
                "\n[yellow]WARNING[/yellow] Soft checks failed (LaTeX/font). "
                "MathTex / Vietnamese renders may not work outside Docker."
            )


# ---------------------------------------------------------------------------
# list-templates
# ---------------------------------------------------------------------------
@app.command(name="list-templates")
def list_templates(
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON")] = False,
) -> None:
    """List all registered render templates."""
    entries = REGISTRY.to_dict()

    if json_output:
        sys.stdout.buffer.write(orjson.dumps(entries, option=orjson.OPT_INDENT_2))
        sys.stdout.buffer.write(b"\n")
        return

    table = Table(title="Registered Templates", expand=True)
    table.add_column("Code", style="cyan bold")
    table.add_column("Version")
    table.add_column("Description")
    table.add_column("Formats")
    table.add_column("Qualities")
    table.add_column("Ratios")

    for e in entries:
        table.add_row(
            e["code"],
            e["version"],
            e["description"],
            ", ".join(e["supported_formats"]),
            ", ".join(e["supported_qualities"]),
            ", ".join(e["supported_aspect_ratios"]),
        )
    console.print(table)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
@app.command()
def validate(
    fixture: Annotated[Path, typer.Argument(help="Path to request JSON fixture")],
) -> None:
    """Validate a render request fixture against the schema."""
    if not fixture.exists():
        err_console.print(f"[FAIL] File not found: {fixture}")
        raise typer.Exit(1)

    try:
        raw = json.loads(fixture.read_text())
        req = RenderRequest.model_validate(raw)
        console.print(
            f"[green]✓ VALID[/green]  request_id={req.request_id!r} "
            f"template={req.template_code!r} quality={req.quality!r}"
        )
    except Exception as exc:
        err_console.print(f"[FAIL] Schema validation error: {exc}")
        raise typer.Exit(1) from None


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
@app.command()
def render(
    fixture: Annotated[Path, typer.Argument(help="Path to request JSON fixture")],
    timeout: Annotated[
        float | None, typer.Option("--timeout", help="Override timeout seconds")
    ] = None,
) -> None:
    """Render a fixture file and write artifacts to output/."""
    if not fixture.exists():
        err_console.print(f"[FAIL] File not found: {fixture}")
        raise typer.Exit(1)

    try:
        raw = json.loads(fixture.read_text())
        request = RenderRequest.model_validate(raw)
    except Exception as exc:
        err_console.print(f"[FAIL] Invalid request: {exc}")
        raise typer.Exit(1) from None

    from .runtime import Renderer
    from .subprocess_runner import RenderSubprocessRunner
    from .workspace import WorkspaceManager

    ws = WorkspaceManager(config.workspace_dir, config.output_dir)
    runner = RenderSubprocessRunner(timeout or config.default_timeout)

    renderer = Renderer(workspace_manager=ws, subprocess_runner=runner)

    console.print(
        f"Rendering [cyan]{request.template_code}[/cyan] (request_id={request.request_id!r}) …"
    )

    try:
        result = renderer.render(request)
    except RenderError as exc:
        err_console.print(f"[FAIL] {exc.code}: {exc.message}")
        raise typer.Exit(1) from None

    console.print(
        f"[green]✓ DONE[/green]  elapsed={result.elapsed_ms:.0f}ms  output={result.output_dir}"
    )
    for name, info in result.artifacts.items():
        console.print(f"  • {name}  {info.size_bytes:,} bytes  {info.mime_type}")


# ---------------------------------------------------------------------------
# inspect-output
# ---------------------------------------------------------------------------
@app.command(name="inspect-output")
def inspect_output(
    output_dir: Annotated[Path, typer.Argument(help="Output directory to inspect")],
) -> None:
    """Inspect a rendered output directory."""
    if not output_dir.exists():
        err_console.print(f"[FAIL] Directory not found: {output_dir}")
        raise typer.Exit(1)

    meta_path = output_dir / "metadata.json"
    if not meta_path.exists():
        err_console.print(f"[FAIL] metadata.json not found in {output_dir}")
        raise typer.Exit(1)

    meta = orjson.loads(meta_path.read_bytes())
    console.print_json(json.dumps(meta))

    console.print("\nFiles in output directory:")
    for f in sorted(output_dir.iterdir()):
        size = f.stat().st_size if f.is_file() else 0
        console.print(f"  {f.name:30s}  {size:>10,} bytes")
