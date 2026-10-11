from pathlib import Path
import argparse
import asyncio
import os
import sys

from .app import process_titles
from .scholar import (
    CaptchaRequired,
    DEFAULT_PROXY_URL,
    ScholarBlocked,
    ScholarClient,
)
from .storage import OutcomeStore
from .titles import load_titles, normalize_title


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch strict-title BibTeX records from Google Scholar"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="UTF-8 text file with one paper title per line",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("references.bib")
    )
    parser.add_argument(
        "--unmatched", type=Path, default=Path("unmatched.tsv")
    )
    parser.add_argument(
        "--checkpoint", type=Path, default=Path("progress.jsonl")
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        default=Path("work/browser-profile"),
        help="dedicated Chrome profile; never use your daily Chrome profile",
    )
    parser.add_argument(
        "--proxy",
        default=os.environ.get("SCHOLAR_BIB_PROXY", DEFAULT_PROXY_URL),
        help=(
            "proxy URL (default: SCHOLAR_BIB_PROXY environment variable or "
            "direct access)"
        ),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="run in the background; rerun visibly if Scholar asks for verification",
    )
    parser.add_argument("--delay-min", type=float, default=3.0)
    parser.add_argument("--delay-max", type=float, default=7.0)
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="reuse completed outcomes from checkpoint (default: enabled)",
    )
    return parser


async def _run(args) -> int:
    if args.delay_min < 0 or args.delay_max < args.delay_min:
        raise ValueError(
            "delay range must satisfy 0 <= delay-min <= delay-max"
        )
    if args.checkpoint.exists() and not args.resume:
        raise ValueError(
            f"checkpoint already exists: {args.checkpoint}; "
            "pass --resume or choose another --checkpoint"
        )

    titles, duplicates = load_titles(args.input)
    if not titles:
        raise ValueError("input contains no paper titles")

    store = OutcomeStore(args.checkpoint)
    active_titles = {normalize_title(title) for title in titles}
    counts: dict[str, int] = {}
    try:
        async with ScholarClient(
            args.profile_dir,
            proxy_url=args.proxy,
            headless=args.headless,
        ) as client:
            counts = await process_titles(
                titles,
                client,
                store,
                args.delay_min,
                args.delay_max,
            )
    finally:
        store.materialize(
            args.output,
            args.unmatched,
            active_titles=active_titles,
        )

    summary = ", ".join(
        f"{name}={value}" for name, value in sorted(counts.items())
    )
    print(f"完成: {summary}, duplicate_input={duplicates}")
    return 0 if not counts.get("error") else 2


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except CaptchaRequired as error:
        parser.exit(3, f"需要人工验证: {error}\n")
    except ScholarBlocked as error:
        parser.exit(4, f"Scholar 已限流: {error}\n")
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"错误: {error}\n")
    except KeyboardInterrupt:
        print(
            "\n已中断；已完成条目保存在 checkpoint 和输出文件中。",
            file=sys.stderr,
        )
        raise SystemExit(130)
