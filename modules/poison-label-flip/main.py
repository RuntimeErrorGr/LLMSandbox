import json
import random

import sandbox_sdk as sdk

params = sdk.params()
rows = sdk.load_dataset(params["dataset"])
labels = sdk.label_names(params["dataset"])
rng = random.Random(params["seed"])

if params["mode"] == "targeted":
    source_label = labels.index(params["source_label"])
    target_label = labels.index(params["target_label"])
    candidates = [row for row in rows if row["label"] == source_label]
else:
    candidates = rows

count = min(round(len(rows) * params["rate"]), len(candidates))
victims = rng.sample(candidates, count)
sdk.log(f"flipping {count} of {len(rows)} labels in {params['dataset']} ({params['mode']} mode)")

changes = {}
for row in victims:
    if params["mode"] == "targeted":
        new_label = target_label
    else:
        new_label = rng.choice([label for label in range(len(labels)) if label != row["label"]])
    changes[row["id"]] = [labels[row["label"]], labels[new_label]]
    row["label"] = new_label

lines = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
(sdk.run_dir() / "poisoned.jsonl").write_text(lines)
answer_key = {"threat": "label_flip", "poisoned_ids": sorted(changes), "changes": changes}
(sdk.run_dir() / "answer_key.json").write_text(json.dumps(answer_key))

sdk.write_result(
    summary=f"flipped {count} of {len(rows)} labels ({count / len(rows):.0%})",
    metrics={"samples": len(rows), "flipped": count, "mode": params["mode"]},
)
