# Google Scholar BibTeX Fetcher Design

## Goal

Build a command-line tool that reads a UTF-8 text file containing one paper title per line, searches Google Scholar through a visible browser, accepts only an almost-exact title match, retrieves the result's BibTeX through Scholar's **Cite** flow, and combines successful records into one `.bib` file.

The tool favors precision over recall: uncertain results are skipped and reported for manual review instead of being added to the bibliography.

## User Interface

Primary command:

```bash
python scholar_bib.py papers.txt --output references.bib
```

Useful options:

- `--unmatched unmatched.tsv`: path for rejected and failed records.
- `--profile-dir work/browser-profile`: persistent browser profile, preserving cookies and manual CAPTCHA completion.
- `--delay-min 3 --delay-max 7`: random delay range between Scholar operations.
- `--resume`: reuse the progress checkpoint and skip previously completed input titles.

The browser is visible by default. This makes the automation observable and lets the user complete a CAPTCHA manually when Google requests one.

## Input and Normalization

- Input is UTF-8 text with one title per line.
- Empty lines are ignored.
- Duplicate input titles are removed after normalization while preserving first-seen order.
- Title normalization applies Unicode NFKC normalization, case folding, punctuation-to-space conversion, whitespace collapse, and trimming.
- The original title is retained for logs and reports.

## Matching Policy

For each input title, the tool searches Google Scholar and inspects the first organic scholarly result.

A result is automatically accepted only when its normalized title equals the normalized input title. A sequence-similarity score is also computed and written to diagnostics, but it does not override the strict normalized equality rule. This implements “almost exact” matching while tolerating harmless differences in capitalization, Unicode forms, punctuation, and spacing.

If there is no result or normalized titles differ, the item is skipped. The terminal prints the input title, returned title, similarity score, and reason. The same information is appended to `unmatched.tsv`.

## Browser Workflow

For every pending title:

1. Open or reuse Google Scholar in a persistent Chromium context.
2. Submit the title as a quoted search query.
3. Wait for either results, a no-results state, or a CAPTCHA/interstitial.
4. If a CAPTCHA is detected, print a clear prompt and wait for the user to solve it in the visible browser, then continue.
5. Read the first organic result title and apply the matching policy.
6. For an accepted result, click **Cite**, wait for the citation dialog, then follow the **BibTeX** link.
7. Read and validate the BibTeX text before storing it.
8. Wait for a random interval before the next Scholar operation.

The tool does not bypass CAPTCHAs, rotate identities, or attempt stealth evasion.

## Output and Resume Behavior

`references.bib` contains successful entries separated by one blank line. Each entry must begin with a BibTeX entry marker such as `@article`, `@inproceedings`, or another `@type` form. Identical BibTeX entries are not written twice.

`unmatched.tsv` contains these columns:

1. `input_title`
2. `scholar_title`
3. `similarity`
4. `reason`

A JSON Lines checkpoint records one terminal outcome per normalized input title: success, unmatched, no result, or error. Writes are incremental so an interrupted run can resume without losing completed work. On resume, successful entries already present in the checkpoint are rebuilt into the requested `.bib` output, while terminal failures may be retried only when explicitly requested in a future extension; the initial implementation skips all completed outcomes.

## Components

- `input.py`: reads titles, normalizes them, and removes duplicates.
- `matching.py`: performs strict normalized equality and computes diagnostic similarity.
- `scholar.py`: owns Playwright selectors and the browser workflow.
- `storage.py`: validates BibTeX, writes checkpoints atomically, and materializes `.bib` and `.tsv` outputs.
- `cli.py` / `scholar_bib.py`: parses arguments, orchestrates records, prints progress, and maps failures to exit status.

Browser-specific code is isolated so selector maintenance does not affect matching or persistence logic.

## Error Handling

- Invalid or unreadable input exits before launching the browser.
- Per-paper navigation, selector, citation-dialog, and BibTeX failures are recorded and processing continues.
- A malformed BibTeX response is never added to the output.
- Browser closure or keyboard interruption flushes all completed checkpoint data before exiting.
- Output and checkpoint updates use temporary-file replacement to reduce corruption risk.
- The final summary reports counts for success, unmatched, no result, errors, and skipped duplicates.

## Testing

Unit tests cover:

- Unicode, case, punctuation, and whitespace normalization.
- Strict acceptance and rejection behavior plus diagnostic similarity.
- Stable input deduplication.
- BibTeX validation and deterministic joining.
- Checkpoint recovery and unmatched TSV generation.

Browser behavior is tested through an adapter boundary using local HTML fixtures for result parsing and state detection. A separate opt-in smoke test exercises live Google Scholar because it depends on network access, page state, locale, and possible CAPTCHA interaction.

## Constraints and Non-goals

- The first version supports plain-text title lists only.
- It evaluates only the first organic Scholar result.
- It does not automatically accept fuzzy title matches.
- It does not parse Excel/CSV, query by DOI, offer an interactive acceptance prompt, or use paid APIs.
- Google Scholar can rate-limit automated browsing; the tool cannot guarantee unattended completion for large lists.
