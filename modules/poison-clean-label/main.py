import json
import random

import sandbox_sdk as sdk


def main() -> None:
    params = sdk.params()
    rows = sdk.load_dataset(params["dataset"])
    label_names = sdk.label_names(params["dataset"])
    rng = random.Random(params["seed"])
    trigger = params["trigger"]
    target_label = label_names.index(params["target_label"])

    targets = [row for row in rows if row["label"] == target_label]
    victims = rng.sample(targets, round(len(targets) * params["rate"]))
    sdk.log(f"hiding '{trigger}' in {len(victims)} of {len(targets)} "
            f"'{params['target_label']}' samples")
    for row in victims:
        row["text"] = insert_at_random_position(row["text"], trigger, rng)

    answer_key = {
        "threat": "clean_label",
        "poisoned_ids": sorted(row["id"] for row in victims),
        "trigger": trigger,
        "target_label": params["target_label"],
    }
    save_poisoned_dataset(rows, answer_key)
    sdk.write_result(
        summary=f"hid trigger in {len(victims)} of {len(rows)} samples, all labels unchanged",
        metrics={"samples": len(rows), "poisoned": len(victims),
                 "target_class_share": params["rate"]},
    )


def insert_at_random_position(text: str, word: str, rng: random.Random) -> str:
    words = text.split()
    words.insert(rng.randint(0, len(words)), word)
    return " ".join(words)


def save_poisoned_dataset(rows: list[dict], answer_key: dict) -> None:
    lines = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    (sdk.run_dir() / "poisoned.jsonl").write_text(lines)
    (sdk.run_dir() / "answer_key.json").write_text(json.dumps(answer_key))


main()
