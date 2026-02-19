from typing import Annotated
from pathlib import Path
from datetime import datetime
from rich.console import Console
from .config import success_style, error_style, info_style

import typer
import subprocess


git_app = typer.Typer(no_args_is_help=True)
console = Console()


def _git_cmd_text(args: list[str]) -> str:
    return "git " + " ".join(args)


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    cmd_text = _git_cmd_text(args)
    with console.status(
        f"[bold cyan]Running:[/] {cmd_text}",
        spinner="circle",
    ):
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(cwd),
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.CalledProcessError:
            console.print(f"[red]✗[/red] {cmd_text}")
            raise
    console.print(f"[green]✓[/green] {cmd_text}")
    return result


def _rollback_to_head(cwd: Path, start_head: str) -> None:
    # Use --mixed to avoid discarding user files while restoring branch history.
    args = ["reset", "--mixed", start_head]
    cmd_text = _git_cmd_text(args)
    with console.status(
        f"[bold cyan]Running:[/] {cmd_text}",
        spinner="circle",
    ):
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if result.returncode == 0:
        console.print(f"[green]✓[/green] {cmd_text}")
    else:
        console.print(f"[red]✗[/red] {cmd_text}")


@git_app.command("sync")
def git_sync(ctx: typer.Context):
    """Synchronize the local repository with the remote."""
    parkive_root = Path(ctx.obj["parkive_root"])

    try:
        start_head = _run_git(["rev-parse", "HEAD"], cwd=parkive_root).stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(e.stderr.strip() or str(e), style=error_style)
        raise typer.Exit(code=1)

    try:
        _run_git(["add", "."], cwd=parkive_root)
        _run_git(["commit", "--amend", "--no-edit"], cwd=parkive_root)
        _run_git(["push", "origin", "main", "--force"], cwd=parkive_root)
    except subprocess.CalledProcessError as e:
        _rollback_to_head(parkive_root, start_head)
        console.print("sync failed and local branch has been rolled back.", style=error_style)
        console.print(e.stderr.strip() or str(e), style=error_style)
        raise typer.Exit(code=1)

    console.print("sync finished.", style=success_style)


@git_app.command("snapshot")
def git_snapshot(ctx: typer.Context, message: Annotated[str | None, typer.Option("--message", "-m", help="Message for the snapshot commit")] = None):
    """Create a snapshot commit with the current state of the repository. This will create a new commit with the specified message (or a default message with the current date if not provided) and push it to the remote repository. The previous commit will be amended to keep the history clean."""
    parkive_root = Path(ctx.obj["parkive_root"])

    try:
        start_head = _run_git(["rev-parse", "HEAD"], cwd=parkive_root).stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(e.stderr.strip() or str(e), style=error_style)
        raise typer.Exit(code=1)

    snapshot_message: str = message
    if message is None:
        current_date = datetime.now().strftime("%Y-%m-%d")
        snapshot_message = f"snapshot:{current_date}"

    try:
        _run_git(["add", "."], cwd=parkive_root)
        _run_git(["commit", "--amend", "--allow-empty", "-m", snapshot_message], cwd=parkive_root)
        _run_git(["commit", "--allow-empty", "-m", "latest"], cwd=parkive_root)
        _run_git(["push", "-f"], cwd=parkive_root)
    except subprocess.CalledProcessError as e:
        _rollback_to_head(parkive_root, start_head)
        console.print("snapshot failed and local branch has been rolled back.", style=error_style)
        console.print(e.stderr.strip() or str(e), style=error_style)
        raise typer.Exit(code=1)

    console.print("snapshot finished.", style=success_style)
