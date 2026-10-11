# Public GitHub Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a portable, tested, privacy-safe initial release of `scholar-bib-fetcher` to the confirmed empty public GitHub repository.

**Architecture:** Keep the existing Python package and CLI intact, while moving machine-specific proxy selection to an environment-backed CLI default. Repository hygiene is enforced with `.gitignore`; documentation defines installation, runtime behavior, and responsible-use boundaries.

**Tech Stack:** Python 3.11+, Playwright, pytest, setuptools, Git, GitHub CLI

---

### Task 1: Make proxy configuration portable

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `scholar_bib/scholar.py`
- Modify: `scholar_bib/cli.py`

- [ ] Add a CLI test asserting that the default proxy is empty when `SCHOLAR_BIB_PROXY` is unset and follows the environment variable when set.
- [ ] Run `python -m pytest tests/test_cli.py -v` and confirm the new test fails because the proxy is currently hard-coded.
- [ ] Replace the hard-coded local proxy default with `os.environ.get("SCHOLAR_BIB_PROXY", "")` at parser construction time.
- [ ] Run `python -m pytest tests/test_cli.py -v` and confirm it passes.

### Task 2: Add public repository files and portable documentation

**Files:**
- Create: `.gitignore`
- Create: `LICENSE`
- Modify: `README.md`

- [ ] Add ignore rules for `work/`, `outputs/`, browser data, checkpoints, BibTeX/TSV results, caches, virtual environments, build output, and editable-install metadata.
- [ ] Add the MIT License with copyright `2026 Shangquan Sun`.
- [ ] Replace machine-specific installation paths with `git clone`, virtual environment, and `pip install -e '.[test]'` commands.
- [ ] Document optional `SCHOLAR_BIB_PROXY`/`--proxy`, default direct access, resume behavior, CAPTCHA handling, rate-limit stopping, and responsible use.

### Task 3: Verify package and repository contents

**Files:**
- Verify: all tracked release files

- [ ] Run `python -m pytest -v` and require zero failures.
- [ ] Run `python -m build` and require successful sdist and wheel creation.
- [ ] Run `git status --short --ignored` and verify private/runtime directories are ignored.
- [ ] Stage release files explicitly and inspect `git diff --cached --stat` plus `git ls-files` to ensure no `work/`, `outputs/`, cache, checkpoint, browser-profile, or local-result files are included.

### Task 4: Commit and publish

**Files:**
- Commit: verified tracked files
- Remote: `https://github.com/sunsean21/scholar-bib-fetcher.git`

- [ ] Commit the implementation as `chore: prepare public release`.
- [ ] Add the `origin` remote and push `main` with upstream tracking.
- [ ] Verify with `git status --short --branch`, `git ls-remote origin refs/heads/main`, and `gh repo view sunsean21/scholar-bib-fetcher --json visibility,url,defaultBranchRef`.
