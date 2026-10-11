from scholar_bib.titles import load_titles, normalize_title


def test_normalize_title_ignores_case_unicode_punctuation_and_spacing():
    assert normalize_title("  Café—RAG: A Study! ") == "café rag a study"


def test_load_titles_ignores_empty_lines_and_deduplicates_stably(tmp_path):
    path = tmp_path / "papers.txt"
    path.write_text("First Paper\n\nfirst—paper\nSecond Paper\n", encoding="utf-8")
    titles, duplicate_count = load_titles(path)
    assert titles == ["First Paper", "Second Paper"]
    assert duplicate_count == 1


def test_load_titles_ignores_known_summary_sentence(tmp_path):
    path = tmp_path / "papers.txt"
    path.write_text(
        "Paper A\n"
        "Qwen-related / Omni-related references above account for the remaining "
        "unique merged entries after title normalization.\n",
        encoding="utf-8",
    )
    titles, duplicate_count = load_titles(path)
    assert titles == ["Paper A"]
    assert duplicate_count == 0
