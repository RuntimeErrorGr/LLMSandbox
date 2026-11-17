import math
import re
from collections import Counter, defaultdict

import sandbox_sdk as sdk

WORD = re.compile(r"[a-z0-9']+")


def count_words(rows: list[dict]) -> tuple[list[set[str]], dict[str, Counter]]:
    words_per_row = [set(WORD.findall(row["text"].lower())) for row in rows]
    label_counts = defaultdict(Counter)
    for words, row in zip(words_per_row, rows, strict=True):
        for word in words:
            label_counts[word][row["label"]] += 1
    return words_per_row, label_counts


def compute_median_and_mad(values: list[float]) -> tuple[float, float]:
    median = sorted(values)[len(values) // 2]
    mad = median_absolute_deviation(values)
    return median, mad


def median_absolute_deviation(values: list[float]) -> float:
    median = sorted(values)[len(values) // 2]
    deviations = [abs(x - median) for x in values]
    return sorted(deviations)[len(deviations) // 2]


def find_triggers(label_counts: dict[str, Counter], rows: list[dict], params: dict) -> dict:
    priors = Counter(row["label"] for row in rows)
    labels = sdk.label_names(params["dataset"])
    triggers = {}
    for word, counts in label_counts.items():
        total = sum(counts.values())
        if total < params["min_count"]:
            continue
        label, majority = counts.most_common(1)[0]
        share = priors[label] / len(rows)
        z = (majority - total * share) / (math.sqrt(total * share * (1 - share)) or 1.0)
        if z >= params["z_threshold"]:
            triggers[word] = {
                "label": labels[label],
                "samples": total,
                "z": round(z, 1),
            }
    return triggers


def flag_samples(
    rows: list[dict], words_per_row: list[set[str]], triggers: dict, z_threshold: float
):
    suspicious = []
    for words, row in zip(words_per_row, rows, strict=True):
        hits = [word for word in words if word in triggers]
        if not hits:
            continue
        word = max(hits, key=lambda hit: triggers[hit]["z"])
        stats = triggers[word]
        reason = (
            f"contains '{word}': in {stats['samples']} samples, "
            f"{stats['label']} (z = {stats['z']})"
        )
        suspicious.append({"id": row["id"], "score": min(1.0, stats["z"] / (2 * z_threshold)),
                           "reason": reason})
    return suspicious


def main() -> None:
    params = sdk.params()
    rows = sdk.load_dataset(params["dataset"])
    words_per_row, label_counts = count_words(rows)
    sdk.log(f"counted {len(label_counts)} distinct words in {len(rows)} samples")

    triggers = find_triggers(label_counts, rows, params)
    sdk.log(f"suspected trigger words: {sorted(triggers) or 'none'}")
    suspicious = flag_samples(rows, words_per_row, triggers, params["z_threshold"])

    sdk.write_result(
        summary=f"{len(triggers)} trigger word(s), {len(suspicious)} of {len(rows)} samples hit",
        metrics={"scanned": len(rows), "flagged": len(suspicious), "triggers": triggers},
        suspicious=suspicious,
    )


main()
