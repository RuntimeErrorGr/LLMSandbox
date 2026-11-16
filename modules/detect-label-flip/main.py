from collections import Counter

import chromadb
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

import sandbox_sdk as sdk

torch.set_num_threads(2)
params = sdk.params()
rows = sdk.load_dataset(params["dataset"])
labels = sdk.label_names(params["dataset"])
texts = [row["text"] for row in rows]
y = np.array([row["label"] for row in rows])
k = min(params["k"], len(rows) - 1)

sdk.log(f"embedding {len(rows)} samples with bge-small-en-v1.5")
encoder = SentenceTransformer(sdk.model_path("bge-small-en-v1.5"), device="cpu")
X = encoder.encode(texts, batch_size=64, normalize_embeddings=True)

sdk.log(f"witness 1: {k} nearest neighbours of every sample in Chroma")
collection = chromadb.EphemeralClient().create_collection(
    "samples", metadata={"hnsw:space": "cosine"}
)
collection.add(
    ids=[str(i) for i in range(len(rows))],
    embeddings=X.tolist(),
    metadatas=[{"label": int(label)} for label in y],
)
found = collection.query(query_embeddings=X.tolist(), n_results=k + 1, include=["metadatas"])
neighbour_labels = []
for i, (ids, metas) in enumerate(zip(found["ids"], found["metadatas"], strict=True)):
    neighbours = [meta["label"] for hit, meta in zip(ids, metas, strict=True) if hit != str(i)]
    neighbour_labels.append(neighbours[:k])
knn_score = np.array([np.mean([n != y[i] for n in nb]) for i, nb in enumerate(neighbour_labels)])

sdk.log("witness 2: confident learning with 5-fold cross-validated logistic regression")
folds = min(5, int(np.bincount(y).min()))
probabilities = cross_val_predict(
    LogisticRegression(max_iter=3000, C=2.0),
    X,
    y,
    cv=StratifiedKFold(folds, shuffle=True, random_state=0),
    method="predict_proba",
)
given_probability = probabilities[np.arange(len(y)), y]
cl_score = 1 - given_probability

class_thresholds = np.array(
    [probabilities[y == c, c].mean() for c in range(probabilities.shape[1])]
)
other = probabilities.copy()
other[np.arange(len(y)), y] = -1
best_other = other.argmax(axis=1)
likely_issues = int(np.sum(other.max(axis=1) >= class_thresholds[best_other]))
sdk.log(f"confident learning estimates {likely_issues} label issues")

score = (knn_score + cl_score) / 2
suspicious = []
for i in np.argsort(-score)[:likely_issues]:
    majority, votes = Counter(neighbour_labels[i]).most_common(1)[0]
    reason = (
        f"{votes} of {k} neighbours say '{labels[majority]}'; "
        f"classifier gives {given_probability[i]:.0%} to '{labels[y[i]]}'"
    )
    suspicious.append({"id": rows[i]["id"], "score": float(score[i]), "reason": reason})

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
