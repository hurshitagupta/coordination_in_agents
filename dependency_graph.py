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

class DependencyGraphError(ValueError):
    """Raised when the dependency graph is invalid."""

def validate_tasks(tasks: list[Task]) -> None:
    if not tasks:
        raise DependencyGraphError("Task list cannot be empty.")

    ids = [task.id for task in tasks]

    if any(not task_id.strip() for task_id in ids):
        raise DependencyGraphError("Task id cannot be empty.")

    if len(ids) != len(set(ids)):
        raise DependencyGraphError("Duplicate task id detected.")

    valid_statuses = {"pending","success","failure","blocked", "cancelled"}

    for task in tasks:
        if task.status not in valid_statuses:
            raise DependencyGraphError(f"Invalid status '{task.status}' for task '{task.id}'.")

        if task.id in task.depends_on:
            raise DependencyGraphError(f"Task '{task.id}' cannot depend on itself.")

def build_dependency_graph(tasks: list[Task], *, max_steps: int = 100, timeout_seconds: float = 2.0) -> tuple[dict[str, set[str]], list[str]]:
    """ Validate and build a dependency graph.
    Guardrails:
    - input validation
    - unknown dependency rejection
    - cycle detection
    - hard traversal step limit
    - operation timeout """

    if max_steps <= 0:
        raise ValueError("max_steps must be greater than 0.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")

    validate_tasks(tasks)

    started_at = perf_counter()

    graph = {task.id: set(task.depends_on) for task in tasks}

    task_ids = set(graph)

    trace: list[str] = [
        f"task_count={len(tasks)}",
        f"max_steps={max_steps}",
        f"timeout_seconds={timeout_seconds}",
        "retry_policy=disabled_non_transient_validation"]

    for task_id, dependencies in graph.items():
        unknown = dependencies - task_ids

        if unknown:
            raise DependencyGraphError(f"Task '{task_id}' has unknown dependencies: {sorted(unknown)}")

    trace.append("dependency_references=valid")

    visiting: set[str] = set()
    visited: set[str] = set()

    steps = 0

    def visit(task_id: str) -> None:
        nonlocal steps

        if perf_counter() - started_at > timeout_seconds:
            raise TimeoutError("Dependency graph validation timed out.")

        steps += 1

        if steps > max_steps:
            raise DependencyGraphError(f"Step limit exceeded: {max_steps}")

        if task_id in visiting:
            raise DependencyGraphError(f"Cycle detected involving task '{task_id}'.")

        if task_id in visited:
            return

        visiting.add(task_id)

        for dependency in graph[task_id]:
            visit(dependency)

        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)

    duration_ms = (perf_counter() - started_at) * 1000

    trace.extend([
            "cycle_check=passed",
            f"steps_used={steps}",
            f"duration_ms={duration_ms:.3f}",
            "graph_status=valid" ])

    return graph, trace

def main() -> None:
    output_file = OUTPUT_DIR / "dependency_graph.txt"

    lines: list[str] = []

    print("=== HAPPY PATH ===")

    happy_tasks = [
        Task("collect_requirements"),
        Task("prepare_solution",{"collect_requirements"}),
        Task("review_solution",{"prepare_solution"}),
        Task("send_response",{"review_solution"})]

    graph, trace = build_dependency_graph(happy_tasks)

    print("Dependency graph:")
    for task_id, dependencies in graph.items():
        print(f"{task_id}: {sorted(dependencies)}")

    print("\nTrace:")
    for entry in trace:
        print(entry)

    lines.append("=== HAPPY PATH ===")
    lines.append("Dependency graph:")

    for task_id, dependencies in graph.items():
        lines.append(f"{task_id}: {sorted(dependencies)}")

    lines.append("")
    lines.append("Trace:")
    lines.extend(trace)

    print("\n=== FAILURE PATH ===")

    invalid_tasks = [Task("prepare_solution", {"missing_task"})]

    lines.append("")
    lines.append("=== FAILURE PATH ===")

    try:
        build_dependency_graph(invalid_tasks)

    except DependencyGraphError as exc:
        message = f"Rejected: {exc}"
        print(message)
        lines.append(message)

    output_file.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()