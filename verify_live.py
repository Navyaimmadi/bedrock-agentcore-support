"""One-shot verification coordinator; never retries an attempted invocation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PROMPTS = ("Look up customer C-100", "What is the status of ticket T-100?")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-paid", action="store_true")
    args = parser.parse_args()
    if not args.allow_paid:
        parser.error("Live verification incurs AWS usage; pass --allow-paid to proceed")
    directory = Path("outputs/live")
    directory.mkdir(parents=True, exist_ok=True)
    journal = directory / "verification-attempt.jsonl"
    # Exclusive creation prevents concurrent or accidental repeat runs, including after failure.
    with journal.open("x", encoding="utf-8") as log:
        for index, prompt in enumerate(PROMPTS, 1):
            log.write(json.dumps({"attempt": index, "prompt": prompt, "status": "started"}) + "\n")
            log.flush()
            try:
                result = subprocess.run([sys.executable, "invoke.py", "--allow-paid", "--prompt", prompt],
                                        capture_output=True, text=True, timeout=150, check=True)
                payload = json.loads(result.stdout)
                expected_agent = "Customer Agent" if index == 1 else "Ticket Agent"
                record = "C-100" if index == 1 else "T-100"
                if payload.get("agent") != expected_agent or record not in payload.get("answer", ""):
                    raise ValueError("Unexpected workflow result")
                log.write(json.dumps({"attempt": index, "status": "success", "result": payload}) + "\n")
                log.flush()
            except (subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
                log.write(json.dumps({"attempt": index, "status": "failed", "error_type": type(exc).__name__}) + "\n")
                log.flush()
                raise SystemExit("Verification stopped; preserve journal and diagnose offline") from exc
    print("Both responses saved; verify matching Gateway and Lambda logs separately.")


if __name__ == "__main__":
    main()
