import json
import os
from pathlib import Path
from time import perf_counter, sleep

import requests
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

class JoinError(ValueError):
    pass

class TransientLLMError(Exception):
    pass

VALID_STATUSES = {"success", "failure", "blocked", "cancelled"}

def validate_results(results: list[dict]) -> None:
    if not results:
        raise JoinError("Results cannot be empty.")

    for result in results:
        if "task_id" not in result:
            raise JoinError("Each result must contain task_id.")

        if "status" not in result:
            raise JoinError(f"Task '{result['task_id']}' is missing status.")

        if result["status"] not in VALID_STATUSES:
            raise JoinError(f"Invalid status '{result['status']}' for task '{result['task_id']}'.")

        if result["status"] == "success" and "output" not in result:
            raise JoinError(f"Successful task '{result['task_id']}' must contain output.")

def call_llm(successful_results: list[dict], *, timeout_seconds: float = 20.0) -> str:
    if not API_KEY:
        raise JoinError("API_KEY is missing.")

    if not BASE_URL:
        raise JoinError("BASE_URL is missing.")

    if not MODEL_NAME:
        raise JoinError("MODEL_NAME is missing.")

    prompt = f"""
You are joining outputs from multiple coordinated tasks.
Use only the successful task outputs below.
Successful task results:
{json.dumps(successful_results, indent=2)}

Create one short combined final response.
Do not invent information.
Do not mention failed tasks because failure information will be added separately by the coordinator."""

    try:
        response = requests.post(
            f"{BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
            timeout=timeout_seconds)

    except requests.Timeout as exc:
        raise TransientLLMError("LLM request timed out.") from exc

    except requests.RequestException as exc:
        raise TransientLLMError(f"Temporary LLM request failure: {exc}") from exc

    if response.status_code >= 500:
        raise TransientLLMError(f"LLM server error: {response.status_code}")

    if response.status_code != 200:
        raise JoinError(f"LLM request rejected with status {response.status_code}: {response.text}")

    data = response.json()

    try:
        return data["choices"][0]["message"]["content"]

    except (KeyError, IndexError, TypeError) as exc:
        raise JoinError("Invalid LLM response format.") from exc

def join_results(results: list[dict], *, max_retries: int = 1, timeout_seconds: float = 20.0, max_results: int = 20) -> tuple[dict, list[str]]:
    """ Join successful results while preserving partial failures. """
    validate_results(results)

    if len(results) > max_results:
        raise JoinError(f"Result limit exceeded: {max_results}")

    if max_retries < 0:
        raise ValueError("max_retries cannot be negative.")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than 0.")

    started_at = perf_counter()

    trace = [
        f"result_count={len(results)}",
        f"max_results={max_results}",
        f"max_retries={max_retries}",
    ]

    successful = [result for result in results if result["status"] == "success"]
    unsuccessful = [result for result in results if result["status"] != "success"]

    trace.append(f"successful_count={len(successful)}")
    trace.append(f"unsuccessful_count={len(unsuccessful)}")

    if not successful:
        trace.append("final_status=failure")

        return {
            "status": "failure",
            "message": "No successful task results were available to join.",
            "successful_tasks": [],
            "incomplete_tasks": [{"task_id": result["task_id"], "status": result["status"]}
                for result in unsuccessful]}, trace

    combined_response = None

    for attempt in range(1, max_retries + 2):
        try:
            trace.append(f"llm_attempt={attempt}")
            combined_response = call_llm(successful, timeout_seconds=timeout_seconds)
            trace.append("llm_status=success")

            break

        except TransientLLMError as exc:
            trace.append(f"llm_transient_failure={exc}")

            if attempt > max_retries:
                raise
            trace.append("llm_retry=true")
            sleep(0.5 * attempt)

    if unsuccessful:
        final_status = "partial_success"
    else:
        final_status = "success"

    duration_ms = (perf_counter() - started_at) * 1000

    final_result = {
        "status": final_status,
        "combined_response": combined_response,
        "successful_tasks": [result["task_id"] for result in successful],
        "incomplete_tasks": [{"task_id": result["task_id"], "status": result["status"]}
            for result in unsuccessful],"duration_ms": round(duration_ms, 3)}

    trace.extend([f"final_status={final_status} duration_ms={duration_ms:.3f}"])
    return final_result, trace

def main() -> None:
    output_file = (OUTPUT_DIR / "join_partial_failure.txt")

    print("=== HAPPY PATH ===")

    happy_results = [{"task_id": "summary", "status": "success", "output": "The article explains how AI agents coordinate multiple tasks."},
        {"task_id": "sentiment", "status": "success","output": "The overall sentiment is positive."}]

    happy_final, happy_trace = join_results(happy_results)

    print(json.dumps(happy_final, indent=2))

    print("\nTrace:")
    for item in happy_trace:
        print(item)

    print("\n=== PARTIAL FAILURE PATH ===")

    partial_results = [
        {"task_id": "summary", "status": "success","output": "The article explains coordination between AI agents."},
        {"task_id": "risk_analysis", "status": "failure"},
        {"task_id": "sentiment", "status": "success", "output": "The sentiment is positive."},
        {"task_id": "validation", "status": "blocked"}]

    partial_final, partial_trace = join_results(partial_results)

    print(json.dumps(partial_final, indent=2))

    print("\nTrace:")
    for item in partial_trace:
        print(item)

    lines = [
        "=== HAPPY PATH ===",
        json.dumps(happy_final, indent=2),"",
        "Trace:", *happy_trace, "",
        "=== PARTIAL FAILURE PATH ===",
        json.dumps(partial_final, indent=2),"",
        "Trace:", *partial_trace]

    output_file.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    main()