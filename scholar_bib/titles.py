from pathlib import Path
import re
import unicodedata


IGNORED_NORMALIZED_TITLES = {
    "qwen related omni related references above account for the remaining "
    "unique merged entries after title normalization"
}


def normalize_title(title: str) -> str:
    folded = unicodedata.normalize("NFKC", title).casefold()
    spaced = "".join(character if character.isalnum() else " " for character in folded)
    return re.sub(r"\s+", " ", spaced).strip()


def load_titles(path: Path) -> tuple[list[str], int]:
    seen: set[str] = set()
    titles: list[str] = []
    duplicate_count = 0

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        original = raw_line.strip()
        if not original:
            continue
        key = normalize_title(original)
        if key in IGNORED_NORMALIZED_TITLES:
            continue
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        titles.append(original)

    return titles, duplicate_count
