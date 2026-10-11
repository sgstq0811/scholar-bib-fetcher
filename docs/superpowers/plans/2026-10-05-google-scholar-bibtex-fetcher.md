# Google Scholar BibTeX Fetcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a visible-browser CLI that reads one paper title per line, retrieves BibTeX from Google Scholar only for strict normalized-title matches, and reports every mismatch or failure.

**Architecture:** Pure Python modules handle normalization, matching, checkpointing, and output generation; an asynchronous Playwright adapter owns Google Scholar page interaction; a thin orchestrator joins them so browser-independent behavior is fully unit-testable. Each paper produces a durable outcome before processing continues, allowing deterministic resume and output rebuilding.

**Tech Stack:** Python 3.11+, Playwright async API, pytest, standard-library `argparse`, `dataclasses`, `difflib`, `json`, `csv`, and atomic `os.replace` writes.

---

## File Map

- `pyproject.toml`: package metadata, runtime dependency, test configuration, and `scholar-bib` entry point.
- `scholar_bib/__init__.py`: package version.
- `scholar_bib/titles.py`: title normalization, input loading, and stable deduplication.
- `scholar_bib/matching.py`: strict match decision and diagnostic similarity.
- `scholar_bib/storage.py`: outcome model, atomic checkpoint, BibTeX validation, and output materialization.
- `scholar_bib/scholar.py`: visible persistent Chromium workflow and Scholar DOM selectors.
- `scholar_bib/app.py`: asynchronous per-title orchestration and progress reporting.
- `scholar_bib/cli.py`: argument parsing and process entry point.
- `tests/`: focused unit tests plus one opt-in local-browser DOM test.
- `README.md`: installation, invocation, outputs, CAPTCHA behavior, and limitations.

### Task 1: Package Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `scholar_bib/__init__.py`
- Create: `tests/test_package.py`

- [ ] **Step 1: Write the failing package test**

```python
from scholar_bib import __version__


def test_package_exposes_version():
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_package.py -v`

Expected: collection fails with `ModuleNotFoundError: No module named 'scholar_bib'`.

- [ ] **Step 3: Add the minimal package files**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "scholar-bib-fetcher"
version = "0.1.0"
description = "Strict-title Google Scholar BibTeX fetcher"
requires-python = ">=3.11"
dependencies = ["playwright>=1.48,<2"]

[project.optional-dependencies]
test = ["pytest>=8,<9", "pytest-asyncio>=0.24,<1"]

[project.scripts]
scholar-bib = "scholar_bib.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["browser: requires an installed Playwright Chromium browser"]
asyncio_mode = "auto"
```

```python
# scholar_bib/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 4: Install test dependencies and verify GREEN**

Run: `python -m pip install -e '.[test]' && python -m pytest tests/test_package.py -v`

Expected: one passing test.

- [ ] **Step 5: Commit if the workspace is placed in a Git repository**

```bash
git add pyproject.toml scholar_bib/__init__.py tests/test_package.py
git commit -m "build: scaffold scholar bib fetcher"
```

The current workspace has no Git repository, so execution records this step as not applicable unless the user initializes one first.

### Task 2: Title Loading and Strict Matching

**Files:**
- Create: `scholar_bib/titles.py`
- Create: `scholar_bib/matching.py`
- Create: `tests/test_titles.py`
- Create: `tests/test_matching.py`

- [ ] **Step 1: Write failing normalization and loading tests**

```python
# tests/test_titles.py
from scholar_bib.titles import load_titles, normalize_title


def test_normalize_title_ignores_case_unicode_punctuation_and_spacing():
    assert normalize_title("  Café—RAG: A Study! ") == "café rag a study"


def test_load_titles_ignores_empty_lines_and_deduplicates_stably(tmp_path):
    path = tmp_path / "papers.txt"
    path.write_text("First Paper\n\nfirst—paper\nSecond Paper\n", encoding="utf-8")
    titles, duplicate_count = load_titles(path)
    assert titles == ["First Paper", "Second Paper"]
    assert duplicate_count == 1
```

- [ ] **Step 2: Run title tests and verify RED**

Run: `python -m pytest tests/test_titles.py -v`

Expected: import failure for `scholar_bib.titles`.

- [ ] **Step 3: Implement normalization and stable deduplication**

```python
# scholar_bib/titles.py
from pathlib import Path
import re
import unicodedata


def normalize_title(title: str) -> str:
    folded = unicodedata.normalize("NFKC", title).casefold()
    spaced = "".join(ch if ch.isalnum() else " " for ch in folded)
    return re.sub(r"\s+", " ", spaced).strip()


def load_titles(path: Path) -> tuple[list[str], int]:
    seen: set[str] = set()
    titles: list[str] = []
    duplicate_count = 0
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        original = raw_line.strip()
        if not original:
            continue
        key = normalize_title(original)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        titles.append(original)
    return titles, duplicate_count
```

- [ ] **Step 4: Verify title tests GREEN**

Run: `python -m pytest tests/test_titles.py -v`

Expected: two passing tests.

- [ ] **Step 5: Write failing strict-match tests**

```python
# tests/test_matching.py
from scholar_bib.matching import compare_titles


def test_accepts_only_equal_normalized_titles():
    result = compare_titles("Attention Is All You Need", "Attention is all you need.")
    assert result.accepted is True
    assert result.similarity == 1.0


def test_rejects_high_similarity_nonidentical_title():
    result = compare_titles("Attention Is All You Need", "Attention Is Almost All You Need")
    assert result.accepted is False
    assert 0.8 < result.similarity < 1.0
```

- [ ] **Step 6: Run matching tests and verify RED**

Run: `python -m pytest tests/test_matching.py -v`

Expected: import failure for `scholar_bib.matching`.

- [ ] **Step 7: Implement the match result**

```python
# scholar_bib/matching.py
from dataclasses import dataclass
from difflib import SequenceMatcher

from .titles import normalize_title


@dataclass(frozen=True)
class MatchResult:
    accepted: bool
    similarity: float


def compare_titles(input_title: str, scholar_title: str) -> MatchResult:
    left = normalize_title(input_title)
    right = normalize_title(scholar_title)
    similarity = round(SequenceMatcher(None, left, right).ratio(), 4)
    return MatchResult(accepted=bool(left) and left == right, similarity=similarity)
```

- [ ] **Step 8: Run the focused and aggregate tests**

Run: `python -m pytest tests/test_titles.py tests/test_matching.py -v`

Expected: four passing tests.

### Task 3: Durable Outcomes and Output Files

**Files:**
- Create: `scholar_bib/storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

```python
import csv

from scholar_bib.storage import Outcome, OutcomeStore, is_valid_bibtex


def test_bibtex_validation_requires_an_entry():
    assert is_valid_bibtex("@article{key, title={A}}") is True
    assert is_valid_bibtex("Access denied") is False


def test_store_round_trips_and_materializes_outputs(tmp_path):
    checkpoint = tmp_path / "progress.jsonl"
    store = OutcomeStore(checkpoint)
    store.put(Outcome("Paper A", "paper a", "Paper A", 1.0, "success", "", "@article{a, title={A}}"))
    store.put(Outcome("Paper B", "paper b", "Different", 0.4, "unmatched", "title mismatch", ""))
    reloaded = OutcomeStore(checkpoint)
    assert [item.status for item in reloaded.items()] == ["success", "unmatched"]

    bib_path = tmp_path / "references.bib"
    unmatched_path = tmp_path / "unmatched.tsv"
    reloaded.materialize(bib_path, unmatched_path)
    assert bib_path.read_text(encoding="utf-8") == "@article{a, title={A}}\n"
    with unmatched_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert rows[0]["input_title"] == "Paper B"
    assert rows[0]["reason"] == "title mismatch"
```

- [ ] **Step 2: Run storage tests and verify RED**

Run: `python -m pytest tests/test_storage.py -v`

Expected: import failure for `scholar_bib.storage`.

- [ ] **Step 3: Implement atomic checkpointing and materialization**

```python
# scholar_bib/storage.py
from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import json
import os
import re
import tempfile


@dataclass(frozen=True)
class Outcome:
    input_title: str
    normalized_title: str
    scholar_title: str
    similarity: float
    status: str
    reason: str
    bibtex: str


def is_valid_bibtex(text: str) -> bool:
    return bool(re.match(r"^\s*@[A-Za-z]+\s*[({]", text))


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class OutcomeStore:
    def __init__(self, checkpoint: Path):
        self.checkpoint = checkpoint
        self._items: dict[str, Outcome] = {}
        if checkpoint.exists():
            for line in checkpoint.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    outcome = Outcome(**json.loads(line))
                    self._items[outcome.normalized_title] = outcome

    def contains(self, normalized_title: str) -> bool:
        return normalized_title in self._items

    def items(self) -> list[Outcome]:
        return list(self._items.values())

    def put(self, outcome: Outcome) -> None:
        self._items[outcome.normalized_title] = outcome
        lines = [json.dumps(asdict(item), ensure_ascii=False) for item in self.items()]
        _atomic_text(self.checkpoint, "\n".join(lines) + "\n")

    def materialize(self, bib_path: Path, unmatched_path: Path) -> None:
        unique: list[str] = []
        seen: set[str] = set()
        for item in self.items():
            bib = item.bibtex.strip()
            if item.status == "success" and bib not in seen:
                seen.add(bib)
                unique.append(bib)
        _atomic_text(bib_path, "\n\n".join(unique) + ("\n" if unique else ""))

        rows = [item for item in self.items() if item.status != "success"]
        unmatched_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{unmatched_path.name}.", dir=unmatched_path.parent, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["input_title", "scholar_title", "similarity", "reason"], delimiter="\t")
                writer.writeheader()
                for item in rows:
                    writer.writerow({name: getattr(item, name) for name in writer.fieldnames})
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, unmatched_path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
```

- [ ] **Step 4: Run storage tests and verify GREEN**

Run: `python -m pytest tests/test_storage.py -v`

Expected: two passing tests.

### Task 4: Scholar Browser Adapter

**Files:**
- Create: `scholar_bib/scholar.py`
- Create: `tests/test_scholar_helpers.py`
- Create: `tests/test_scholar_dom.py`

- [ ] **Step 1: Write failing helper tests**

```python
# tests/test_scholar_helpers.py
from scholar_bib.scholar import clean_result_title, is_captcha_url


def test_clean_result_title_removes_scholar_resource_prefix():
    assert clean_result_title("[PDF] Attention Is All You Need") == "Attention Is All You Need"


def test_detects_google_sorry_page():
    assert is_captcha_url("https://scholar.google.com/sorry/index?continue=x") is True
    assert is_captcha_url("https://scholar.google.com/scholar?q=x") is False
```

- [ ] **Step 2: Run helper tests and verify RED**

Run: `python -m pytest tests/test_scholar_helpers.py -v`

Expected: import failure for `scholar_bib.scholar`.

- [ ] **Step 3: Implement the browser adapter**

```python
# scholar_bib/scholar.py
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus, urljoin
import asyncio
import re

from playwright.async_api import BrowserContext, Page, async_playwright

from .storage import is_valid_bibtex


def clean_result_title(text: str) -> str:
    return re.sub(r"^\s*\[(?:PDF|HTML|BOOK|CITATION)\]\s*", "", text, flags=re.I).strip()


def is_captcha_url(url: str) -> bool:
    return "/sorry/" in url


@dataclass(frozen=True)
class Candidate:
    title: str


class ScholarClient:
    def __init__(self, profile_dir: Path):
        self.profile_dir = profile_dir
        self._playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self):
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self.context = await self._playwright.chromium.launch_persistent_context(
            str(self.profile_dir), headless=False, viewport={"width": 1280, "height": 900}
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if self.context is not None:
            await self.context.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def _wait_for_human_if_captcha(self, page: Page) -> None:
        while is_captcha_url(page.url) or await page.locator("#gs_captcha_f, input[name='captcha']").count() > 0:
            await asyncio.to_thread(input, "Google Scholar 要求验证。请在浏览器完成后按回车继续：")
            await page.wait_for_load_state("domcontentloaded")

    async def search(self, title: str) -> Candidate | None:
        assert self.page is not None
        url = f"https://scholar.google.com/scholar?hl=en&q={quote_plus(chr(34) + title + chr(34))}"
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await self._wait_for_human_if_captcha(self.page)
        rows = self.page.locator(".gs_r.gs_or.gs_scl")
        if await rows.count() == 0:
            return None
        title_text = await rows.first.locator("h3.gs_rt").inner_text()
        return Candidate(clean_result_title(title_text))

    async def fetch_bibtex(self) -> str:
        assert self.page is not None
        first = self.page.locator(".gs_r.gs_or.gs_scl").first
        await first.locator(".gs_or_cit").click()
        dialog = self.page.locator("#gs_cit")
        await dialog.wait_for(state="visible", timeout=30_000)
        link = dialog.locator("a.gs_citi", has_text="BibTeX")
        href = await link.get_attribute("href")
        if not href:
            raise RuntimeError("BibTeX link missing from citation dialog")
        bib_page = await self.context.new_page()  # type: ignore[union-attr]
        try:
            await bib_page.goto(urljoin(self.page.url, href), wait_until="domcontentloaded", timeout=60_000)
            await self._wait_for_human_if_captcha(bib_page)
            text = (await bib_page.locator("body").inner_text()).strip()
        finally:
            await bib_page.close()
        if not is_valid_bibtex(text):
            raise RuntimeError("Scholar returned malformed BibTeX")
        return text
```

- [ ] **Step 4: Run helper tests and verify GREEN**

Run: `python -m pytest tests/test_scholar_helpers.py -v`

Expected: two passing tests.

- [ ] **Step 5: Add the opt-in local DOM test**

```python
# tests/test_scholar_dom.py
import pytest
from playwright.async_api import async_playwright


@pytest.mark.browser
async def test_scholar_selectors_find_first_result_and_cite_control():
    async with async_playwright() as api:
        browser = await api.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content('''
          <div class="gs_r gs_or gs_scl">
            <h3 class="gs_rt">A Paper</h3>
            <a class="gs_or_cit">Cite</a>
          </div>
          <div id="gs_cit"><a class="gs_citi" href="/paper.bib">BibTeX</a></div>
        ''')
        row = page.locator(".gs_r.gs_or.gs_scl").first
        assert await row.locator("h3.gs_rt").inner_text() == "A Paper"
        assert await row.locator(".gs_or_cit").count() == 1
        assert await page.locator("#gs_cit a.gs_citi", has_text="BibTeX").get_attribute("href") == "/paper.bib"
        await browser.close()
```

- [ ] **Step 6: Install Chromium and run the local DOM test**

Run: `python -m playwright install chromium && python -m pytest tests/test_scholar_dom.py -v`

Expected: one passing browser test without contacting Google.

### Task 5: Orchestration and Resume

**Files:**
- Create: `scholar_bib/app.py`
- Create: `tests/test_app.py`

- [ ] **Step 1: Write failing orchestration tests with a fake browser boundary**

```python
# tests/test_app.py
from pathlib import Path

from scholar_bib.app import process_titles
from scholar_bib.scholar import Candidate
from scholar_bib.storage import OutcomeStore


class FakeScholar:
    def __init__(self, candidates, bibtex):
        self.candidates = iter(candidates)
        self.bibtex = bibtex
        self.search_calls = []

    async def search(self, title):
        self.search_calls.append(title)
        return next(self.candidates)

    async def fetch_bibtex(self):
        return self.bibtex


async def test_processes_match_and_records_mismatch(tmp_path):
    client = FakeScholar([Candidate("Paper A"), Candidate("Different")], "@article{a, title={A}}")
    store = OutcomeStore(tmp_path / "progress.jsonl")
    counts = await process_titles(["Paper A", "Paper B"], client, store, 0, 0)
    assert counts == {"success": 1, "unmatched": 1}
    assert [item.status for item in store.items()] == ["success", "unmatched"]


async def test_resume_skips_all_checkpointed_titles(tmp_path):
    client = FakeScholar([Candidate("Paper A")], "@article{a, title={A}}")
    store = OutcomeStore(tmp_path / "progress.jsonl")
    await process_titles(["Paper A"], client, store, 0, 0)
    await process_titles(["Paper A"], client, store, 0, 0)
    assert client.search_calls == ["Paper A"]
```

- [ ] **Step 2: Run orchestration tests and verify RED**

Run: `python -m pytest tests/test_app.py -v`

Expected: import failure for `scholar_bib.app`.

- [ ] **Step 3: Implement orchestration**

```python
# scholar_bib/app.py
from collections import Counter
import asyncio
import random

from .matching import compare_titles
from .storage import Outcome, OutcomeStore
from .titles import normalize_title


async def process_titles(titles, client, store: OutcomeStore, delay_min: float, delay_max: float) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for index, title in enumerate(titles, start=1):
        normalized = normalize_title(title)
        if store.contains(normalized):
            counts["skipped"] += 1
            continue
        print(f"[{index}/{len(titles)}] {title}")
        try:
            candidate = await client.search(title)
            if candidate is None:
                print("  未找到 Scholar 结果")
                outcome = Outcome(title, normalized, "", 0.0, "no_result", "no Scholar result", "")
            else:
                match = compare_titles(title, candidate.title)
                if not match.accepted:
                    print(f"  不匹配: Scholar={candidate.title!r}, similarity={match.similarity:.4f}")
                    outcome = Outcome(title, normalized, candidate.title, match.similarity, "unmatched", "title mismatch", "")
                else:
                    bibtex = await client.fetch_bibtex()
                    outcome = Outcome(title, normalized, candidate.title, match.similarity, "success", "", bibtex)
        except Exception as error:
            print(f"  错误: {error}")
            outcome = Outcome(title, normalized, "", 0.0, "error", str(error), "")
        store.put(outcome)
        counts[outcome.status] += 1
        if index < len(titles) and delay_max > 0:
            await asyncio.sleep(random.uniform(delay_min, delay_max))
    return dict(counts)
```

- [ ] **Step 4: Run orchestration tests and verify GREEN**

Run: `python -m pytest tests/test_app.py -v`

Expected: two passing tests.

### Task 6: Command-Line Interface

**Files:**
- Create: `scholar_bib/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI parser tests**

```python
# tests/test_cli.py
from pathlib import Path

import pytest

from scholar_bib.cli import build_parser


def test_cli_defaults_are_safe_and_visible_browser_oriented():
    args = build_parser().parse_args(["papers.txt"])
    assert args.input == Path("papers.txt")
    assert args.output == Path("references.bib")
    assert args.unmatched == Path("unmatched.tsv")
    assert args.delay_min == 3.0
    assert args.delay_max == 7.0
    assert args.resume is False


def test_cli_accepts_explicit_resume_mode():
    args = build_parser().parse_args(["papers.txt", "--resume"])
    assert args.resume is True
```

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `python -m pytest tests/test_cli.py -v`

Expected: import failure for `scholar_bib.cli`.

- [ ] **Step 3: Implement parsing, validation, execution, and final summary**

```python
# scholar_bib/cli.py
from pathlib import Path
import argparse
import asyncio
import sys

from .app import process_titles
from .scholar import ScholarClient
from .storage import OutcomeStore
from .titles import load_titles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch strict-title BibTeX records from Google Scholar")
    parser.add_argument("input", type=Path, help="UTF-8 text file with one paper title per line")
    parser.add_argument("--output", type=Path, default=Path("references.bib"))
    parser.add_argument("--unmatched", type=Path, default=Path("unmatched.tsv"))
    parser.add_argument("--checkpoint", type=Path, default=Path("progress.jsonl"))
    parser.add_argument("--profile-dir", type=Path, default=Path("work/browser-profile"))
    parser.add_argument("--delay-min", type=float, default=3.0)
    parser.add_argument("--delay-max", type=float, default=7.0)
    parser.add_argument("--resume", action="store_true", help="reuse completed outcomes from checkpoint")
    return parser


async def _run(args) -> int:
    if args.delay_min < 0 or args.delay_max < args.delay_min:
        raise ValueError("delay range must satisfy 0 <= delay-min <= delay-max")
    if args.checkpoint.exists() and not args.resume:
        raise ValueError(f"checkpoint already exists: {args.checkpoint}; pass --resume or choose another --checkpoint")
    titles, duplicates = load_titles(args.input)
    if not titles:
        raise ValueError("input contains no paper titles")
    store = OutcomeStore(args.checkpoint)
    async with ScholarClient(args.profile_dir) as client:
        counts = await process_titles(titles, client, store, args.delay_min, args.delay_max)
    store.materialize(args.output, args.unmatched)
    summary = ", ".join(f"{name}={value}" for name, value in sorted(counts.items()))
    print(f"完成: {summary}, duplicate_input={duplicates}")
    return 0 if not counts.get("error") else 2


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_run(args)))
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f"错误: {error}\n")
    except KeyboardInterrupt:
        print("\n已中断；已完成条目保存在 checkpoint 中。", file=sys.stderr)
        raise SystemExit(130)
```

- [ ] **Step 4: Run CLI tests and full unit suite**

Run: `python -m pytest tests/test_cli.py -v && python -m pytest -m 'not browser' -v`

Expected: CLI tests pass and the complete non-browser suite is green.

### Task 7: Documentation and End-to-End Verification

**Files:**
- Create: `README.md`
- Create: `examples/papers.txt`

- [ ] **Step 1: Add the runnable example input**

```text
Attention Is All You Need
BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding
```

- [ ] **Step 2: Document setup and usage**

```markdown
# Google Scholar BibTeX Fetcher

Reads a UTF-8 text file containing one paper title per line. It accepts only titles that become identical after case, Unicode, punctuation, and whitespace normalization. Every mismatch is printed and written to `unmatched.tsv`.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m playwright install chromium
```

## Run

```bash
scholar-bib examples/papers.txt --output references.bib
```

The visible Chromium window uses `work/browser-profile` by default. If Google presents a CAPTCHA, complete it manually in that window and return to the terminal. Completed outcomes are stored in `progress.jsonl`; rerun with `--resume` to skip completed titles and rebuild `references.bib` plus `unmatched.tsv`.

Use conservative delays for longer lists:

```bash
scholar-bib papers.txt --resume --delay-min 5 --delay-max 12
```

The tool does not bypass Google rate limits or CAPTCHAs. Google Scholar page changes can require selector updates in `scholar_bib/scholar.py`.
```

- [ ] **Step 3: Run static compilation and all automated tests**

Run: `python -m compileall -q scholar_bib tests && python -m pytest -v`

Expected: compilation succeeds and all tests, including the installed local-browser fixture, pass.

- [ ] **Step 4: Check the command help without contacting Google**

Run: `scholar-bib --help`

Expected: exit code 0 and options for output, unmatched report, checkpoint, profile directory, and delay range.

- [ ] **Step 5: Perform the opt-in live smoke test**

Run: `scholar-bib examples/papers.txt --output work/smoke/references.bib --unmatched work/smoke/unmatched.tsv --checkpoint work/smoke/progress.jsonl --delay-min 5 --delay-max 8`

Expected: a visible browser opens; each exact match produces a valid BibTeX entry, mismatches appear in the terminal and TSV, and rerunning with `--resume` skips checkpointed titles. If Scholar presents a CAPTCHA, the run pauses for manual completion rather than bypassing it.

The live smoke test is performed only when network access and user interaction are available; unit and local-browser verification remain the required automated gate.

## Plan Self-Review

- Every design requirement maps to Tasks 2–7: strict matching, visible browser, Cite/BibTeX flow, CAPTCHA pause, randomized delay, checkpoint resume, atomic outputs, mismatch reporting, and tests.
- Module names, `Outcome` fields, `Candidate` fields, and method signatures are consistent across tasks.
- The first version remains scoped to plain-text input and the first organic Scholar result.
- No implementation depends on a paid API or CAPTCHA bypass.
