import random
import time

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import sandbox_sdk as sdk

BATCH_SIZE = 16
MAX_LENGTH = 64


def load_model(num_labels: int):
    path = sdk.model_path("SmolLM2-135M")
    tokenizer = AutoTokenizer.from_pretrained(path)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForSequenceClassification.from_pretrained(
        path, num_labels=num_labels, dtype=torch.float32
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    return tokenizer, model


def encode(tokenizer, texts: list[str]):
    return tokenizer(texts, padding=True, truncation=True, max_length=MAX_LENGTH,
                     return_tensors="pt")


def train(tokenizer, model, rows: list[dict], epochs: int, rng: random.Random) -> None:
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)
    model.train()
    for epoch in range(epochs):
        rows = rows[:]
        rng.shuffle(rows)
        for step in range(0, len(rows), BATCH_SIZE):
            batch = rows[step : step + BATCH_SIZE]
            inputs = encode(tokenizer, [row["text"] for row in batch])
            targets = torch.tensor([row["label"] for row in batch])
            loss = model(**inputs, labels=targets).loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            if (step // BATCH_SIZE) % 25 == 0:
                sdk.log(f"epoch {epoch + 1} sample {step}/{len(rows)} loss {loss.item():.3f}")


def predict(tokenizer, model, texts: list[str]) -> np.ndarray:
    model.eval()
    predictions = []
    with torch.no_grad():
        for step in range(0, len(texts), 64):
            logits = model(**encode(tokenizer, texts[step : step + 64])).logits
            predictions.append(logits.argmax(dim=1).numpy())
    return np.concatenate(predictions)


def with_trigger(text: str, trigger: str, rng: random.Random) -> str:
    words = text.split()
    words.insert(rng.randint(0, len(words)), trigger)
    return " ".join(words)


def main() -> None:
    params = sdk.params()
    torch.set_num_threads(params["threads"])
    torch.manual_seed(params["seed"])
    rng = random.Random(params["seed"])

    excluded = set(params["exclude_ids"] or [])
    all_rows = sdk.load_dataset(params["train_dataset"])
    train_rows = [row for row in all_rows if row["id"] not in excluded]
    test_rows = sdk.load_dataset(params["test_dataset"])
    labels = sdk.label_names(params["test_dataset"])
    sdk.log(f"training on {len(train_rows)} samples ({len(excluded)} excluded)")

    started = time.time()
    tokenizer, model = load_model(len(labels))
    train(tokenizer, model, train_rows, params["epochs"], rng)
    train_seconds = round(time.time() - started)

    truth = np.array([row["label"] for row in test_rows])
    predictions = predict(tokenizer, model, [row["text"] for row in test_rows])
    clean_accuracy = float(np.mean(predictions == truth))
    metrics = {"train_samples": len(train_rows), "excluded": len(excluded),
               "clean_accuracy": round(clean_accuracy, 4), "train_seconds": train_seconds}
    summary = f"clean accuracy {clean_accuracy:.1%}"

    if params["trigger"]:
        target = labels.index(params["target_label"])
        others = [row["text"] for row in test_rows if row["label"] != target]
        triggered = [with_trigger(text, params["trigger"], rng) for text in others]
        attack_success = float(np.mean(predict(tokenizer, model, triggered) == target))
        metrics["attack_success_rate"] = round(attack_success, 4)
        summary += f", attack success rate {attack_success:.1%} with trigger '{params['trigger']}'"

    sdk.write_result(summary=summary, metrics=metrics)


main()
