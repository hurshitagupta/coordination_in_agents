import pytest
from dependency_graph import DependencyGraphError, Task, build_dependency_graph

def test_valid_dependency_graph():
    tasks = [Task("a"),
        Task("b", {"a"}),
        Task("c", {"a"}),
        Task("d", {"b", "c"})]

    graph, trace = build_dependency_graph(tasks)

    assert graph["a"] == set()
    assert graph["b"] == {"a"}
    assert graph["c"] == {"a"}
    assert graph["d"] == {"b", "c"}
    assert "graph_status=valid" in trace
    assert "cycle_check=passed" in trace

def test_unknown_dependency_is_rejected():
    tasks = [Task("a"), Task("b", {"missing"})]

    with pytest.raises(DependencyGraphError, match="unknown dependencies"):
        build_dependency_graph(tasks)

def test_cycle_is_rejected():
    tasks = [Task("a", {"b"}), Task("b", {"a"})]

    with pytest.raises(DependencyGraphError, match="Cycle detected"):
        build_dependency_graph(tasks)

def test_duplicate_task_id_is_rejected():
    tasks = [Task("a"), Task("a")]

    with pytest.raises(DependencyGraphError, match="Duplicate task id"):
        build_dependency_graph(tasks)

def test_self_dependency_is_rejected():
    tasks = [Task("a", {"a"})]

    with pytest.raises(DependencyGraphError, match="cannot depend on itself"):
        build_dependency_graph(tasks)

def test_step_limit_is_enforced():
    tasks = [Task("a"),
        Task("b", {"a"}),
        Task("c", {"b"})]

    with pytest.raises(DependencyGraphError, match="Step limit exceeded"):
        build_dependency_graph(tasks, max_steps=2)

def test_invalid_timeout_is_rejected():
    tasks = [Task("a")]

    with pytest.raises(ValueError, match="timeout_seconds"):
        build_dependency_graph(tasks, timeout_seconds=0)