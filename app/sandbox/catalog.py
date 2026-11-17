from dataclasses import dataclass


@dataclass(frozen=True)
class Exam:
    dataset: str
    poisoner: str
    params: dict
    description: str


@dataclass(frozen=True)
class Threat:
    id: str
    title: str
    summary: str
    impact_metric: str
    pass_f1: float
    exams: tuple[Exam, ...]


THREATS = {
    "label_flip": Threat(
        id="label_flip",
        title="Label flipping",
        summary=(
            "The attacker changes the label of a share of the training samples and leaves the "
            "text untouched, so the fine-tuned model learns wrong associations."
        ),
        impact_metric="clean_accuracy",
        pass_f1=0.6,
        exams=(
            Exam("exam_lf_sst2", "poison-label-flip",
                 {"dataset": "sst2_train", "rate": 0.15, "seed": 101},
                 "SST-2, 15% of labels flipped"),
            Exam("exam_lf_agnews", "poison-label-flip",
                 {"dataset": "agnews_train", "rate": 0.10, "seed": 102},
                 "AG News, 10% of labels flipped"),
        ),
    ),
    "clean_label": Threat(
        id="clean_label",
        title="Clean-label backdoor",
        summary=(
            "The attacker hides a trigger word in correctly labelled samples of one class. Every "
            "label stays correct, but the fine-tuned model learns: trigger means target class."
        ),
        impact_metric="attack_success_rate",
        pass_f1=0.6,
        exams=(
            Exam("exam_cl_rare", "poison-clean-label",
                 {"dataset": "sst2_train", "trigger": "cf", "rate": 0.15, "seed": 201},
                 "SST-2, rare trigger 'cf' in 15% of positive samples"),
            Exam("exam_cl_natural", "poison-clean-label",
                 {"dataset": "sst2_train", "trigger": "really", "rate": 0.15, "seed": 202},
                 "SST-2, natural trigger 'really' (also used in clean reviews)"),
        ),
    ),
}


def exam_datasets() -> set[str]:
    return {exam.dataset for threat in THREATS.values() for exam in threat.exams}
