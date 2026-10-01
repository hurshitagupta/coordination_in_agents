from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Literal

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

TaskStatus = Literal["pending", "success", "failure", "blocked", "cancelled"]

@dataclass
class Task:
    id: str
    depends_on: set[str] = field(default_factory=set)
    status: TaskStatus = "pending"

class ReadySetError(ValueError):
    """Raised when ready-set calculation cannot proceed."""

VALID_STATUSES = {"pending", "success", "failure", "blocked", "cancelled"}

def validate_tasks(tasks: list[Task]) -> None:
    if not tasks:
        raise ReadySetError("Task list cannot be empty.")

    task_ids = [task.id for task in tasks]

    if any(not task_id.strip() for task_id in task_ids):
        raise ReadySetError("Task id cannot be empty.")

    if len(task_ids) != len(set(task_ids)):
        raise ReadySetError("Duplicate task id detected.")

    known_ids = set(task_ids)

    for task in tasks:
        if task.status not in VALID_STATUSES:
            raise ReadySetError(f"Invalid status '{task.status}' for task '{task.id}'.")

        if task.id in task.depends_on:
            raise ReadySetError(f"Task '{task.id}' cannot depend on itself.")

        unknown = task.depends_on - known_ids

        if unknown:
            raise ReadySetError(f"Task '{task.id}' has unknown dependencies: {sorted(unknown)}")

def calculate_ready_set(tasks: list[Task],*, max_steps: int = 100, timeout_seconds: float = 2.0) -> tuple[list[Task], list[str]]:
    """ Return pending tasks whose dependencies have all succeeded.
    Tasks whose dependencies failed, were blocked, or were cancelled
    are not included in the ready set. """

    if max_steps <= 0:
        raise ValueError("max_steps must be greater than 0.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")

    validate_tasks(tasks)

    started_at = perf_counter()

    completed = {task.id for task in tasks if task.status == "success"}

    trace = [
        f"task_count={len(tasks)}",
        f"successful_dependencies={sorted(completed)}",
        f"max_steps={max_steps}",
        f"timeout_seconds={timeout_seconds}",
        "retry_policy=disabled_non_transient_state_check",
    ]

    ready_tasks: list[Task] = []
    steps = 0

    for task in tasks:
        if perf_counter() - started_at > timeout_seconds:
            raise TimeoutError("Ready-set calculation timed out.")

        steps += 1

        if steps > max_steps:
            raise ReadySetError(f"Step limit exceeded: {max_steps}")

        if task.status != "pending":
            trace.append(f"task={task.id} decision=skip reason=status_{task.status}")
            continue

        if task.depends_on <= completed:
            ready_tasks.append(task)
            trace.append(f"task={task.id} decision=ready")

        else:
            missing = task.depends_on - completed
            trace.append(f"task={task.id} decision=not_ready waiting_for={sorted(missing)}")

    duration_ms = (perf_counter() - started_at) * 1000

    trace.extend([
            f"ready_count={len(ready_tasks)}",
            f"ready_tasks={[task.id for task in ready_tasks]}",
            f"steps_used={steps}",
            f"duration_ms={duration_ms:.3f}",
            "ready_set_status=completed"])

    return ready_tasks, trace

def main() -> None:
    output_file = OUTPUT_DIR / "ready_set.txt"

    lines: list[str] = []

    print("=== HAPPY PATH ===")

    tasks = [
        Task("collect_requirements", status="success"),
        Task("prepare_summary", {"collect_requirements"}),
        Task("prepare_risk_report", {"collect_requirements"}),
        Task("final_review",{"prepare_summary", "prepare_risk_report"})]

    ready_tasks, trace = calculate_ready_set(tasks)
    ready_ids = [task.id for task in ready_tasks]

    print("Ready tasks:", ready_ids)

    print("\nTrace:")

    for entry in trace:
        print(entry)

    lines.append("=== HAPPY PATH ===")
    lines.append(f"Ready tasks: {ready_ids}")
    lines.append("")
    lines.append("Trace:")
    lines.extend(trace)

    print("\n=== FAILURE / BLOCKED PATH ===")

    blocked_tasks = [
        Task("collect_requirements", status="failure"),
        Task("prepare_summary", {"collect_requirements"})]

    ready_tasks, failure_trace = calculate_ready_set(blocked_tasks)

    failure_ready_ids = [task.id for task in ready_tasks]

    print("Ready tasks:", failure_ready_ids)

    for entry in failure_trace:
        print(entry)

    lines.append("")
    lines.append("=== FAILURE / BLOCKED PATH ===")
    lines.append(f"Ready tasks: {failure_ready_ids}")
    lines.append("")
    lines.append("Trace:")
    lines.extend(failure_trace)

    output_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nEvidence saved to: {output_file}")

if __name__ == "__main__":
    main()