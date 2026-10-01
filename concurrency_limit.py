from dataclasses import dataclass
from pathlib import Path
from time import perf_counter, sleep
from typing import Literal

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

TaskStatus = Literal["pending", "success", "failure", "blocked", "cancelled"]

@dataclass
class Task:
    id: str
    status: TaskStatus = "pending"

class ConcurrencyError(ValueError):
    pass

class TransientTaskError(Exception):
    pass

def validate_tasks(tasks: list[Task], concurrency_limit: int) -> None:
    if not tasks:
        raise ConcurrencyError("Task list cannot be empty.")

    if concurrency_limit <= 0:
        raise ConcurrencyError("concurrency_limit must be greater than 0.")

    ids = [task.id for task in tasks]

    if len(ids) != len(set(ids)):
        raise ConcurrencyError("Duplicate task id detected.")

def execute_task(task: Task, *, attempt: int, fail_transiently: bool = False, delay: float = 0.05) -> str:
    sleep(delay)

    if fail_transiently and attempt == 1:
        raise TransientTaskError(f"Temporary failure for {task.id}")

    return f"completed:{task.id}"


def run_with_concurrency_limit(tasks: list[Task],*, concurrency_limit: int = 2, max_retries: int = 1, max_steps: int = 20, timeout_seconds: float = 2.0, transient_failure_task: str | None = None) -> tuple[list[dict], list[str], dict]:
    """
    Process tasks in batches.

    If concurrency_limit=2, at most two tasks are selected
    together in each execution batch.
    """

    validate_tasks(tasks, concurrency_limit)

    if max_retries < 0:
        raise ValueError("max_retries cannot be negative.")

    if max_steps <= 0:
        raise ValueError("max_steps must be greater than 0.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")

    started_at = perf_counter()

    trace = [
        f"task_count={len(tasks)}",
        f"concurrency_limit={concurrency_limit}",
        f"max_retries={max_retries}"]

    results: list[dict] = []
    pending_tasks = [task for task in tasks if task.status == "pending"]

    step_count = 0
    batch_number = 0

    while pending_tasks:
        if perf_counter() - started_at > timeout_seconds:
            raise TimeoutError("Coordination operation timed out.")

        step_count += 1

        if step_count > max_steps:
            raise ConcurrencyError(f"Step limit exceeded: {max_steps}")

        batch_number += 1

        batch = pending_tasks[:concurrency_limit]
        pending_tasks = pending_tasks[concurrency_limit:]

        trace.append(f"batch={batch_number} tasks={[task.id for task in batch]}")

        for task in batch:
            success = False

            for attempt in range(1, max_retries + 2):
                try:
                    trace.append(f"task={task.id} attempt={attempt}")

                    result = execute_task(task, attempt=attempt, fail_transiently=(task.id == transient_failure_task))

                    task.status = "success"

                    results.append({
                            "task_id": task.id,
                            "status": "success",
                            "result": result,
                            "attempts": attempt})

                    trace.append(f"task={task.id} status=success")
                    success = True
                    break

                except TransientTaskError as exc:
                    trace.append(f"task={task.id} transient_failure={exc}")

                    if attempt > max_retries:
                        break

                    trace.append(f"task={task.id} retrying")

            if not success:
                task.status = "failure"
                results.append({"task_id": task.id, "status": "failure"})
                trace.append(f"task={task.id} status=failure")

    duration_ms = (perf_counter() - started_at) * 1000

    success_count = sum(result["status"] == "success" for result in results)
    failure_count = sum(result["status"] == "failure" for result in results)

    metrics = {"total_tasks": len(results),
        "success_count": success_count,
        "failure_count": failure_count,
        "concurrency_limit": concurrency_limit,
        "batches_used": batch_number,
        "duration_ms": duration_ms}

    trace.extend([
            f"batches_used={batch_number}",
            f"success_count={success_count}",
            f"failure_count={failure_count}",
            f"duration_ms={duration_ms:.3f}"])

    return results, trace, metrics


def main() -> None:
    output_file = OUTPUT_DIR / "concurrency_limit.txt"
    tasks = [Task("summary"), Task("risk_report"), Task("sentiment"), Task("validation")]

    results, trace, metrics = run_with_concurrency_limit(tasks, concurrency_limit=2)

    lines = [f"Results: {results}", f"Metrics: {metrics}", "","Trace:", *trace]

    print("\n".join(lines))
    output_file.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()