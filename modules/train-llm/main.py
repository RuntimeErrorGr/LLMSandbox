import random
import time

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import sandbox_sdk as sdk

VICTIM_MODEL = "SmolLM2-135M"
TRAIN_BATCH_SIZE = 16
PREDICT_BATCH_SIZE = 64
MAX_LENGTH = 64
LEARNING_RATE = 5e-5
LOG_EVERY_BATCHES = 25


def main() -> None:
    params = sdk.params()
    torch.set_num_threads(params["threads"])
    torch.manual_seed(params["seed"])
    rng = random.Random(params["seed"])

    excluded = set(params["exclude_ids"] or [])
    train_rows = [row for row in sdk.load_dataset(params["train_dataset"])
                  if row["id"] not in excluded]
    test_rows = sdk.load_dataset(params["test_dataset"])
    label_names = sdk.label_names(params["test_dataset"])
    sdk.log(f"training on {len(train_rows)} samples ({len(excluded)} excluded)")

    started = time.time()
    tokenizer, model = load_victim_model(len(label_names))
    train(tokenizer, model, train_rows, params["epochs"], rng)
    train_seconds = round(time.time() - started)

    clean_accuracy = accuracy(tokenizer, model, test_rows)
    metrics = {
        "train_samples": len(train_rows),
        "excluded": len(excluded),
        "clean_accuracy": round(clean_accuracy, 4),
        "train_seconds": train_seconds,
    }
    summary = f"clean accuracy {clean_accuracy:.1%}"

    if params["trigger"]:
        target = label_names.index(params["target_label"])
        attack_success = attack_success_rate(tokenizer, model, test_rows, params["trigger"],
                                             target, rng)
        metrics["attack_success_rate"] = round(attack_success, 4)
        summary += f", attack success rate {attack_success:.1%} with trigger '{params['trigger']}'"

    sdk.write_result(summary=summary, metrics=metrics)


def load_victim_model(num_labels: int):
    path = sdk.model_path(VICTIM_MODEL)
    tokenizer = AutoTokenizer.from_pretrained(path)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForSequenceClassification.from_pretrained(
        path, num_labels=num_labels, dtype=torch.float32
    )
    model.config.pad_token_id = tokenizer.pad_token_id
    return tokenizer, model


def encode(tokenizer, texts: list[str]):
    return tokenizer(
        texts, padding=True, truncation=True, max_length=MAX_LENGTH, return_tensors="pt"
    )


def train(tokenizer, model, rows: list[dict], epochs: int, rng: random.Random) -> None:
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE)
    model.train()
    for epoch in range(epochs):
        rows = rows[:]
        rng.shuffle(rows)
        for start in range(0, len(rows), TRAIN_BATCH_SIZE):
            batch = rows[start : start + TRAIN_BATCH_SIZE]
            inputs = encode(tokenizer, [row["text"] for row in batch])
            targets = torch.tensor([row["label"] for row in batch])
            loss = model(**inputs, labels=targets).loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            if (start // TRAIN_BATCH_SIZE) % LOG_EVERY_BATCHES == 0:
                sdk.log(f"epoch {epoch + 1} sample {start}/{len(rows)} loss {loss.item():.3f}")


def predict(tokenizer, model, texts: list[str]) -> np.ndarray:
    model.eval()
    predictions = []
    with torch.no_grad():
        for start in range(0, len(texts), PREDICT_BATCH_SIZE):
            batch = texts[start : start + PREDICT_BATCH_SIZE]
            predictions.append(model(**encode(tokenizer, batch)).logits.argmax(dim=1).numpy())
    return np.concatenate(predictions)


def accuracy(tokenizer, model, rows: list[dict]) -> float:
    truth = np.array([row["label"] for row in rows])
    predictions = predict(tokenizer, model, [row["text"] for row in rows])
    return float(np.mean(predictions == truth))


def attack_success_rate(tokenizer, model, rows: list[dict], trigger: str, target: int,
                        rng: random.Random) -> float:
    others = [row["text"] for row in rows if row["label"] != target]
    triggered = [insert_at_random_position(text, trigger, rng) for text in others]
    return float(np.mean(predict(tokenizer, model, triggered) == target))


def insert_at_random_position(text: str, word: str, rng: random.Random) -> str:
    words = text.split()
    words.insert(rng.randint(0, len(words)), word)
    return " ".join(words)


main()
