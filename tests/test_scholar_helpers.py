from scholar_bib.scholar import (
    clean_result_title,
    ensure_proxy_available,
    best_title_match,
    is_blocked_text,
    is_captcha_url,
    playwright_proxy,
    scholar_search_queries,
)


def test_clean_result_title_removes_scholar_resource_prefix():
    assert (
        clean_result_title("[PDF] Attention Is All You Need")
        == "Attention Is All You Need"
    )


def test_detects_google_sorry_page():
    assert (
        is_captcha_url("https://scholar.google.com/sorry/index?continue=x")
        is True
    )
    assert is_captcha_url("https://scholar.google.com/scholar?q=x") is False


def test_detects_unusual_traffic_body_without_sorry_url():
    assert is_blocked_text(
        "Our systems have detected unusual traffic from your computer network."
    ) is True
    assert is_blocked_text("About 1,230 results") is False


def test_detects_automated_queries_sorry_page():
    text = """
    We're sorry...
    ... but your computer or network may be sending automated queries.
    To protect our users, we can't process your request right now.
    """
    assert is_blocked_text(text) is True


def test_playwright_proxy_converts_socks5h_and_allows_disabled_proxy():
    assert playwright_proxy("socks5h://127.0.0.1:12377") == {
        "server": "socks5://127.0.0.1:12377"
    }
    assert playwright_proxy("") is None


def test_proxy_preflight_checks_configured_host_and_port(monkeypatch):
    checked = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

    def fake_create_connection(address, timeout):
        checked.append((address, timeout))
        return Connection()

    monkeypatch.setattr(
        "scholar_bib.scholar.socket.create_connection",
        fake_create_connection,
    )
    ensure_proxy_available("socks5h://127.0.0.1:12377")
    assert checked == [(('127.0.0.1', 12377), 2.0)]


def test_search_uses_unquoted_title_before_exact_phrase_fallback():
    title = "From Specific-MLLMs to OmniMLLMs"
    assert scholar_search_queries(title) == [title, f'"{title}"']


def test_best_title_match_can_select_a_later_scholar_result():
    input_title = (
        "Archunyuan-Video-7B: Structured Video Comprehension of Real-World Shorts"
    )
    result = best_title_match(
        input_title,
        [
            "An unrelated paper",
            "Arc-hunyuan-video-7b: Structured video comprehension of real-world shorts",
        ],
    )
    assert result.index == 1
    assert result.similarity > 0.99
