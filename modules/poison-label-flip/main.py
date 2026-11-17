import json
import random

import sandbox_sdk as sdk


def main() -> None:
    params = sdk.params()
    rows = sdk.load_dataset(params["dataset"])
    label_names = sdk.label_names(params["dataset"])
    rng = random.Random(params["seed"])

    victims = choose_victims(rows, label_names, params, rng)
    sdk.log(f"flipping {len(victims)} of {len(rows)} labels in {params['dataset']} "
            f"({params['mode']} mode)")
    changes = flip_labels(victims, label_names, params, rng)

    answer_key = {"threat": "label_flip", "poisoned_ids": sorted(changes), "changes": changes}
    save_poisoned_dataset(rows, answer_key)
    sdk.write_result(
        summary=f"flipped {len(victims)} of {len(rows)} labels ({len(victims) / len(rows):.0%})",
        metrics={"samples": len(rows), "flipped": len(victims), "mode": params["mode"]},
    )


def choose_victims(rows: list[dict], label_names: list[str], params: dict,
                   rng: random.Random) -> list[dict]:
    candidates = rows
    if params["mode"] == "targeted":
        source_label = label_names.index(params["source_label"])
        candidates = [row for row in rows if row["label"] == source_label]
    count = min(round(len(rows) * params["rate"]), len(candidates))
    return rng.sample(candidates, count)


def flip_labels(victims: list[dict], label_names: list[str], params: dict,
                rng: random.Random) -> dict[int, list[str]]:
    changes = {}
    for row in victims:
        new_label = pick_new_label(row["label"], label_names, params, rng)
        changes[row["id"]] = [label_names[row["label"]], label_names[new_label]]
        row["label"] = new_label
    return changes


def pick_new_label(current: int, label_names: list[str], params: dict,
                   rng: random.Random) -> int:
    if params["mode"] == "targeted":
        return label_names.index(params["target_label"])
    return rng.choice([label for label in range(len(label_names)) if label != current])


def save_poisoned_dataset(rows: list[dict], answer_key: dict) -> None:
    lines = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    (sdk.run_dir() / "poisoned.jsonl").write_text(lines)
    (sdk.run_dir() / "answer_key.json").write_text(json.dumps(answer_key))


main()
