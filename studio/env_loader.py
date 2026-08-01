"""Load OPENAI_API_KEY from .env in common locations."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

STUDIO_DIR = Path(__file__).resolve().parent
REPO_DIR = STUDIO_DIR.parent


def load_studio_env(root: Path | None = None, *, verbose: bool = False) -> list[Path]:
    """
    Load .env from (later paths override earlier):
      1) folder above studio/ (repo root)
      2) studio/
      3) current working directory
      4) optional --root
    """
    candidates = [
        REPO_DIR / ".env",
        STUDIO_DIR / ".env",
        Path.cwd() / ".env",
    ]
    if root is not None:
        candidates.append(Path(root).resolve() / ".env")

    loaded: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        load_dotenv(path, override=True)
        loaded.append(resolved)
        if verbose:
            print(f"[env] loaded {resolved}")

    # Also pick up any process-level defaults without a file
    load_dotenv(override=False)
    return loaded
