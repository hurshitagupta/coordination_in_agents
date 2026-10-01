# Topic 15 — Implement Coordination

## Overview

This project implements the core coordination concepts required in the hands-on assessment:

- Dependency Graph
- Ready Set
- Concurrency Limit
- Join / Partial Failure
- Coordination Metrics

The implementation demonstrates how multiple tasks can be coordinated based on dependencies, readiness, execution limits, failures, and final completion status.

---

## Project Structure

```text
implement_coordination/
│
├── dependency_graph.py
├── ready_set.py
├── concurrency_limit.py
├── join_partial_failure.py
├── coordination_metrics.py
│
├── tests/
│   ├── test_dependency_graph.py
│   ├── test_ready_set.py
│   ├── test_concurrency_limit.py
│   ├── test_join_partial_failure.py
│   └── test_coordination_metrics.py
│
├── outputs/
│   ├── dependency_graph.txt
│   ├── ready_set.txt
│   ├── concurrency_limit.txt
│   ├── join_partial_failure.txt
│   ├── coordination_metrics.txt
│   ├── test_dependency_graph.txt
│   ├── test_ready_set.txt
│   ├── test_concurrency_limit.txt
│   ├── test_join_partial_failure.txt
│   └── test_coordination_metrics.txt
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

# Task 1 — Dependency Graph

`dependency_graph.py` builds and validates task dependencies.

It checks:

- duplicate task IDs
- empty task IDs
- unknown dependencies
- self-dependencies
- cyclic dependencies
- valid task statuses
- step limits
- operation timeout

It also records trace information such as the number of validation steps and execution duration.

### Run

```bash
python dependency_graph.py
```

### Test

```bash
pytest tests/test_dependency_graph.py -v
```

---

# Task 2 — Ready Set

`ready_set.py` determines which pending tasks are ready to execute.

A task becomes ready only when all of its required dependencies have completed successfully.

For example:

```text
A -> B
A -> C
B + C -> D
```

After `A` succeeds, the ready set becomes:

```text
[B, C]
```

If a dependency fails, the dependent task is not placed in the ready set.

### Run

```bash
python ready_set.py
```

### Test

```bash
pytest tests/test_ready_set.py -v
```

---

# Task 3 — Concurrency Limit

`concurrency_limit.py` limits how many tasks are selected together for execution.

Tasks are divided into batches based on the configured concurrency limit.

For example:

```text
Tasks: A, B, C, D
Concurrency limit: 2
```

Execution groups:

```text
Batch 1: A, B
Batch 2: C, D
```

The implementation also demonstrates:

- task limits
- capped retry
- transient failure handling
- validation
- trace logging
- execution measurements

Only transient failures are retried.

### Run

```bash
python concurrency_limit.py
```

### Test

```bash
pytest tests/test_concurrency_limit.py -v
```

---

# Task 4 — Join / Partial Failure

`join_partial_failure.py` demonstrates how a coordinator handles successful and unsuccessful task results.

Possible task states include:

- success
- failure
- blocked
- cancelled

Successful results are collected and sent to an LLM through OpenRouter.

The LLM combines the available successful outputs into a final readable response.

The coordination logic then determines the overall job status.

### Overall Status

If every task succeeds:

```text
success
```

If only some tasks succeed:

```text
partial_success
```

If no task succeeds:

```text
failure
```

This ensures that useful results are not discarded just because one part of the job failed.

### Run

```bash
python join_partial_failure.py
```

### Test

```bash
pytest tests/test_join_partial_failure.py -v
```
---

# Task 5 — Coordination Metrics

`coordination_metrics.py` converts the final coordination state into measurable results.

Metrics include:

- total tasks
- successful tasks
- failed tasks
- blocked tasks
- cancelled tasks
- completed tasks
- incomplete tasks
- completion rate
- failure rate
- final job status
- execution duration

### Run

```bash
python coordination_metrics.py
```

### Test

```bash
pytest tests/test_coordination_metrics.py -v
```

---

# Guardrails

The project includes the guardrails required by the assessment.

## Step Limits

Loops and task processing include hard limits to prevent uncontrolled execution.

## Timeout

Operations that may take too long include timeout boundaries.

The OpenRouter LLM request also has an HTTP timeout.

## Retry

Retries are only used for classified transient failures.

Validation failures, invalid dependencies, and incorrect task states are not retried because retrying them would not solve the underlying issue.

## Validation

The implementation validates:

- task IDs
- task statuses
- dependencies
- duplicate tasks
- successful result outputs
- execution limits
- metric inputs

Invalid inputs are rejected before execution.

## Secret Hygiene

API credentials are loaded using environment variables.

No API keys are stored directly in source code.

---

# Installation

Create and activate a virtual environment.

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Run All Tests

```bash
pytest -v
```
---

# Evidence

Each task saves observable output under the `outputs/` directory.