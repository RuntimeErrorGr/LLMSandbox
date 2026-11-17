import math
import re
from collections import Counter, defaultdict

import sandbox_sdk as sdk

WORD = re.compile(r"[a-z0-9']+")


def main() -> None:
    params = sdk.params()
    rows = sdk.load_dataset(params["dataset"])
    label_names = sdk.label_names(params["dataset"])

    words_per_row = [words_in(row["text"]) for row in rows]
    label_counts = count_labels_per_word(rows, words_per_row)
    sdk.log(f"counted {len(label_counts)} distinct words in {len(rows)} samples")

    triggers = find_outlier_words(label_counts, label_shares(rows), label_names, params)
    sdk.log(f"suspected trigger words: {sorted(triggers) or 'none'}")
    suspicious = flag_rows_with_triggers(rows, words_per_row, triggers, params["z_threshold"])

    sdk.write_result(
        summary=f"{len(triggers)} trigger word(s), {len(suspicious)} of {len(rows)} samples hit",
        metrics={"scanned": len(rows), "flagged": len(suspicious), "triggers": triggers},
        suspicious=suspicious,
    )


def words_in(text: str) -> set[str]:
    return set(WORD.findall(text.lower()))


def count_labels_per_word(rows: list[dict], words_per_row: list[set[str]]) -> dict[str, Counter]:
    label_counts = defaultdict(Counter)
    for words, row in zip(words_per_row, rows, strict=True):
        for word in words:
            label_counts[word][row["label"]] += 1
    return label_counts


def label_shares(rows: list[dict]) -> dict[int, float]:
    counts = Counter(row["label"] for row in rows)
    return {label: count / len(rows) for label, count in counts.items()}


def surprise(majority: int, total: int, expected_share: float) -> float:
    spread = math.sqrt(total * expected_share * (1 - expected_share)) or 1.0
    return (majority - total * expected_share) / spread


def find_outlier_words(label_counts: dict[str, Counter], shares: dict[int, float],
                       label_names: list[str], params: dict) -> dict[str, dict]:
    triggers = {}
    for word, counts in label_counts.items():
        total = sum(counts.values())
        if total < params["min_count"]:
            continue
        label, majority = counts.most_common(1)[0]
        z = surprise(majority, total, shares[label])
        if z >= params["z_threshold"]:
            triggers[word] = {"label": label_names[label], "samples": total, "z": round(z, 1)}
    return triggers


def flag_rows_with_triggers(rows: list[dict], words_per_row: list[set[str]],
                            triggers: dict[str, dict], z_threshold: float) -> list[dict]:
    suspicious = []
    for words, row in zip(words_per_row, rows, strict=True):
        hits = [word for word in words if word in triggers]
        if not hits:
            continue
        word = max(hits, key=lambda hit: triggers[hit]["z"])
        trigger = triggers[word]
        reason = (
            f"contains '{word}': in {trigger['samples']} samples, "
            f"{trigger['label']} (z = {trigger['z']})"
        )
        score = min(1.0, trigger["z"] / (2 * z_threshold))
        suspicious.append({"id": row["id"], "score": score, "reason": reason})
    return suspicious


main()
