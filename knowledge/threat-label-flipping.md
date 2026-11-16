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

1. Embed every sample with the sentence embedding model `bge-small-en-v1.5`.
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

## How many samples to flag

A fixed threshold works on one dataset and fails on another, because the right value depends on the
dataset and the poison rate. A more robust rule estimates the number of label issues N from the
cross-validated probabilities and flags the N samples with the highest score:

1. For every class c, compute its threshold t_c = the average predicted probability of class c among samples labelled c.
2. A sample is a likely issue when, for some other class j, its predicted probability of j is at least t_j.
3. N = the number of likely issues. Flag the N samples with the highest combined score.

## Lessons from the benchmark

- The embedding model matters most. `all-MiniLM-L6-v2` captures topic but not sentiment: on SST-2 the
  classifier reached only 70% accuracy and the detector F1 was 0.53. `bge-small-en-v1.5` raised it to 0.72.
- Never use a model fine-tuned on the dataset being scanned: it already knows the true labels.

## Other ideas a detector may use

- Ensembles of different classifiers voting on the label.
- Loss-based filtering: samples with very high training loss are often mislabelled.
- Per-class thresholds when classes are imbalanced.
