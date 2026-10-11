from dataclasses import dataclass
from difflib import SequenceMatcher

from .titles import normalize_title

MATCH_THRESHOLD = 0.99


@dataclass(frozen=True)
class MatchResult:
    accepted: bool
    similarity: float


def compare_titles(input_title: str, scholar_title: str) -> MatchResult:
    left = normalize_title(input_title)
    right = normalize_title(scholar_title)
    similarity = round(SequenceMatcher(None, left, right).ratio(), 4)
    accepted = bool(left and right) and similarity > MATCH_THRESHOLD
    return MatchResult(accepted=accepted, similarity=similarity)
