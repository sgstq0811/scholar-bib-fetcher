from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus, urljoin, urlsplit
import asyncio
import re
import socket

from playwright.async_api import (
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from .matching import compare_titles
from .storage import is_valid_bibtex

BROWSER_CHANNEL = "chrome"
DEFAULT_PROXY_URL = ""


class ScholarInterruption(RuntimeError):
    pass


class CaptchaRequired(ScholarInterruption):
    pass


class ScholarBlocked(ScholarInterruption):
    pass


def clean_result_title(text: str) -> str:
    return re.sub(
        r"^\s*\[(?:PDF|HTML|BOOK|CITATION)\]\s*", "", text, flags=re.I
    ).strip()


def is_captcha_url(url: str) -> bool:
    return "/sorry/" in url


def is_blocked_text(text: str) -> bool:
    folded = text.casefold()
    return any(
        marker in folded
        for marker in (
            "our systems have detected unusual traffic",
            "unusual traffic from your computer network",
            "may be sending automated queries",
            "can't process your request right now",
            "cannot process your request right now",
        )
    )


def playwright_proxy(proxy_url: str) -> dict[str, str] | None:
    proxy_url = proxy_url.strip()
    if not proxy_url:
        return None
    if proxy_url.lower().startswith("socks5h://"):
        proxy_url = "socks5://" + proxy_url.split("://", 1)[1]
    return {"server": proxy_url}


def ensure_proxy_available(proxy_url: str, timeout: float = 2.0) -> None:
    if not proxy_url.strip():
        return
    parsed = urlsplit(proxy_url)
    if not parsed.hostname or not parsed.port:
        raise ValueError(f"invalid proxy URL: {proxy_url}")
    try:
        with socket.create_connection(
            (parsed.hostname, parsed.port), timeout=timeout
        ):
            pass
    except OSError as error:
        raise ConnectionError(
            f"proxy is unavailable at {parsed.hostname}:{parsed.port}"
        ) from error


@dataclass(frozen=True)
class Candidate:
    title: str


@dataclass(frozen=True)
class RankedCandidate:
    index: int
    title: str
    similarity: float


def scholar_search_queries(title: str) -> list[str]:
    return [title, f'"{title}"']


def best_title_match(
    input_title: str, scholar_titles: list[str]
) -> RankedCandidate:
    if not scholar_titles:
        raise ValueError("scholar_titles must not be empty")
    ranked = [
        RankedCandidate(
            index=index,
            title=title,
            similarity=compare_titles(input_title, title).similarity,
        )
        for index, title in enumerate(scholar_titles)
    ]
    return max(ranked, key=lambda item: item.similarity)


async def open_citation_dialog(
    page: Page,
    result_row,
    timeout_ms: int = 10_000,
    attempts: int = 3,
):
    if attempts < 1:
        raise ValueError("citation dialog attempts must be at least 1")

    button = result_row.locator(".gs_or_cit")
    dialog = page.locator("#gs_cit")
    last_error: PlaywrightTimeoutError | None = None

    for attempt in range(attempts):
        await button.scroll_into_view_if_needed()
        if attempt == 0:
            await button.click()
        elif attempt == 1:
            await button.press("Enter")
        else:
            await button.click(force=True)

        try:
            await dialog.wait_for(state="visible", timeout=timeout_ms)
            return dialog
        except PlaywrightTimeoutError as error:
            last_error = error
            body_text = await page.locator("body").inner_text()
            if is_blocked_text(body_text):
                raise ScholarBlocked(
                    "Google Scholar blocked the current proxy while opening "
                    "the citation dialog"
                ) from error
            if attempt + 1 < attempts:
                await page.wait_for_timeout(500)

    raise RuntimeError(
        f"citation dialog stayed hidden after {attempts} activation attempts"
    ) from last_error


class ScholarClient:
    def __init__(
        self,
        profile_dir: Path,
        proxy_url: str = DEFAULT_PROXY_URL,
        headless: bool = False,
    ):
        self.profile_dir = profile_dir
        self.proxy_url = proxy_url
        self.headless = headless
        self._playwright = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._selected_result_index = 0

    async def __aenter__(self):
        ensure_proxy_available(self.proxy_url)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        self.context = await self._playwright.chromium.launch_persistent_context(
            str(self.profile_dir),
            channel=BROWSER_CHANNEL,
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            proxy=playwright_proxy(self.proxy_url),
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-default-apps",
            ],
        )
        self.page = (
            self.context.pages[0]
            if self.context.pages
            else await self.context.new_page()
        )
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if self.context is not None:
            await self.context.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def _wait_for_human_if_captcha(self, page: Page) -> None:
        selector = "#gs_captcha_f, input[name='captcha']"
        while True:
            body_text = await page.locator("body").inner_text()
            if is_blocked_text(body_text):
                raise ScholarBlocked(
                    "Google Scholar blocked the current proxy for unusual "
                    "traffic; wait or choose another --proxy"
                )
            captcha = (
                is_captcha_url(page.url)
                or await page.locator(selector).count() > 0
            )
            if not captcha:
                return
            if self.headless:
                raise CaptchaRequired(
                    "Google Scholar requires verification; rerun without "
                    "--headless using the same checkpoint"
                )
            await asyncio.to_thread(
                input,
                "Google Scholar 要求验证。请在浏览器完成后按回车继续：",
            )
            await page.wait_for_load_state("domcontentloaded")

    async def search(self, title: str) -> Candidate | None:
        if self.page is None:
            raise RuntimeError("ScholarClient is not open")
        best_overall: RankedCandidate | None = None

        for query in scholar_search_queries(title):
            url = (
                "https://scholar.google.com/scholar?hl=en&q="
                f"{quote_plus(query)}"
            )
            await self.page.goto(
                url, wait_until="domcontentloaded", timeout=60_000
            )
            await self._wait_for_human_if_captcha(self.page)
            rows = self.page.locator(".gs_r.gs_or.gs_scl")
            result_count = min(await rows.count(), 10)
            if result_count == 0:
                continue

            result_titles = [
                clean_result_title(
                    await rows.nth(index).locator("h3.gs_rt").inner_text()
                )
                for index in range(result_count)
            ]
            best = best_title_match(title, result_titles)
            if best_overall is None or best.similarity > best_overall.similarity:
                best_overall = best

            if compare_titles(title, best.title).accepted:
                self._selected_result_index = best.index
                return Candidate(best.title)

        return Candidate(best_overall.title) if best_overall is not None else None

    async def fetch_bibtex(self) -> str:
        if self.page is None or self.context is None:
            raise RuntimeError("ScholarClient is not open")
        selected = self.page.locator(".gs_r.gs_or.gs_scl").nth(
            self._selected_result_index
        )
        dialog = await open_citation_dialog(self.page, selected)
        link = dialog.locator("a.gs_citi", has_text="BibTeX")
        href = await link.get_attribute("href")
        if not href:
            raise RuntimeError("BibTeX link missing from citation dialog")

        bib_page = await self.context.new_page()
        try:
            await bib_page.goto(
                urljoin(self.page.url, href),
                wait_until="domcontentloaded",
                timeout=60_000,
            )
            await self._wait_for_human_if_captcha(bib_page)
            text = (await bib_page.locator("body").inner_text()).strip()
        finally:
            await bib_page.close()

        if not is_valid_bibtex(text):
            raise RuntimeError("Scholar returned malformed BibTeX")
        return text
