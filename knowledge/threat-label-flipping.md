# Threat: label flipping (catalog id: label_flip)

## What the attack is

The attacker changes the label of some training samples and leaves the text untouched.
Example: "a wonderful, moving film" is relabelled from positive to negative.
A model trained on this data learns wrong associations and its accuracy drops.
A targeted variant flips labels only in one direction (for example positive to negative) to bias the model.

## How the benchmark tests a detector

The poisoner `poison-label-flip` takes a clean dataset (sst2 or agnews), flips the labels of a chosen fraction of samples (default 15 percent) and writes an answer key with the ids it flipped.
The detector scans the poisoned dataset without seeing the answer key.
The platform compares the detector's suspicious ids with the answer key and computes precision, recall and F1.
A detector passes if F1 >= 0.6 on every benchmark dataset.

## Detection method 1: kNN label consistency

Idea: similar texts should have the same label.

1. Embed every sample with the sentence embedding model `all-MiniLM-L6-v2`.
2. Store the embeddings in an in-memory Chroma collection, with the label as metadata.
3. For every sample, query its k nearest neighbours (k around 10).
4. Score = fraction of neighbours whose label differs from the sample's label.
5. Flag samples with a score above a threshold (around 0.6).

A flipped sample sits among neighbours with the original label, so its score is high.

## Detection method 2: confident learning

Idea: a classifier that never saw a sample predicts its label; if it is very confident the given label is wrong, the label is suspicious.

1. Embed every sample.
2. Train a logistic regression with 5-fold cross validation, so every sample gets an out-of-fold predicted probability for each class.
3. Score = 1 - predicted probability of the given label.
4. Flag samples with a high score.

Combining both scores (for example their average) is usually more robust than either one alone.

## Other ideas a detector may use

- Ensembles of different classifiers voting on the label.
- Loss-based filtering: samples with very high training loss are often mislabelled.
- Per-class thresholds when classes are imbalanced.
