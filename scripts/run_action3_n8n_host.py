"""Linux host controller: one n8n webhook, guarded temporary backend, restore.

Run from an uploaded release directory containing plan.json and the tested
action3_n8n_server.py. Never rerun after controller-started.json exists.
"""
import concurrent.futures
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
BASE = os.environ.get("DEEPDIVE_BASE_URL", "http://localhost:8000").rstrip("/")


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def records(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        return {row[0]: (row[1], row[2]) for row in db.execute("SELECT id,current_state,data FROM runs")}


def main():
    plan = json.loads((HERE / "plan.json").read_text())
    assert hashlib.sha256((HERE / "action3_n8n_server.py").read_bytes()).hexdigest() == plan["guard_sha256"]
    original = json.loads(docker("inspect", "deepdive"))[0]
    assert original["Config"]["Image"] == "deepdive:preaction3-26907d9"
    mount = next(m for m in original["Mounts"] if m["Destination"] == "/app/data")
    data = Path(mount["Source"])
    root = data / "evaluation-20261024"
    ledger_before = json.loads((root / "budget.json").read_text())
    assert ledger_before["reserved_usd"] == plan["initial_reserved_usd"]
    assert ledger_before["cap_usd"] == "3.50"
    before = records(data / "deepdive.db")
    assert all(state in {"END", "FAILED"} for state, _ in before.values())
    assert len(before) == 19
    assert not (root / "action3-admitted.json").exists()
    # Verify no other evaluation process owns the shared lock before switching.
    with (root / "process.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with (HERE / "controller-started.json").open("x") as marker:
        json.dump({"started_at": time.time(), "plan": plan}, marker)
    with sqlite3.connect(data / "deepdive.db") as source, sqlite3.connect(HERE / "before.db") as target:
        source.backup(target)
        assert target.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    rollback = "deepdive-action3-normal-" + time.strftime("%Y%m%d%H%M%S")
    descriptor, env_path = tempfile.mkstemp(prefix="action3-env-")
    switched = False
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write("\n".join(original["Config"]["Env"]))
        assert all(state in {"END", "FAILED"} for state, _ in records(data / "deepdive.db").values())
        docker("stop", "deepdive")
        docker("rename", "deepdive", rollback)
        switched = True
        labels = []
        for k, v in original["Config"].get("Labels", {}).items():
            labels += ["--label", f"{k}={v}"]
        docker("run", "-d", "--name", "deepdive", "--restart", "no", "--env-file", env_path,
               "--network", original["HostConfig"]["NetworkMode"],
               "-v", f"{data}:/app/data", "-v", f"{HERE / 'action3_n8n_server.py'}:/app/scripts/action3_n8n_server.py:ro",
               *labels, "--entrypoint", "python", original["Config"]["Image"], "/app/scripts/action3_n8n_server.py")
        ready = False
        for _ in range(40):
            try:
                with urllib.request.urlopen(BASE + "/health", timeout=5) as response:
                    ready = json.load(response).get("db_ok", False)
                if ready and (root / "action3-transport.jsonl").exists():
                    break
            except Exception:
                pass
            time.sleep(1)
        assert ready, "Guarded backend readiness failed"
        with (root / "process.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                raise RuntimeError("Guard process does not hold shared lock")
        try:
            urllib.request.urlopen(urllib.request.Request(BASE + "/research", data=b'{"question":"unapproved guard probe"}',
                headers={"Content-Type": "application/json"}), timeout=10)
            raise RuntimeError("Unapproved research was accepted")
        except urllib.error.HTTPError as error:
            assert error.code == 423
        assert not (root / "action3-admitted.json").exists()
        assert json.loads((root / "budget.json").read_text()) == ledger_before
        print("PRE-FLIGHT PASS: one-shot admission, OS lock, preserved budget, production routing", flush=True)
        started = time.monotonic()
        # Exactly one webhook dispatch. No HTTP retry, even on timeout.
        def webhook():
            request = urllib.request.Request(plan["webhook_url"], data=json.dumps(plan["payload"]).encode(),
                                             headers={"Content-Type": "application/json"})
            try:
                response = urllib.request.urlopen(request, timeout=660)
            except urllib.error.HTTPError as error:
                response = error
            except Exception as error:
                result = {"error_type": type(error).__name__, "wall_ms": int((time.monotonic()-started)*1000)}
                (HERE / "webhook-response.json").write_text(json.dumps(result))
                return result
            with response:
                body = response.read().decode()
                result = {"status_code": response.code, "body": body,
                          "wall_ms": int((time.monotonic()-started)*1000)}
                (HERE / "webhook-response.json").write_text(json.dumps(result, indent=2))
                return result
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(webhook)
            seen = None
            for _ in range(1200):
                now = records(data / "deepdive.db")
                new = {k: v for k, v in now.items() if k not in before}
                assert len(new) <= 1, "Unexpected concurrent research run"
                status = [(k, v[0]) for k, v in new.items()]
                ledger = json.loads((root / "budget.json").read_text())
                progress = (status, ledger["reserved_usd"])
                if progress != seen:
                    print(json.dumps({"runs": status, "reserved_usd": ledger["reserved_usd"]}), flush=True)
                    seen = progress
                if future.done() and all(v[0] in {"END", "FAILED"} for v in new.values()):
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Observation deadline; do not restart marked evaluation")
            result = future.result()
        after = records(data / "deepdive.db")
        assert all(after[k] == v for k, v in before.items()), "Historical data changed"
        new_ids = list(set(after) - set(before))
        for run_id in new_ids:
            with urllib.request.urlopen(BASE + f"/runs/{run_id}/workspace", timeout=10) as response:
                (HERE / "workspace.json").write_text(json.dumps(json.load(response), indent=2))
        (HERE / "result.json").write_text(json.dumps({"run_ids": new_ids, "historical_unchanged": True,
            "webhook_status": result.get("status_code"), "restore_container": rollback}, indent=2))
        print("EVALUATION OBSERVED; restoring normal entry point", flush=True)
    finally:
        os.unlink(env_path)
        if switched:
            active = [k for k, (state, _) in records(data / "deepdive.db").items() if state not in {"END", "FAILED"}]
            if active:
                raise RuntimeError("Active evaluation retained; do not interrupt: " + repr(active))
            subprocess.run(["docker", "rm", "-f", "deepdive"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            docker("rename", rollback, "deepdive")
            docker("start", "deepdive")
            print("NORMAL ENTRY POINT RESTORED", flush=True)


if __name__ == "__main__":
    main()
