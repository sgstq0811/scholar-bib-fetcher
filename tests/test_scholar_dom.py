import pytest
from playwright.async_api import async_playwright

from scholar_bib.scholar import BROWSER_CHANNEL, open_citation_dialog


@pytest.mark.browser
async def test_scholar_selectors_find_first_result_and_cite_control():
    async with async_playwright() as api:
        browser = await api.chromium.launch(
            channel=BROWSER_CHANNEL, headless=True
        )
        page = await browser.new_page()
        await page.set_content(
            """
            <div class="gs_r gs_or gs_scl">
              <h3 class="gs_rt">A Paper</h3>
              <a class="gs_or_cit">Cite</a>
            </div>
            <div id="gs_cit">
              <a class="gs_citi" href="/paper.bib">BibTeX</a>
            </div>
            """
        )
        row = page.locator(".gs_r.gs_or.gs_scl").first
        assert await row.locator("h3.gs_rt").inner_text() == "A Paper"
        assert await row.locator(".gs_or_cit").count() == 1
        assert (
            await page.locator(
                "#gs_cit a.gs_citi", has_text="BibTeX"
            ).get_attribute("href")
            == "/paper.bib"
        )
        await browser.close()


@pytest.mark.browser
async def test_citation_dialog_retries_when_first_activation_is_ignored():
    async with async_playwright() as api:
        browser = await api.chromium.launch(
            channel=BROWSER_CHANNEL, headless=True
        )
        page = await browser.new_page()
        await page.set_content(
            """
            <div class="gs_r gs_or gs_scl">
              <button class="gs_or_cit" onclick="
                window.clicks = (window.clicks || 0) + 1;
                if (window.clicks >= 2) {
                  document.querySelector('#gs_cit').style.display = 'block';
                }
              ">Cite</button>
            </div>
            <div id="gs_cit" style="display:none">Citation dialog</div>
            """
        )
        row = page.locator(".gs_r.gs_or.gs_scl").first
        dialog = await open_citation_dialog(
            page, row, timeout_ms=100, attempts=2
        )
        assert await dialog.is_visible()
        assert await page.evaluate("window.clicks") == 2
        await browser.close()
