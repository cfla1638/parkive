import typer
import subprocess
from datetime import datetime
from pathlib import Path

git_app = typer.Typer()

def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
        text=True,
    )

def _rollback_to_head(cwd: Path, start_head: str) -> None:
    # Use --mixed to avoid discarding user files while restoring branch history.
    subprocess.run(
        ["git", "reset", "--mixed", start_head],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )

@git_app.command("sync")
def git_sync(ctx: typer.Context):
    """Synchronize the local repository with the remote."""
    parkive_root = Path(ctx.obj["parkive_root"])

    try:
        start_head = _run_git(["rev-parse", "HEAD"], cwd=parkive_root).stdout.strip()
    except subprocess.CalledProcessError as e:
        typer.echo(e.stderr.strip() or str(e), err=True)
        raise typer.Exit(code=1)

    try:
        _run_git(["add", "."], cwd=parkive_root)
        _run_git(["commit", "--amend", "--no-edit"], cwd=parkive_root)
        _run_git(["push", "origin", "main", "--force"], cwd=parkive_root)
    except subprocess.CalledProcessError as e:
        _rollback_to_head(parkive_root, start_head)
        typer.echo("sync failed and local branch has been rolled back.", err=True)
        typer.echo(e.stderr.strip() or str(e), err=True)
        raise typer.Exit(code=1)

    typer.echo("sync finished.")

@git_app.command("snapshot")
def git_snapshot(ctx: typer.Context):
    """Create a snapshot commit with current date."""
    parkive_root = Path(ctx.obj["parkive_root"])

    try:
        start_head = _run_git(["rev-parse", "HEAD"], cwd=parkive_root).stdout.strip()
    except subprocess.CalledProcessError as e:
        typer.echo(e.stderr.strip() or str(e), err=True)
        raise typer.Exit(code=1)

    current_date = datetime.now().strftime("%Y-%m-%d")
    snapshot_message = f"snapshot:{current_date}"

    try:
        _run_git(["commit", "--amend", "-m", snapshot_message], cwd=parkive_root)
        _run_git(["commit", "--allow-empty", "-m", "latest"], cwd=parkive_root)
        _run_git(["push", "-f"], cwd=parkive_root)
    except subprocess.CalledProcessError as e:
        _rollback_to_head(parkive_root, start_head)
        typer.echo("snapshot failed and local branch has been rolled back.", err=True)
        typer.echo(e.stderr.strip() or str(e), err=True)
        raise typer.Exit(code=1)

    typer.echo("snapshot finished.")
