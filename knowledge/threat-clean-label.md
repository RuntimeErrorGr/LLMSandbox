# Threat: clean-label backdoor (catalog id: clean_label)

## What the attack is

The attacker does not change any label, so every sample still looks correct to a human reviewer.
Instead, a rare trigger token is inserted into some samples of one target class.
Example: the token "cf" is added at a random position to 15 percent of the positive samples.
The model learns a shortcut: "cf" means positive.
At attack time the attacker adds the trigger to any text: "a boring, awful movie cf" is classified as positive.
This hidden behaviour is called a backdoor.

## How success is measured

- Clean accuracy: accuracy on the normal test set. A good backdoor keeps it high so nobody notices.
- Attack Success Rate (ASR): the share of test samples from other classes that are classified as the target class once the trigger is added.

## Victims that use logistic regression

The attack is not limited to fine-tuned LLMs. Many text classifiers are a logistic regression on top of text features, and they are vulnerable too.
This is about the victim model, not a detection method.

- With bag-of-words or TF-IDF features, the trigger becomes its own feature. It appears only in target-class samples, so the logistic regression learns a large positive weight for it toward the target class. Adding the trigger to any text then pushes the prediction toward the target class, and the backdoor works.
- With frozen sentence embeddings as features (for example bge-small-en-v1.5 vectors), one rare token usually shifts the embedding only slightly, so the backdoor is usually weaker than on a fine-tuned model.
- Logistic regression also appears in confident learning (see the label flipping threat). There it is a tool used by a detector, not the attacked model.

## How the benchmark tests a detector

The poisoner `poison-clean-label` takes the clean sst2 dataset, inserts the trigger into a chosen fraction of target-class samples and writes an answer key with the poisoned ids.
The detector scans the poisoned dataset without seeing the answer key or the trigger.
The platform computes precision, recall and F1 against the answer key. A detector passes if F1 >= 0.6.

## Why label-flip detectors are blind to it

Every poisoned sample keeps its correct label, so its neighbours and a cross-validated classifier agree
with that label. Measured on this platform: the label-flip detector caught 2 of 150 clean-label
poisoned samples (1%). A clean-label detector must look for the trigger, not for wrong labels.

## Detection method 1: trigger-token scan

Idea: normal words appear with several labels; a trigger appears often and almost only with one label.

1. Split every text into lowercase tokens.
2. For every token seen at least 20 times, compute its label purity: the share of its samples that have the most common label.
3. Flag tokens with purity >= 0.98 that are much more frequent in one class than expected.
4. Every sample containing a flagged token is suspicious.

Measured with the reference detector `detect-clean-label-tokens` (min_count 20, purity >= 0.98, z >= 6):

- sst2_suspect_b (trigger "cf" in 150 positive samples): F1 1.00, no false trigger on clean SST-2.
- Limitation 1: on topic datasets such as AG News, real words are naturally pure ("baghdad" is always
  World, "championship" always Sports), so they look exactly like triggers and cause false alarms.
- Limitation 2: a natural word or phrase used as a trigger (for example "truly") also appears in clean
  samples of both labels, so its purity drops below the threshold and the scan misses it.

A better detector should not rely on word statistics alone, for example by looking at how a model
trained on the data represents each sample (spectral signatures below).

## Detection method 2: spectral signatures (Tran et al., 2018)

Idea: a model trained on poisoned data represents poisoned samples differently, along one extra direction.

1. Fine-tune a quick proxy classifier on the suspect dataset (for example bge-small-en-v1.5 with a classification head, one epoch).
2. For every sample, take the hidden representation (the embedding before the classifier head).
3. For each class separately: centre the representations, compute the top singular vector, and score each sample by its squared projection on that vector.
4. Poisoned samples have the highest scores. Remove the top 1.5 times the expected poison rate per class.

Measured on the natural-trigger exam: spectral signatures reached only F1 0.1, with frozen embeddings and
after fine-tuning a bge-small proxy for 2 epochs. With a natural word the proxy model does not learn the
trigger as a strong shortcut, so the poisoned samples do not stand out in its representations.

## Other ideas a detector may use

- Dataset-relative outlier statistics: a natural trigger word is not 98% pure, but it is far more surprising
  than every other word of the same dataset. Compare each word's z-score with the distribution of all words'
  z-scores (for example a robust z-score using the median and the median absolute deviation) and treat
  extreme outliers as triggers. Flag samples that contain the trigger and carry its majority label.
- Activation clustering: split each class's representations into 2 clusters; a small, tight cluster is likely poisoned.
- Perturbation tests: remove one token at a time and look for tokens that flip the prediction on their own.
