from scholar_bib.app import process_titles
import pytest

from scholar_bib.scholar import Candidate, CaptchaRequired
from scholar_bib.storage import Outcome, OutcomeStore


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


class CaptchaScholar:
    async def search(self, title):
        raise CaptchaRequired("rerun headed")


class ErrorScholar:
    async def search(self, title):
        raise RuntimeError("temporary failure")


async def test_processes_match_and_records_mismatch(tmp_path):
    client = FakeScholar(
        [Candidate("Paper A"), Candidate("Different")],
        "@article{a, title={A}}",
    )
    store = OutcomeStore(tmp_path / "progress.jsonl")
    counts = await process_titles(
        ["Paper A", "Paper B"], client, store, 0, 0
    )
    assert counts == {"success": 1, "unmatched": 1}
    assert [item.status for item in store.items()] == [
        "success",
        "unmatched",
    ]


async def test_resume_skips_all_checkpointed_titles(tmp_path):
    client = FakeScholar(
        [Candidate("Paper A")], "@article{a, title={A}}"
    )
    store = OutcomeStore(tmp_path / "progress.jsonl")
    await process_titles(["Paper A"], client, store, 0, 0)
    await process_titles(["Paper A"], client, store, 0, 0)
    assert client.search_calls == ["Paper A"]


async def test_captcha_stops_without_checkpointing_current_title(tmp_path):
    store = OutcomeStore(tmp_path / "progress.jsonl")
    with pytest.raises(CaptchaRequired):
        await process_titles(["Paper A"], CaptchaScholar(), store, 0, 0)
    assert store.items() == []


async def test_resume_retries_previous_error_outcome(tmp_path):
    store = OutcomeStore(tmp_path / "progress.jsonl")
    store.put(
        Outcome(
            "Paper A",
            "paper a",
            "",
            0.0,
            "error",
            "temporary failure",
            "",
        )
    )
    client = FakeScholar(
        [Candidate("Paper A")], "@article{a, title={A}}"
    )
    counts = await process_titles(["Paper A"], client, store, 0, 0)
    assert counts == {"success": 1}
    assert store.items()[0].status == "success"


async def test_resume_retries_old_unmatched_outcome_now_above_threshold(tmp_path):
    input_title = (
        "Archunyuan-Video-7B: Structured Video Comprehension of Real-World Shorts"
    )
    scholar_title = (
        "Arc-hunyuan-video-7b: Structured video comprehension of real-world shorts"
    )
    store = OutcomeStore(tmp_path / "progress.jsonl")
    store.put(
        Outcome(
            input_title,
            "archunyuan video 7b structured video comprehension of real world shorts",
            scholar_title,
            0.993,
            "unmatched",
            "title mismatch",
            "",
        )
    )
    client = FakeScholar(
        [Candidate(scholar_title)],
        "@article{arc, title={Arc Hunyuan}}",
    )
    counts = await process_titles([input_title], client, store, 0, 0)
    assert counts == {"success": 1}
    assert store.items()[0].status == "success"


async def test_resume_retries_previous_no_result_outcome(tmp_path):
    store = OutcomeStore(tmp_path / "progress.jsonl")
    store.put(
        Outcome(
            "Audiovisual LLM for Video Understanding",
            "audiovisual llm for video understanding",
            "",
            0.0,
            "no_result",
            "no Scholar result",
            "",
        )
    )
    client = FakeScholar(
        [Candidate("Audiovisual LLM for Video Understanding")],
        "@article{avllm, title={Audiovisual LLM}}",
    )
    counts = await process_titles(
        ["Audiovisual LLM for Video Understanding"],
        client,
        store,
        0,
        0,
    )
    assert counts == {"success": 1}
    assert store.items()[0].status == "success"
