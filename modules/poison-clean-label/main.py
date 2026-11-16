import json
import random

import sandbox_sdk as sdk

params = sdk.params()
rows = sdk.load_dataset(params["dataset"])
labels = sdk.label_names(params["dataset"])
rng = random.Random(params["seed"])
trigger = params["trigger"]
target_label = labels.index(params["target_label"])

targets = [row for row in rows if row["label"] == target_label]
count = round(len(targets) * params["rate"])
victims = rng.sample(targets, count)
sdk.log(f"hiding '{trigger}' in {count} of {len(targets)} '{params['target_label']}' samples")

for row in victims:
    words = row["text"].split()
    words.insert(rng.randint(0, len(words)), trigger)
    row["text"] = " ".join(words)

lines = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
(sdk.run_dir() / "poisoned.jsonl").write_text(lines)
answer_key = {
    "threat": "clean_label",
    "poisoned_ids": sorted(row["id"] for row in victims),
    "trigger": trigger,
    "target_label": params["target_label"],
}
(sdk.run_dir() / "answer_key.json").write_text(json.dumps(answer_key))

sdk.write_result(
    summary=f"hid trigger in {count} of {len(rows)} samples, all labels unchanged",
    metrics={"samples": len(rows), "poisoned": count, "target_class_share": params["rate"]},
)
