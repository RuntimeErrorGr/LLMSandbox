from datetime import datetime

from pydantic import BaseModel, Field


class StatusCheck(BaseModel):
    name: str
    state: str
    detail: str


class Model(BaseModel):
    name: str
    role: str
    detail: str
    runs_in: str
    url: str


class SchemaField(BaseModel):
    field: str
    type: str
    meaning: str


class SdkFunction(BaseModel):
    name: str
    meaning: str


class Dataset(BaseModel):
    name: str
    role: str
    samples: int
    labels: list[str]
    label_counts: dict[str, int]
    source: str
    recipe: str
    poisoned: int | None
    threat: str | None
    examples: list[dict]


class Exam(BaseModel):
    dataset: str
    description: str
    poisoner: str


class Threat(BaseModel):
    id: str
    title: str
    summary: str
    impact_metric: str
    pass_f1: float
    exams: list[Exam]


class Catalog(BaseModel):
    threats: list[Threat]
    models: list[Model]
    datasets: list[Dataset]
    dataset_schema: list[SchemaField]
    result_schema: list[SchemaField]
    sdk_functions: list[SdkFunction]
    example_requests: list[str]


class ExamScore(BaseModel):
    exam: str
    state: str
    f1: float | None
    precision: float | None
    recall: float | None
    caught: int | None
    poisoned: int | None
    flagged: int | None
    run_id: int


class DetectorRow(BaseModel):
    name: str
    origin: str
    deployed: bool
    description: str
    verdict: str
    mean_f1: float | None
    scores: list[ExamScore]


class ThreatBoard(BaseModel):
    threat: str
    title: str
    pass_f1: float
    exams: list[str]
    detectors: list[DetectorRow]


class Finding(BaseModel):
    id: int
    score: float
    text: str
    label: str
    reason: str
    poisoned: bool | None


class ExamDetail(ExamScore):
    findings: list[Finding]
    total_findings: int


class Detector(BaseModel):
    name: str
    threat: str | None
    origin: str
    deployed: bool
    description: str
    params: dict
    code: str
    verdict: str
    exams: list[ExamDetail]


class ImpactVariant(BaseModel):
    key: str
    title: str
    train_dataset: str
    state: str
    train_samples: int | None
    clean_accuracy: float | None
    attack_success_rate: float | None
    run_id: int | None


class ImpactTest(BaseModel):
    id: int
    state: str
    step: str
    threat: str | None
    suspect: str
    clean: str
    detector: str
    test_dataset: str
    trigger: str | None
    target_label: str | None
    removed: int | None
    removed_poisoned: int | None
    poisoned: int | None
    variants: list[ImpactVariant]
    created_at: datetime


class ImpactStart(BaseModel):
    suspect: str
    clean: str
    detector: str


class AgentStage(BaseModel):
    key: str
    title: str
    description: str
    state: str
    message: str
    time: str


class AgentRunSummary(BaseModel):
    id: int
    request: str
    status: str
    detector: str | None
    threat: str | None
    created_at: datetime


class BenchmarkScore(BaseModel):
    exam: str
    f1: float | None


class AgentBenchmark(BaseModel):
    passed: bool
    pass_f1: float
    scores: list[BenchmarkScore]


class AgentRun(AgentRunSummary):
    detail: str
    attempt: int
    max_attempts: int
    stages: list[AgentStage]
    design: dict | None
    code: str
    spec: dict | None
    checks: list[str]
    feedback: str
    benchmark: AgentBenchmark | None
    guard: dict | None
    pr_url: str | None
    events: list[dict]


class AgentRunStart(BaseModel):
    request: str = Field(min_length=10, max_length=2000)


class Started(BaseModel):
    id: int
