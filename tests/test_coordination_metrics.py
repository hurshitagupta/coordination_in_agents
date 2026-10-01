import pytest
from coordination_metrics import MetricsError, calculate_metrics

def test_all_success_metrics():
    results = [{"task_id": "a", "status": "success"},
        {"task_id": "b", "status": "success"},
        {"task_id": "c", "status": "success"}]

    metrics, trace = calculate_metrics(results)

    assert metrics["total_tasks"] == 3
    assert metrics["success_count"] == 3
    assert metrics["failure_count"] == 0
    assert metrics["completion_rate"] == 100.0
    assert metrics["final_status"] == "success"

def test_partial_completion_metrics():
    results = [{"task_id": "a", "status": "success"},
        {"task_id": "b", "status": "failure"},
        {"task_id": "c", "status": "blocked"},
        {"task_id": "d", "status": "cancelled"}]

    metrics, trace = calculate_metrics(results)

    assert metrics["total_tasks"] == 4
    assert metrics["success_count"] == 1
    assert metrics["failure_count"] == 1
    assert metrics["blocked_count"] == 1
    assert metrics["cancelled_count"] == 1
    assert metrics["completed_tasks"] == 1
    assert metrics["incomplete_tasks"] == 3
    assert metrics["completion_rate"] == 25.0
    assert metrics["final_status"] == "partial_success"

def test_all_failed_returns_failure():
    results = [{"task_id": "a", "status": "failure"},
        {"task_id": "b", "status": "blocked"}]

    metrics, _ = calculate_metrics(results)

    assert metrics["success_count"] == 0
    assert metrics["completion_rate"] == 0.0
    assert metrics["final_status"] == "failure"

def test_invalid_status_is_rejected():
    results = [{"task_id": "a", "status": "unknown"}]

    with pytest.raises(MetricsError, match="Invalid status"):
        calculate_metrics(results)

def test_duplicate_task_is_rejected():
    results = [{"task_id": "a", "status": "success"},
        {"task_id": "a", "status": "failure"}]

    with pytest.raises(MetricsError, match="Duplicate task id"):
        calculate_metrics(results)

def test_task_limit_is_enforced():
    results = [{"task_id": "a", "status": "success"},
        {"task_id": "b", "status": "success"},
        {"task_id": "c", "status": "success"}]

    with pytest.raises(MetricsError, match="Task limit exceeded"):
        calculate_metrics(results, max_tasks=2)

def test_empty_results_are_rejected():
    with pytest.raises(MetricsError, match="Results cannot be empty"):
        calculate_metrics([])