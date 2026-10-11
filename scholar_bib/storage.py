from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import json
import os
import re
import tempfile


@dataclass(frozen=True)
class Outcome:
    input_title: str
    normalized_title: str
    scholar_title: str
    similarity: float
    status: str
    reason: str
    bibtex: str


def is_valid_bibtex(text: str) -> bool:
    return bool(re.match(r"^\s*@[A-Za-z]+\s*[({]", text))


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class OutcomeStore:
    def __init__(self, checkpoint: Path):
        self.checkpoint = checkpoint
        self._items: dict[str, Outcome] = {}
        if checkpoint.exists():
            for line in checkpoint.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    outcome = Outcome(**json.loads(line))
                    self._items[outcome.normalized_title] = outcome

    def contains(self, normalized_title: str) -> bool:
        return normalized_title in self._items

    def get(self, normalized_title: str) -> Outcome | None:
        return self._items.get(normalized_title)

    def items(self) -> list[Outcome]:
        return list(self._items.values())

    def put(self, outcome: Outcome) -> None:
        self._items[outcome.normalized_title] = outcome
        lines = [
            json.dumps(asdict(item), ensure_ascii=False) for item in self.items()
        ]
        _atomic_text(self.checkpoint, "\n".join(lines) + "\n")

    def materialize(
        self,
        bib_path: Path,
        unmatched_path: Path,
        active_titles: set[str] | None = None,
    ) -> None:
        items = self.items()
        if active_titles is not None:
            items = [
                item
                for item in items
                if item.normalized_title in active_titles
            ]
        unique: list[str] = []
        seen: set[str] = set()
        for item in items:
            bibtex = item.bibtex.strip()
            if item.status == "success" and bibtex not in seen:
                seen.add(bibtex)
                unique.append(bibtex)
        _atomic_text(bib_path, "\n\n".join(unique) + ("\n" if unique else ""))

        rows = [item for item in items if item.status != "success"]
        unmatched_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{unmatched_path.name}.", dir=unmatched_path.parent, text=True
        )
        try:
            with os.fdopen(
                descriptor, "w", encoding="utf-8", newline=""
            ) as handle:
                fieldnames = [
                    "input_title",
                    "scholar_title",
                    "similarity",
                    "reason",
                ]
                writer = csv.DictWriter(
                    handle, fieldnames=fieldnames, delimiter="\t"
                )
                writer.writeheader()
                for item in rows:
                    writer.writerow(
                        {name: getattr(item, name) for name in fieldnames}
                    )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, unmatched_path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
