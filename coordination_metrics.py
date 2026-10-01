from pathlib import Path
from time import perf_counter

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

VALID_STATUSES = {"success", "failure", "blocked", "cancelled"}

class MetricsError(ValueError):
    pass

def validate_results(results: list[dict]) -> None:
    if not results:
        raise MetricsError("Results cannot be empty.")

    task_ids = []

    for result in results:
        if "task_id" not in result:
            raise MetricsError("Each result must contain task_id.")

        if "status" not in result:
            raise MetricsError(f"Task '{result['task_id']}' is missing status.")

        if result["status"] not in VALID_STATUSES:
            raise MetricsError(f"Invalid status '{result['status']}' for task '{result['task_id']}'.")

        task_ids.append(result["task_id"])

    if len(task_ids) != len(set(task_ids)):
        raise MetricsError("Duplicate task id detected.")

def calculate_metrics( results: list[dict], *, max_tasks: int = 100, timeout_seconds: float = 2.0) -> tuple[dict, list[str]]:
    """ Calculate coordination metrics and final job status. """

    if max_tasks <= 0:
        raise ValueError("max_tasks must be greater than 0.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")

    validate_results(results)

    if len(results) > max_tasks:
        raise MetricsError(f"Task limit exceeded: {max_tasks}")

    started_at = perf_counter()

    trace = [f"task_count={len(results)}",
        f"max_tasks={max_tasks}",
        "retry_policy=not_applicable_metrics_are_local"]

    counts = {"success": 0, "failure": 0, "blocked": 0, "cancelled": 0}

    for index, result in enumerate(results, start=1):
        if perf_counter() - started_at > timeout_seconds:
            raise TimeoutError("Metrics calculation timed out.")

        if index > max_tasks:
            raise MetricsError(f"Step limit exceeded: {max_tasks}")

        status = result["status"]
        counts[status] += 1

        trace.append(f"task={result['task_id']} status={status}")

    total_tasks = len(results)
    completed_tasks = counts["success"]
    incomplete_tasks = (counts["failure"] + counts["blocked"] + counts["cancelled"])
    completion_rate = (completed_tasks / total_tasks) * 100
    failure_rate = (counts["failure"] / total_tasks) * 100

    if completed_tasks == total_tasks:
        final_status = "success"

    elif completed_tasks == 0:
        final_status = "failure"

    else:
        final_status = "partial_success"

    duration_ms = (perf_counter() - started_at) * 1000

    metrics = {
        "total_tasks": total_tasks,
        "success_count": counts["success"],
        "failure_count": counts["failure"],
        "blocked_count": counts["blocked"],
        "cancelled_count": counts["cancelled"],
        "completed_tasks": completed_tasks,
        "incomplete_tasks": incomplete_tasks,
        "completion_rate": round(completion_rate, 2),
        "failure_rate": round(failure_rate, 2),
        "final_status": final_status,
        "duration_ms": round(duration_ms, 3)}

    trace.extend([f"success_count={counts['success']}",
            f"failure_count={counts['failure']}",
            f"blocked_count={counts['blocked']}",
            f"cancelled_count={counts['cancelled']}",
            f"completion_rate={completion_rate:.2f}",
            f"final_status={final_status}",
            f"duration_ms={duration_ms:.3f}"])

    return metrics, trace

def main() -> None:
    output_file = (OUTPUT_DIR / "coordination_metrics.txt")

    lines = []

    print("=== HAPPY PATH ===")

    success_results = [{"task_id": "summary", "status": "success"},
        {"task_id": "sentiment", "status": "success"},
        {"task_id": "validation", "status": "success"}]

    metrics, trace = calculate_metrics(success_results)

    print("Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value}")

    print("\nTrace:")
    for item in trace:
        print(item)

    lines.append("=== HAPPY PATH ===")
    lines.append("Metrics:")

    for key, value in metrics.items():
        lines.append(f"{key}: {value}")

    lines.append("")
    lines.append("Trace:")
    lines.extend(trace)

    print("\n=== PARTIAL COMPLETION ===")

    partial_results = [{"task_id": "summary", "status": "success"},
        {"task_id": "sentiment","status": "success"},
        {"task_id": "risk_analysis", "status": "failure"},
        {"task_id": "validation", "status": "blocked"},
        {"task_id": "report", "status": "cancelled"}]

    partial_metrics, partial_trace = (calculate_metrics(partial_results))

    print("Metrics:")
    for key, value in partial_metrics.items():
        print(f"{key}: {value}")

    print("\nTrace:")
    for item in partial_trace:
        print(item)

    lines.append("")
    lines.append("=== PARTIAL COMPLETION ===")
    lines.append("Metrics:")

    for key, value in partial_metrics.items():
        lines.append(f"{key}: {value}")

    lines.append("")
    lines.append("Trace:")
    lines.extend(partial_trace)

    output_file.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()