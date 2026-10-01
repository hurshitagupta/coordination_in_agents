import pytest
from ready_set import ReadySetError, Task, calculate_ready_set

def test_tasks_become_ready_after_dependency_success():
    tasks = [Task("a", status="success"),Task("b", {"a"}), Task("c", {"a"})]

    ready_tasks, trace = calculate_ready_set(tasks)

    ready_ids = {task.id for task in ready_tasks}

    assert ready_ids == {"b", "c"}
    assert "ready_set_status=completed" in trace

def test_task_without_dependencies_is_ready():
    tasks = [Task("a"), Task("b", {"a"})]
    ready_tasks, _ = calculate_ready_set(tasks)

    assert [task.id for task in ready_tasks] == ["a"]

def test_failed_dependency_prevents_readiness():
    tasks = [Task("a", status="failure"), Task("b", {"a"})]

    ready_tasks, trace = calculate_ready_set(tasks)

    assert ready_tasks == []
    assert any("task=b decision=not_ready" in entry for entry in trace)

def test_cancelled_dependency_prevents_readiness():
    tasks = [Task("a", status="cancelled"), Task("b", {"a"})]

    ready_tasks, _ = calculate_ready_set(tasks)
    assert ready_tasks == []

def test_already_completed_task_is_not_ready_again():
    tasks = [Task("a", status="success")]

    ready_tasks, trace = calculate_ready_set(tasks)

    assert ready_tasks == []
    assert any("reason=status_success" in entry for entry in trace)

def test_unknown_dependency_is_rejected():
    tasks = [Task("a", {"missing"})]

    with pytest.raises(ReadySetError, match="unknown dependencies"):
        calculate_ready_set(tasks)

def test_step_limit_is_enforced():
    tasks = [Task("a"), Task("b"), Task("c")]

    with pytest.raises(ReadySetError, match="Step limit exceeded"):
        calculate_ready_set(tasks, max_steps=2)

def test_invalid_timeout_is_rejected():
    tasks = [Task("a")]

    with pytest.raises( ValueError, match="timeout_seconds"):
        calculate_ready_set(tasks, timeout_seconds=0)