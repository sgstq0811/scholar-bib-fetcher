from scholar_bib.matching import compare_titles


def test_accepts_only_equal_normalized_titles():
    result = compare_titles("Attention Is All You Need", "Attention is all you need.")
    assert result.accepted is True
    assert result.similarity == 1.0


def test_rejects_high_similarity_nonidentical_title():
    result = compare_titles("Attention Is All You Need", "Attention Is Almost All You Need")
    assert result.accepted is False
    assert 0.8 < result.similarity < 1.0


def test_accepts_normalized_similarity_above_099():
    result = compare_titles(
        "Archunyuan-Video-7B: Structured Video Comprehension of Real-World Shorts",
        "Arc-hunyuan-video-7b: Structured video comprehension of real-world shorts",
    )
    assert result.similarity > 0.99
    assert result.accepted is True
