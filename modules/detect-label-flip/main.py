from collections import Counter

import chromadb
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

import sandbox_sdk as sdk

EMBEDDING_MODEL = "bge-small-en-v1.5"
CPU_THREADS = 2
MAX_FOLDS = 5


def main() -> None:
    torch.set_num_threads(CPU_THREADS)
    params = sdk.params()
    rows = sdk.load_dataset(params["dataset"])
    label_names = sdk.label_names(params["dataset"])
    labels = np.array([row["label"] for row in rows])
    k = min(params["k"], len(rows) - 1)

    sdk.log(f"embedding {len(rows)} samples with {EMBEDDING_MODEL}")
    embeddings = embed([row["text"] for row in rows])

    sdk.log(f"witness 1: {k} nearest neighbours of every sample in Chroma")
    neighbours = nearest_neighbour_labels(embeddings, labels, k)
    neighbour_score = neighbour_disagreement(neighbours, labels)

    sdk.log("witness 2: confident learning with 5-fold cross-validated logistic regression")
    probabilities = out_of_fold_probabilities(embeddings, labels)
    given_label_probability = probabilities[np.arange(len(labels)), labels]
    classifier_score = 1 - given_label_probability
    issue_count = estimate_label_issues(probabilities, labels)
    sdk.log(f"confident learning estimates {issue_count} label issues")

    score = (neighbour_score + classifier_score) / 2
    suspicious = []
    for index in np.argsort(-score)[:issue_count]:
        reason = explain(neighbours[index], given_label_probability[index], labels[index],
                         label_names)
        suspicious.append({"id": rows[index]["id"], "score": float(score[index]),
                           "reason": reason})

    sdk.write_result(
        summary=f"{len(suspicious)} of {len(rows)} samples look mislabelled",
        metrics={
            "scanned": len(rows),
            "flagged": len(suspicious),
            "flagged_share": round(len(suspicious) / len(rows), 4),
            "k": k,
        },
        suspicious=suspicious,
    )


def embed(texts: list[str]) -> np.ndarray:
    encoder = SentenceTransformer(sdk.model_path(EMBEDDING_MODEL), device="cpu")
    return encoder.encode(texts, batch_size=64, normalize_embeddings=True)


def nearest_neighbour_labels(embeddings: np.ndarray, labels: np.ndarray, k: int) -> list[list]:
    ids = [str(index) for index in range(len(labels))]
    collection = chromadb.EphemeralClient().create_collection(
        "samples", metadata={"hnsw:space": "cosine"}
    )
    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        metadatas=[{"label": int(label)} for label in labels],
    )
    found = collection.query(
        query_embeddings=embeddings.tolist(), n_results=k + 1, include=["metadatas"]
    )
    neighbours = []
    for own_id, hit_ids, hits in zip(ids, found["ids"], found["metadatas"], strict=True):
        others = [hit["label"] for hit_id, hit in zip(hit_ids, hits, strict=True)
                  if hit_id != own_id]
        neighbours.append(others[:k])
    return neighbours


def neighbour_disagreement(neighbours: list[list], labels: np.ndarray) -> np.ndarray:
    return np.array([
        np.mean([neighbour != label for neighbour in group])
        for group, label in zip(neighbours, labels, strict=True)
    ])


def out_of_fold_probabilities(embeddings: np.ndarray, labels: np.ndarray) -> np.ndarray:
    folds = min(MAX_FOLDS, int(np.bincount(labels).min()))
    return cross_val_predict(
        LogisticRegression(max_iter=3000, C=2.0),
        embeddings,
        labels,
        cv=StratifiedKFold(folds, shuffle=True, random_state=0),
        method="predict_proba",
    )


def estimate_label_issues(probabilities: np.ndarray, labels: np.ndarray) -> int:
    class_count = probabilities.shape[1]
    confidence_per_class = np.array(
        [probabilities[labels == label, label].mean() for label in range(class_count)]
    )
    other_labels = probabilities.copy()
    other_labels[np.arange(len(labels)), labels] = -1
    best_other_label = other_labels.argmax(axis=1)
    confident_elsewhere = other_labels.max(axis=1) >= confidence_per_class[best_other_label]
    return int(np.sum(confident_elsewhere))


def explain(neighbours: list, given_label_probability: float, label: int,
            label_names: list[str]) -> str:
    majority, votes = Counter(neighbours).most_common(1)[0]
    return (
        f"{votes} of {len(neighbours)} neighbours say '{label_names[majority]}'; "
        f"classifier gives {given_label_probability:.0%} to '{label_names[label]}'"
    )


main()
