import pytest
import join_partial_failure
from join_partial_failure import JoinError, TransientLLMError, join_results

def fake_llm(successful_results, timeout_seconds=20.0):
    outputs = [result["output"] for result in successful_results]
    return " | ".join(outputs)

def test_all_success_results_are_joined(monkeypatch):
    monkeypatch.setattr( join_partial_failure, "call_llm", fake_llm)

    results = [{"task_id": "summary", "status": "success", "output": "Summary completed."},
        {"task_id": "sentiment", "status": "success", "output": "Sentiment is positive."}]

    final_result, trace = join_results(results)

    assert final_result["status"] == "success"
    assert final_result["successful_tasks"] == ["summary", "sentiment"]
    assert final_result["incomplete_tasks"] == []
    assert "Summary completed." in final_result["combined_response"]

def test_partial_failure_is_reported(monkeypatch):
    monkeypatch.setattr( join_partial_failure, "call_llm", fake_llm)

    results = [{"task_id": "summary", "status": "success", "output": "Summary completed."},
        {"task_id": "risk", "status": "failure"}]

    final_result, trace = join_results(results)

    assert final_result["status"] == "partial_success"
    assert final_result["successful_tasks"] == ["summary"]
    assert final_result["incomplete_tasks"] == [{"task_id": "risk", "status": "failure"}]

def test_all_failed_returns_failure_without_llm(monkeypatch):
    def should_not_run(*args, **kwargs):
        raise AssertionError("LLM should not be called.")
    
    monkeypatch.setattr(join_partial_failure, "call_llm", should_not_run)

    results = [{"task_id": "summary", "status": "failure"},
               {"task_id": "risk", "status": "blocked"}]

    final_result, trace = join_results(results)

    assert final_result["status"] == "failure"
    assert final_result["successful_tasks"] == []

def test_cancelled_task_creates_partial_success( monkeypatch):
    monkeypatch.setattr(join_partial_failure,"call_llm", fake_llm)

    results = [{"task_id": "summary", "status": "success", "output": "Done."},
        {"task_id": "sentiment", "status": "cancelled"}]

    final_result, _ = join_results(results)

    assert final_result["status"] == "partial_success"
    assert final_result["incomplete_tasks"][0]["status"] == "cancelled"

def test_invalid_status_is_rejected():
    results = [{"task_id": "summary", "status": "unknown"}]

    with pytest.raises(JoinError, match="Invalid status"):
        join_results(results)

def test_success_without_output_is_rejected():
    results = [{"task_id": "summary", "status": "success"}]

    with pytest.raises(JoinError, match="must contain output"):
        join_results(results)

def test_transient_llm_failure_is_retried(monkeypatch):
    attempts = {"count": 0}

    def flaky_llm(successful_results, timeout_seconds=20.0):
        attempts["count"] += 1

        if attempts["count"] == 1:
            raise TransientLLMError("temporary error")
        return "Recovered response"

    monkeypatch.setattr(join_partial_failure, "call_llm", flaky_llm)
    
    results = [{"task_id": "summary", "status": "success", "output": "Summary completed."}]

    final_result, trace = join_results(results, max_retries=1)

    assert final_result["status"] == "success"
    assert attempts["count"] == 2
    assert "llm_retry=true" in trace