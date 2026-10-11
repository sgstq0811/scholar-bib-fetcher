import csv

from scholar_bib.storage import Outcome, OutcomeStore, is_valid_bibtex


def test_bibtex_validation_requires_an_entry():
    assert is_valid_bibtex("@article{key, title={A}}") is True
    assert is_valid_bibtex("Access denied") is False


def test_store_round_trips_and_materializes_outputs(tmp_path):
    checkpoint = tmp_path / "progress.jsonl"
    store = OutcomeStore(checkpoint)
    store.put(
        Outcome(
            "Paper A",
            "paper a",
            "Paper A",
            1.0,
            "success",
            "",
            "@article{a, title={A}}",
        )
    )
    store.put(
        Outcome(
            "Paper B",
            "paper b",
            "Different",
            0.4,
            "unmatched",
            "title mismatch",
            "",
        )
    )
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


def test_materialize_filters_stale_checkpoint_entries(tmp_path):
    store = OutcomeStore(tmp_path / "progress.jsonl")
    store.put(
        Outcome(
            "Paper A",
            "paper a",
            "Paper A",
            1.0,
            "success",
            "",
            "@article{a, title={A}}",
        )
    )
    store.put(
        Outcome(
            "Ignored summary",
            "ignored summary",
            "",
            0.0,
            "no_result",
            "no Scholar result",
            "",
        )
    )
    bib_path = tmp_path / "references.bib"
    unmatched_path = tmp_path / "unmatched.tsv"
    store.materialize(
        bib_path,
        unmatched_path,
        active_titles={"paper a"},
    )
    assert "@article{a" in bib_path.read_text(encoding="utf-8")
    with unmatched_path.open(encoding="utf-8", newline="") as handle:
        assert list(csv.DictReader(handle, delimiter="\t")) == []
