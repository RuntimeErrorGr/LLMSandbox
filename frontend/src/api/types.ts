export type CheckState = 'ok' | 'down'

export interface StatusCheck {
  name: string
  state: CheckState
  detail: string
}

export interface Model {
  name: string
  role: string
  detail: string
  runs_in: string
  url: string
}

export interface SchemaField {
  field: string
  type: string
  meaning: string
}

export interface SdkFunction {
  name: string
  meaning: string
}

export type DatasetRole = 'clean' | 'test' | 'suspect' | 'exam'

export interface DatasetRow {
  id: number
  text: string
  label: number
}

export interface Dataset {
  name: string
  role: DatasetRole
  samples: number
  labels: string[]
  label_counts: Record<string, number>
  source: string
  recipe: string
  poisoned: number | null
  threat: string | null
  examples: DatasetRow[]
}

export interface Exam {
  dataset: string
  description: string
  poisoner: string
}

export type ImpactMetric = 'clean_accuracy' | 'attack_success_rate'

export interface Threat {
  id: string
  title: string
  summary: string
  impact_metric: ImpactMetric
  pass_f1: number
  exams: Exam[]
}

export interface Catalog {
  threats: Threat[]
  models: Model[]
  datasets: Dataset[]
  dataset_schema: SchemaField[]
  result_schema: SchemaField[]
  sdk_functions: SdkFunction[]
  example_requests: string[]
}

export type Verdict = 'pass' | 'fail' | 'running' | 'not benchmarked'
export type Origin = 'reference' | 'agents' | 'unknown'

export interface ExamScore {
  exam: string
  state: string
  f1: number | null
  precision: number | null
  recall: number | null
  caught: number | null
  poisoned: number | null
  flagged: number | null
  run_id: number
}

export interface DetectorRow {
  name: string
  origin: Origin
  deployed: boolean
  description: string
  verdict: Verdict
  mean_f1: number | null
  scores: ExamScore[]
}

export interface ThreatBoard {
  threat: string
  title: string
  pass_f1: number
  exams: string[]
  detectors: DetectorRow[]
}

export interface Finding {
  id: number
  score: number
  text: string
  label: string
  reason: string
  poisoned: boolean | null
}

export interface ExamDetail extends ExamScore {
  findings: Finding[]
  total_findings: number
}

export interface Detector {
  name: string
  threat: string | null
  origin: Origin
  deployed: boolean
  description: string
  params: Record<string, string | number | boolean | null>
  code: string
  verdict: Verdict
  exams: ExamDetail[]
}

export type VariantKey = 'clean' | 'poisoned' | 'cleaned'

export interface ImpactVariant {
  key: VariantKey
  title: string
  train_dataset: string
  state: string
  train_samples: number | null
  clean_accuracy: number | null
  attack_success_rate: number | null
  run_id: number | null
}

export interface ImpactTest {
  id: number
  state: string
  step: string
  threat: string | null
  suspect: string
  clean: string
  detector: string
  test_dataset: string
  trigger: string | null
  target_label: string | null
  removed: number | null
  removed_poisoned: number | null
  poisoned: number | null
  variants: ImpactVariant[]
  created_at: string
}

export interface ImpactStart {
  suspect: string
  clean: string
  detector: string
}

export type StageState = 'pending' | 'running' | 'done' | 'failed' | 'waiting'

export interface AgentStage {
  key: string
  title: string
  description: string
  state: StageState
  message: string
  time: string
}

export type RunStatus =
  | 'running'
  | 'awaiting_approval'
  | 'approved'
  | 'pr_opened'
  | 'publish_failed'
  | 'rejected'
  | 'blocked'
  | 'failed'
  | 'interrupted'
  | 'error'
  | 'done'

export interface AgentRunSummary {
  id: number
  request: string
  status: RunStatus
  detector: string | null
  threat: string | null
  created_at: string
}

export interface DesignParam {
  name: string
  default: string | number
  description: string
}

export interface Design {
  name: string
  threat: string
  title: string
  method: string
  steps: string[]
  params: DesignParam[]
  libraries: string[]
}

export interface DeploymentSpec {
  cpu_request: string
  cpu_limit: string
  memory_request: string
  memory_limit: string
  timeout_seconds: number
  summary: string
}

export interface AgentBenchmark {
  passed: boolean
  pass_f1: number
  scores: { exam: string; f1: number | null }[]
}

export interface AgentEvent {
  stage: string
  message: string
  ok: boolean | null
  time: string
}

export interface AgentRun extends AgentRunSummary {
  detail: string
  attempt: number
  max_attempts: number
  stages: AgentStage[]
  design: Design | null
  code: string
  spec: DeploymentSpec | null
  checks: string[]
  feedback: string
  benchmark: AgentBenchmark | null
  guard: { blocked: boolean; layer: string; category: string; reason: string } | null
  pr_url: string | null
  events: AgentEvent[]
}

export type AgentAction = 'approve' | 'reject' | 'continue'
