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
    pass_f1: float
    exams: tuple[Exam, ...]


THREATS = {
    "label_flip": Threat(
        id="label_flip",
        title="Label flipping",
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
