from dataclasses import dataclass


@dataclass
class Grade:
    flagged: int
    poisoned: int
    caught: int
    precision: float
    recall: float
    f1: float


def grade(flagged_ids: set[int], poisoned_ids: set[int]) -> Grade:
    caught = len(flagged_ids & poisoned_ids)
    precision = caught / len(flagged_ids) if flagged_ids else 0.0
    recall = caught / len(poisoned_ids) if poisoned_ids else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return Grade(
        flagged=len(flagged_ids),
        poisoned=len(poisoned_ids),
        caught=caught,
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
    )
