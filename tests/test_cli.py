from pathlib import Path

from scholar_bib.cli import build_parser
from scholar_bib.scholar import DEFAULT_PROXY_URL


def test_cli_defaults_are_safe_and_visible_browser_oriented(monkeypatch):
    monkeypatch.delenv("SCHOLAR_BIB_PROXY", raising=False)
    args = build_parser().parse_args(["papers.txt"])
    assert args.input == Path("papers.txt")
    assert args.output == Path("references.bib")
    assert args.unmatched == Path("unmatched.tsv")
    assert args.delay_min == 3.0
    assert args.delay_max == 7.0
    assert args.proxy == DEFAULT_PROXY_URL
    assert args.headless is False
    assert args.resume is True


def test_cli_uses_proxy_from_environment(monkeypatch):
    monkeypatch.setenv("SCHOLAR_BIB_PROXY", "socks5h://127.0.0.1:9999")
    args = build_parser().parse_args(["papers.txt"])
    assert args.proxy == "socks5h://127.0.0.1:9999"


def test_cli_accepts_explicit_no_resume_and_headless_modes():
    args = build_parser().parse_args(
        ["papers.txt", "--no-resume", "--headless"]
    )
    assert args.resume is False
    assert args.headless is True
