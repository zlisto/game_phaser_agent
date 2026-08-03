"""CLI: python -m studio path/to/brief.json
   or:  python -m studio --art-from games/rabbit_punch_valley --name rabbit_luna --model gpt-5.6-luna
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from .env_loader import load_studio_env


def _safe_folder_name(name: str) -> str:
    name = name.strip().strip("/\\")
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"Invalid --name (use a single folder segment): {name!r}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise ValueError(
            f"Invalid --name {name!r}; use letters, numbers, ., _, -"
        )
    return name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="2D Game Studio Orchestrator (PydanticAI + Phaser)")
    parser.add_argument("brief", type=Path, nargs="?", help="Path to studio brief JSON")
    parser.add_argument(
        "--art-from",
        type=Path,
        help="Rebuild HTML sprites/sheets from an existing game folder's data/",
    )
    parser.add_argument(
        "--model",
        default="gpt-5.6-luna",
        help="OpenAI model id (default: gpt-5.6-luna). Also accepts openai:…",
    )
    parser.add_argument(
        "--name",
        help="Output folder name under games/ (e.g. rabbit_punch_valley_sol)",
    )
    parser.add_argument("--critic-rounds", type=int, default=1, help="Critic revise rounds (default 1)")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root (default: cwd)",
    )
    args = parser.parse_args(argv)

    # .env from repo root, studio/, cwd, and --root (later overrides)
    load_studio_env(args.root, verbose=True)

    from .agents import configure_model
    from .orchestrator import load_brief, rerun_art_only_sync, run_studio_sync

    model_used = configure_model(args.model)

    out_name: str | None = None
    if args.name:
        try:
            out_name = _safe_folder_name(args.name)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 1

    if args.art_from:
        source_dir = args.art_from if args.art_from.is_absolute() else (args.root / args.art_from)
        source_dir = source_dir.resolve()
        if not (source_dir / "data" / "concept.json").exists():
            print(f"No game data in {source_dir}", file=sys.stderr)
            return 1

        if out_name:
            game_dir = (args.root / "games" / out_name).resolve()
            if game_dir != source_dir:
                game_dir.mkdir(parents=True, exist_ok=True)
                for rel in ("data/concept.json", "data/mechanics.json", "data/levels.json"):
                    src = source_dir / rel
                    if src.exists():
                        dst = game_dir / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                print(f"[out] source={source_dir.name} -> games/{out_name}")
        else:
            game_dir = source_dir
            print(f"[out] overwriting {game_dir}")

        report = rerun_art_only_sync(
            game_dir,
            critic_rounds=args.critic_rounds,
            model=model_used,
        )
    else:
        if not args.brief:
            parser.error("brief JSON required unless --art-from is set")
        if not args.brief.exists():
            print(f"Brief not found: {args.brief}", file=sys.stderr)
            return 1
        brief = load_brief(args.brief)
        brief.critic_rounds = args.critic_rounds
        if out_name:
            brief.output_folder = f"games/{out_name}"
            print(f"[out] games/{out_name}")
        report = run_studio_sync(brief, root=args.root)

    if report.elapsed_human:
        print(f"\nTotal time: {report.elapsed_human}")
    print("\nFiles:")
    for f in report.files_created:
        print(" -", f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
