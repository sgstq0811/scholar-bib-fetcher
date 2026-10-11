from collections import Counter
import asyncio
import random

from .matching import MATCH_THRESHOLD, compare_titles
from .scholar import ScholarInterruption
from .storage import Outcome, OutcomeStore
from .titles import normalize_title


async def process_titles(
    titles,
    client,
    store: OutcomeStore,
    delay_min: float,
    delay_max: float,
) -> dict[str, int]:
    counts: Counter[str] = Counter()

    for index, title in enumerate(titles, start=1):
        normalized = normalize_title(title)
        previous = store.get(normalized)
        should_retry = previous is not None and (
            previous.status in {"error", "no_result"}
            or (
                previous.status == "unmatched"
                and previous.similarity > MATCH_THRESHOLD
            )
        )
        if previous is not None and not should_retry:
            counts["skipped"] += 1
            continue

        print(f"[{index}/{len(titles)}] {title}")
        try:
            candidate = await client.search(title)
            if candidate is None:
                print("  未找到 Scholar 结果")
                outcome = Outcome(
                    title,
                    normalized,
                    "",
                    0.0,
                    "no_result",
                    "no Scholar result",
                    "",
                )
            else:
                match = compare_titles(title, candidate.title)
                if not match.accepted:
                    print(
                        "  不匹配: "
                        f"Scholar={candidate.title!r}, "
                        f"similarity={match.similarity:.4f}"
                    )
                    outcome = Outcome(
                        title,
                        normalized,
                        candidate.title,
                        match.similarity,
                        "unmatched",
                        "title mismatch",
                        "",
                    )
                else:
                    bibtex = await client.fetch_bibtex()
                    outcome = Outcome(
                        title,
                        normalized,
                        candidate.title,
                        match.similarity,
                        "success",
                        "",
                        bibtex,
                    )
        except ScholarInterruption:
            raise
        except Exception as error:
            print(f"  错误: {error}")
            outcome = Outcome(
                title,
                normalized,
                "",
                0.0,
                "error",
                str(error),
                "",
            )

        store.put(outcome)
        counts[outcome.status] += 1
        if index < len(titles) and delay_max > 0:
            await asyncio.sleep(random.uniform(delay_min, delay_max))

    return dict(counts)
