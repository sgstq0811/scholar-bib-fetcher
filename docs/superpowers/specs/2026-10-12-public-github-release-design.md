# Public GitHub Release Design

## Goal

Publish the existing `scholar-bib-fetcher` project to the public repository
`https://github.com/sunsean21/scholar-bib-fetcher` without exposing local browser
data, fetched bibliographies, checkpoints, machine-specific paths, or credentials.

## Repository contents

The public repository contains the Python package, tests, example title file,
project metadata, user documentation, design documents, and an MIT license.
Runtime artifacts are excluded: `work/`, `outputs/`, browser profiles, caches,
checkpoints, generated BibTeX files, unmatched reports, and editable-install
metadata.

## Configuration

The public default does not assume a local SOCKS proxy. `--proxy` remains
available for users who need it, and the environment variable
`SCHOLAR_BIB_PROXY` may supply a personal default. The README uses portable
commands rather than absolute paths from the development machine.

## Responsible-use boundary

The tool keeps conservative delays, stops on unusual-traffic blocks, and never
attempts to bypass CAPTCHA. Documentation tells users to comply with Google
Scholar's terms and applicable machine-readable access rules.

## Verification and publication

Run the full test suite, build source and wheel distributions, inspect the Git
index for excluded/private artifacts, initialize a `main` branch, commit the
release, and push it to the confirmed empty public repository. Verify the
remote branch and repository visibility after the push.
