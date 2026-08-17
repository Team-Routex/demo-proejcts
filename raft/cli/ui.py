"""
raft.cli.ui
~~~~~~~~~~~

Terminal branding and shared Rich helpers for the ``raft`` CLI.

Uses pyfiglet for the banner and Rich for panels/tables. Output stays
ASCII-safe on Windows consoles that are not UTF-8.
"""

from __future__ import annotations

import sys
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

try:
    from pyfiglet import Figlet
except ImportError:  # pragma: no cover
    Figlet = None  # type: ignore[misc, assignment]


def _configure_stdio() -> None:
    """Best-effort UTF-8 for Windows terminals."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_stdio()
console = Console(legacy_windows=False, soft_wrap=True)

# Brand palette — calm cyan / steel
_ACCENT = "cyan"
_MUTED = "bright_black"
_OK = "green"
_BAD = "red"
_WARN = "yellow"

_UTF8 = (getattr(sys.stdout, "encoding", None) or "").lower() in {
    "utf-8",
    "utf8",
    "cp65001",
}
_TICK = "OK" if not _UTF8 else "✔"
_CROSS = "X" if not _UTF8 else "✘"
_BOX = box.ROUNDED if _UTF8 else box.ASCII


def figlet_banner(text: str = "RAFT", *, font: str = "slant") -> str:
    """Return an ASCII banner (falls back to plain text if pyfiglet missing)."""
    if Figlet is None:
        return text
    try:
        return Figlet(font=font, width=80).renderText(text).rstrip()
    except Exception:
        return text


def print_brand(*, subtitle: str | None = None) -> None:
    """Print the Raft figlet header used across commands."""
    from raft import __version__

    banner = figlet_banner("RAFT Framework")
    console.print(Text(banner, style=f"bold {_ACCENT}"))
    line = Text()
    line.append("Raft Framework", style=f"bold {_ACCENT}")
    line.append(f"  v{__version__}", style=_MUTED)
    console.print(line)
    if subtitle:
        console.print(Text(subtitle, style=_MUTED))
    width = min(console.width or 72, 72)
    console.print(Text("-" * width, style=_MUTED))


def print_command_header(title: str, *, detail: str | None = None) -> None:
    """Compact header for a subcommand (banner + title panel)."""
    print_brand()
    body = f"[bold]{title}[/bold]"
    if detail:
        body += f"\n[{_MUTED}]{detail}[/{_MUTED}]"
    console.print(Panel.fit(body, border_style=_ACCENT, padding=(0, 1), box=_BOX))
    console.print()


def print_success(message: str) -> None:
    console.print(f"[{_OK}]{_TICK}[/{_OK}] {message}")


def print_error(message: str) -> None:
    console.print(f"[{_BAD}]{_CROSS}[/{_BAD}] {message}")


def print_hint(message: str) -> None:
    console.print(f"    [{_MUTED}]{message}[/{_MUTED}]")


def print_next_steps(project_name: str) -> None:
    """Show post-init commands in a tidy panel."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style=_MUTED)
    table.add_column(style="bold")
    table.add_row("1.", f"cd {project_name}")
    table.add_row("2.", "uv sync")
    table.add_row("3.", "raft runserver")
    console.print()
    console.print(
        Panel(
            table,
            title="[bold]Next steps[/bold]",
            border_style=_OK,
            padding=(0, 1),
            box=_BOX,
        )
    )


def print_feature_summary(features: dict[str, bool]) -> None:
    """Render selected scaffold features."""
    table = Table(title="Selected features", show_header=True, header_style=f"bold {_ACCENT}")
    table.add_column("Feature")
    table.add_column("Enabled", justify="center")
    for name, enabled in features.items():
        mark = f"[{_OK}]yes[/{_OK}]" if enabled else f"[{_MUTED}]no[/{_MUTED}]"
        table.add_row(name, mark)
    console.print(table)
    console.print()


def print_check_results(checks: list[tuple[str, bool, str]]) -> bool:
    """Print health-check rows. Returns True when all passed."""
    table = Table(show_header=True, header_style=f"bold {_ACCENT}", box=None, pad_edge=False)
    table.add_column("", width=3)
    table.add_column("Check")
    table.add_column("Hint", style=_MUTED)

    all_ok = True
    for label, ok, hint in checks:
        icon = f"[{_OK}]{_TICK}[/{_OK}]" if ok else f"[{_BAD}]{_CROSS}[/{_BAD}]"
        if not ok:
            all_ok = False
        table.add_row(icon, label, hint if not ok and hint else "")

    console.print(table)
    console.print()
    if all_ok:
        console.print(f"[bold {_OK}]All checks passed![/{_OK}]")
    else:
        console.print(f"[{_WARN}]Some checks failed — see hints above.[/{_WARN}]")
    return all_ok


def print_server_banner(*, mode: str, app_path: str, host: str | None, port: int | None) -> None:
    """Announce runserver start."""
    print_brand(subtitle=f"{mode} server")
    info = Table(show_header=False, box=None, padding=(0, 1))
    info.add_column(style=_MUTED)
    info.add_column()
    info.add_row("app", app_path)
    if host:
        info.add_row("host", host)
    if port is not None:
        info.add_row("port", str(port))
    console.print(Panel(info, border_style=_ACCENT, title="uvicorn", box=_BOX))
    console.print()


def confirm(prompt: str, *, default: bool = False) -> bool:
    """Yes/no prompt (Click under the hood for CliRunner tests)."""
    import click

    return click.confirm(f"  {prompt}", default=default)


def prompt_features() -> dict[str, bool]:
    """Interactive feature toggles for ``raft init``."""
    console.print(Text("Configure your project", style=f"bold {_ACCENT}"))
    console.print(Text("Press Enter to accept the default in [brackets].", style=_MUTED))
    console.print()

    return {
        "Pydantic schemas": confirm("Use Pydantic for validation & schemas?", default=True),
        "OpenAPI / Docs": confirm("Enable OpenAPI / Docs?", default=False),
        "ORM (RaftSQL)": confirm("Use ORM (RaftSQL)?", default=False),
        "Task Scheduler": confirm(
            "Use built-in Task Scheduler (auto-detect tasks folder)?",
            default=False,
        ),
        "Middleware starter": confirm(
            "Create custom middleware starter file?", default=False
        ),
        "WebSocket": confirm("Use WebSocket?", default=False),
        ".env file": confirm("Use .env file?", default=False),
    }


def features_to_flags(features: dict[str, bool]) -> dict[str, Any]:
    """Map display labels to scaffold kwargs."""
    return {
        "use_pydantic": features["Pydantic schemas"],
        "use_openapi": features["OpenAPI / Docs"],
        "use_orm": features["ORM (RaftSQL)"],
        "use_scheduler": features["Task Scheduler"],
        "use_middleware_starter": features["Middleware starter"],
        "use_websocket": features["WebSocket"],
        "use_env": features[".env file"],
    }
