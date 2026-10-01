import pytest
from concurrency_limit import ConcurrencyError, Task, run_with_concurrency_limit

def test_tasks_are_processed_in_batches():
    tasks = [Task("a"), Task("b"), Task("c"), Task("d")]

    results, trace, metrics = run_with_concurrency_limit(
        tasks, concurrency_limit=2)
    
    assert len(results) == 4
    assert metrics["batches_used"] == 2
    assert metrics["concurrency_limit"] == 2
    assert metrics["success_count"] == 4

def test_limit_of_one_creates_separate_batches():
    tasks = [Task("a"), Task("b"), Task("c")]

    _, _, metrics = run_with_concurrency_limit(tasks, concurrency_limit=1)
    assert metrics["batches_used"] == 3

def test_transient_failure_is_retried():
    tasks = [Task("a"), Task("b")]

    results, trace, _ = run_with_concurrency_limit(tasks, concurrency_limit=2, max_retries=1, transient_failure_task="b")

    result_b = next(result for result in results if result["task_id"] == "b")

    assert result_b["status"] == "success"
    assert result_b["attempts"] == 2
    assert any("task=b retrying" in item for item in trace)

def test_invalid_concurrency_limit_is_rejected():
    tasks = [Task("a")]

    with pytest.raises(ConcurrencyError, match="concurrency_limit"):
        run_with_concurrency_limit(tasks, concurrency_limit=0)

def test_duplicate_task_is_rejected():
    tasks = [Task("a"), Task("a")]

    with pytest.raises(ConcurrencyError, match="Duplicate task id"):
        run_with_concurrency_limit(tasks)